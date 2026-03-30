"""FITS ingestion module.

Loads sequences of calibrated FITS files from disk and returns stacked numpy
arrays suitable for photometry and astrometry pipelines.  All I/O is
synchronous; call these functions from a worker thread, never from the UI
thread.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time

logger = logging.getLogger(__name__)


def load_fits_sequence(paths: list[Path]) -> tuple[np.ndarray, list]:
    """Load a sequence of calibrated FITS files into a 3-D numpy array.

    Parameters
    ----------
    paths : list[Path]
        Ordered list of FITS file paths.  All files must have identical
        spatial dimensions.

    Returns
    -------
    image_stack : np.ndarray
        Array of shape ``(N, height, width)`` with dtype ``float64``.
    headers : list of astropy.io.fits.Header
        One header per frame, preserving all original keywords.

    Raises
    ------
    ValueError
        If *paths* is empty or frames have inconsistent spatial dimensions.
    FileNotFoundError
        If any path does not exist.
    OSError
        If any file cannot be opened as a valid FITS file.
    """
    if not paths:
        raise ValueError("load_fits_sequence requires at least one path.")

    frames: list[np.ndarray] = []
    headers: list[fits.Header] = []
    reference_shape: tuple[int, int] | None = None

    for path in paths:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"FITS file not found: {path}")

        logger.debug("Loading %s", path)
        with fits.open(path, memmap=False) as hdul:
            hdul.verify("silentfix")
            data, header = _extract_image_and_header(hdul)

        data = data.astype(np.float64)

        if reference_shape is None:
            reference_shape = data.shape
        elif data.shape != reference_shape:
            raise ValueError(
                f"Frame dimension mismatch: expected {reference_shape}, "
                f"got {data.shape} for {path.name}"
            )

        frames.append(data)
        headers.append(header)
        logger.info("Loaded %s — shape %s", path.name, data.shape)

    image_stack = np.stack(frames, axis=0)
    logger.info(
        "Loaded sequence of %d frame(s), stack shape %s", len(frames), image_stack.shape
    )
    return image_stack, headers


def _extract_image_and_header(hdul: fits.HDUList) -> tuple[np.ndarray, fits.Header]:
    """Return the first usable 2-D image array and its header from *hdul*.

    Parameters
    ----------
    hdul : fits.HDUList
        Open HDU list.

    Returns
    -------
    tuple[np.ndarray, fits.Header]
        Pixel data and FITS header.

    Raises
    ------
    ValueError
        If no 2-D image HDU is found.
    """
    # Primary HDU first
    if hdul[0].data is not None and hdul[0].data.ndim == 2:
        return hdul[0].data, hdul[0].header

    # For 3-D primary (e.g. RGB cube), use first plane
    if hdul[0].data is not None and hdul[0].data.ndim == 3:
        return hdul[0].data[0], hdul[0].header

    # Search extensions
    for hdu in hdul[1:]:
        if isinstance(hdu, (fits.ImageHDU, fits.CompImageHDU)):
            if hdu.data is not None and hdu.data.ndim >= 2:
                data = hdu.data if hdu.data.ndim == 2 else hdu.data[0]
                return data, hdu.header

    raise ValueError("No 2-D image data found in any HDU.")


def get_observation_times(headers: list) -> Time:
    """Extract observation timestamps from a list of FITS headers.

    Tries the following keywords in order: ``DATE-OBS``, ``JD``, ``MJD``.
    The first keyword found in the first header is used for all frames.

    Parameters
    ----------
    headers : list of astropy.io.fits.Header
        One header per frame.

    Returns
    -------
    astropy.time.Time
        Time array with one element per frame, in UTC scale.

    Raises
    ------
    ValueError
        If no recognised time keyword is found in any header.
    """
    if not headers:
        raise ValueError("headers list is empty.")

    time_values: list[float | str] = []
    time_format: str | None = None
    time_scale: str = "utc"

    # Determine which keyword is available using the first header
    first = headers[0]
    if "DATE-OBS" in first:
        time_format = "isot"
        for h in headers:
            value = h.get("DATE-OBS", "")
            if not value:
                raise ValueError("DATE-OBS keyword is missing or empty in one or more headers.")
            time_values.append(value)
    elif "JD" in first:
        time_format = "jd"
        time_scale = "utc"
        for h in headers:
            if "JD" not in h:
                raise ValueError("JD keyword is missing in one or more headers.")
            time_values.append(float(h["JD"]))
    elif "MJD" in first:
        time_format = "mjd"
        time_scale = "utc"
        for h in headers:
            if "MJD" not in h:
                raise ValueError("MJD keyword is missing in one or more headers.")
            time_values.append(float(h["MJD"]))
    else:
        raise ValueError(
            "No recognised time keyword (DATE-OBS, JD, MJD) found in headers."
        )

    logger.debug("Parsed %d timestamps using keyword format=%s", len(time_values), time_format)
    return Time(time_values, format=time_format, scale=time_scale)


def summarize_sequence(paths: list[Path], stack: np.ndarray, headers: list) -> dict:
    """Return a dict of human-readable metadata about a loaded FITS sequence.

    Parameters
    ----------
    paths : list[Path]
        Ordered list of FITS file paths (same order as *stack* and *headers*).
    stack : np.ndarray
        Image stack of shape ``(N, height, width)``.
    headers : list of astropy.io.fits.Header
        One header per frame.

    Returns
    -------
    dict
        Dictionary with keys:

        ``n_frames``
            Number of frames.
        ``dimensions``
            String ``"height × width"`` in pixels.
        ``filter``
            Value of the ``FILTER`` header keyword, or ``"unknown"`` if absent.
        ``date_range``
            String ``"start → end"`` in ISO format, or ``"unknown"`` if no time
            keyword is present.
        ``median_sky``
            Sigma-clipped median background estimate (ADU) from the first frame,
            as a float rounded to 2 decimal places.
    """
    n, height, width = stack.shape
    first_header = headers[0] if headers else {}

    filter_name = first_header.get("FILTER", "unknown") if headers else "unknown"

    # Date range
    date_range = "unknown"
    try:
        times = get_observation_times(headers)
        if len(times) == 1:
            date_range = times[0].isot
        else:
            date_range = f"{times[0].isot} → {times[-1].isot}"
    except ValueError:
        pass

    # Sigma-clipped background estimate from first frame
    _, median, _ = sigma_clipped_stats(stack[0], sigma=3.0)

    return {
        "n_frames": n,
        "dimensions": f"{height} × {width}",
        "filter": str(filter_name),
        "date_range": date_range,
        "median_sky": round(float(median), 2),
    }
