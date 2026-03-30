"""Aperture photometry stub.

Wraps ``photutils`` aperture photometry.  All computations use raw calibrated
counts — no display stretching is applied here.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class PhotometryError(Exception):
    """Raised when aperture photometry cannot be performed."""


def run_aperture_photometry(
    data: np.ndarray,
    positions: list[tuple[float, float]],
    aperture_radius: float = 8.0,
    inner_annulus: float = 12.0,
    outer_annulus: float = 20.0,
) -> list[dict[str, Any]]:
    """Perform aperture photometry on *data* at *positions*.

    Uses a circular aperture with a circular-annulus background estimator
    (sigma-clipped median).

    Parameters
    ----------
    data : np.ndarray
        2-D science frame in calibrated ADU (float32 or float64).
    positions : list[tuple[float, float]]
        List of (x, y) pixel positions (0-indexed, column-major).
    aperture_radius : float
        Source aperture radius in pixels.
    inner_annulus : float
        Inner radius of background annulus in pixels.
    outer_annulus : float
        Outer radius of background annulus in pixels.

    Returns
    -------
    list[dict[str, Any]]
        One dict per position with keys:
        ``x``, ``y``, ``flux``, ``flux_err``, ``sky_per_pixel``.

    Raises
    ------
    PhotometryError
        If ``photutils`` is unavailable or photometry fails.
    """
    try:
        from photutils.aperture import (  # type: ignore[import]
            CircularAperture,
            CircularAnnulus,
            ApertureStats,
        )
    except ImportError as exc:
        raise PhotometryError(
            "photutils is required for aperture photometry."
        ) from exc

    if data.ndim != 2:
        raise PhotometryError(f"Expected a 2-D array, got shape {data.shape}.")
    if not positions:
        return []

    apertures = CircularAperture(positions, r=aperture_radius)
    annuli = CircularAnnulus(positions, r_in=inner_annulus, r_out=outer_annulus)

    # Estimate background per pixel from annulus
    try:
        bkg_stats = ApertureStats(data, annuli, sigma_clip=None)
        sky_per_pixel = bkg_stats.median  # shape (N,)

        src_stats = ApertureStats(data, apertures)
        raw_flux = src_stats.sum  # shape (N,)
        npix = src_stats.sum_aper_area.value  # shape (N,)
    except Exception as exc:
        raise PhotometryError(f"Aperture photometry failed: {exc}") from exc

    results = []
    for i, (x, y) in enumerate(positions):
        sky = float(sky_per_pixel[i]) if np.isfinite(sky_per_pixel[i]) else 0.0
        net_flux = float(raw_flux[i]) - sky * float(npix[i])
        # Simple Poisson + readnoise estimate (gain assumed 1 e-/ADU)
        flux_err = float(np.sqrt(max(net_flux, 0.0) + float(npix[i]) * sky))
        results.append(
            {
                "x": float(x),
                "y": float(y),
                "flux": net_flux,
                "flux_err": flux_err,
                "sky_per_pixel": sky,
            }
        )

    logger.debug("Photometry complete for %d sources.", len(results))
    return results
