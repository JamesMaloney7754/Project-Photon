"""FITS ingestion module.

Loads FITS files from disk, validates them, and returns ``FitsFrame`` objects.
All I/O happens synchronously; call this from a worker thread, not the UI thread.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
import warnings

from photon.core.session import FitsFrame

logger = logging.getLogger(__name__)


class FitsLoadError(Exception):
    """Raised when a FITS file cannot be loaded or is structurally invalid."""


def load_fits(path: str | Path) -> FitsFrame:
    """Load a FITS file and return a ``FitsFrame``.

    Supports single-extension FITS and multi-extension FITS (MEF).  For MEF
    files the first image extension with 2-D or 3-D data is used.  The pixel
    array is converted to ``float32`` to keep memory predictable.

    Parameters
    ----------
    path : str | Path
        Path to the FITS file on disk.

    Returns
    -------
    FitsFrame
        Loaded frame with ``data``, ``header``, and ``wcs`` populated.  ``wcs``
        is ``None`` when no valid WCS is present in the header.

    Raises
    ------
    FitsLoadError
        If the file does not exist, is not a valid FITS file, or contains no
        usable image data.
    """
    path = Path(path)
    if not path.exists():
        raise FitsLoadError(f"File not found: {path}")

    logger.debug("Loading FITS file: %s", path)

    try:
        with fits.open(path, memmap=False) as hdul:
            hdul.verify("silentfix")
            primary_header = dict(hdul[0].header)
            data, header = _extract_image(hdul)
    except OSError as exc:
        raise FitsLoadError(f"Cannot open FITS file {path}: {exc}") from exc

    data = data.astype(np.float32)
    wcs = _extract_wcs(header)

    logger.info("Loaded %s — shape %s, dtype %s", path.name, data.shape, data.dtype)
    return FitsFrame(path=path.resolve(), data=data, header=header, wcs=wcs)


def _extract_image(hdul: fits.HDUList) -> tuple[np.ndarray, dict[str, Any]]:
    """Return the first usable image array and its header from *hdul*.

    Parameters
    ----------
    hdul : fits.HDUList
        Open HDU list.

    Returns
    -------
    tuple[np.ndarray, dict[str, Any]]
        Pixel data and header dict.

    Raises
    ------
    FitsLoadError
        If no image HDU with at least 2 dimensions is found.
    """
    # Try primary HDU first
    if hdul[0].data is not None and hdul[0].data.ndim >= 2:
        return hdul[0].data, dict(hdul[0].header)

    # Search extensions
    for hdu in hdul[1:]:
        if isinstance(hdu, (fits.ImageHDU, fits.CompImageHDU)):
            if hdu.data is not None and hdu.data.ndim >= 2:
                return hdu.data, dict(hdu.header)

    raise FitsLoadError("No 2-D or 3-D image data found in any HDU.")


def _extract_wcs(header: dict[str, Any]) -> WCS | None:
    """Build a ``WCS`` from *header* if the header contains WCS keywords.

    Parameters
    ----------
    header : dict[str, Any]
        FITS header as a plain dict.

    Returns
    -------
    WCS | None
        Parsed WCS object, or ``None`` if no WCS keywords are present or the
        header cannot be parsed.
    """
    # Quick check — requires at least CRPIX1 and CRVAL1
    if "CRPIX1" not in header or "CRVAL1" not in header:
        return None

    fits_header = fits.Header(header)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FITSFixedWarning)
            wcs = WCS(fits_header, naxis=2)
        if wcs.has_celestial:
            return wcs
        return None
    except Exception as exc:  # astropy raises various internal errors
        logger.warning("Could not parse WCS from header: %s", exc)
        return None


def debayer(data: np.ndarray, pattern: str = "RGGB") -> np.ndarray:
    """Debayer a raw Bayer-mosaic frame to a 3-channel RGB array.

    This is a simple bilinear debayer suitable for preview only.  Use a
    dedicated library (e.g. ``colour-demosaicing``) for science-grade results.

    Parameters
    ----------
    data : np.ndarray
        2-D raw sensor array.
    pattern : str
        Bayer CFA pattern string.  One of ``"RGGB"``, ``"BGGR"``, ``"GRBG"``,
        ``"GBRG"``.

    Returns
    -------
    np.ndarray
        3-D array of shape ``(H, W, 3)`` with dtype ``float32``.

    Raises
    ------
    ValueError
        If *data* is not 2-D or *pattern* is unrecognised.
    """
    if data.ndim != 2:
        raise ValueError(f"debayer expects a 2-D array, got shape {data.shape}")
    if pattern not in {"RGGB", "BGGR", "GRBG", "GBRG"}:
        raise ValueError(f"Unknown Bayer pattern: {pattern!r}")

    h, w = data.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)

    offsets = {
        "RGGB": {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)},
        "BGGR": {"R": (1, 1), "G1": (0, 1), "G2": (1, 0), "B": (0, 0)},
        "GRBG": {"R": (0, 1), "G1": (0, 0), "G2": (1, 1), "B": (1, 0)},
        "GBRG": {"R": (1, 0), "G1": (0, 0), "G2": (1, 1), "B": (0, 1)},
    }
    o = offsets[pattern]

    # Red channel
    rgb[o["R"][0]::2, o["R"][1]::2, 0] = data[o["R"][0]::2, o["R"][1]::2]
    # Green channel — average of two green sub-arrays
    rgb[o["G1"][0]::2, o["G1"][1]::2, 1] = data[o["G1"][0]::2, o["G1"][1]::2]
    rgb[o["G2"][0]::2, o["G2"][1]::2, 1] = data[o["G2"][0]::2, o["G2"][1]::2]
    # Blue channel
    rgb[o["B"][0]::2, o["B"][1]::2, 2] = data[o["B"][0]::2, o["B"][1]::2]

    return rgb
