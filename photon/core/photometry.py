"""Aperture photometry stubs.

This module will implement differential aperture photometry on a stack of
calibrated FITS frames.  All computations use raw calibrated ADU counts —
never stretched or display-normalised arrays.

Pipeline:
1. ``select_comparison_stars`` — pick stable, unsaturated comparison stars
   from a catalog table (Gaia DR3 or SIMBAD cross-match).
2. ``run_aperture_photometry`` — perform circular aperture + annulus
   background subtraction on every frame for every selected source using
   ``photutils``.  Returns per-frame flux measurements that are stored in
   ``PhotonSession.photometry_results``.
"""

from __future__ import annotations

import numpy as np


class PhotometryError(Exception):
    """Raised when aperture photometry cannot be performed."""


def select_comparison_stars(
    catalog_table: object,
    *,
    max_stars: int = 10,
    mag_range: tuple[float, float] = (10.0, 16.0),
    max_variability_flag: int = 0,
) -> object:
    """Select suitable comparison stars from a catalog cross-match table.

    Filters the catalog to non-variable, unsaturated, isolated stars within
    the specified magnitude range, then ranks by proximity to the target and
    signal-to-noise estimate.

    Parameters
    ----------
    catalog_table : astropy.table.Table
        Cross-matched source catalog (e.g. Gaia DR3 ``gaia_source`` table)
        containing at minimum magnitude and variability flag columns.
    max_stars : int
        Maximum number of comparison stars to return.  Default is 10.
    mag_range : tuple[float, float]
        ``(bright_limit, faint_limit)`` in magnitudes.  Default is
        ``(10.0, 16.0)``.
    max_variability_flag : int
        Maximum allowed Gaia ``phot_variable_flag`` value.  Default is 0
        (only ``NOT_AVAILABLE`` or ``NON_VARIABLE`` sources).

    Returns
    -------
    astropy.table.Table
        Filtered and ranked subset of *catalog_table* with at most
        *max_stars* rows, suitable for use as differential photometry
        comparison ensemble.

    Raises
    ------
    PhotometryError
        If the filtered table contains fewer than 3 usable comparison stars.
    """
    raise NotImplementedError(
        "select_comparison_stars() is not yet implemented. "
        "It will filter catalog_table by mag_range and variability flag, "
        "then rank by isolation and SNR estimate."
    )


def run_aperture_photometry(
    image_stack: np.ndarray,
    positions: list[tuple[float, float]],
    *,
    aperture_radius: float = 8.0,
    inner_annulus: float = 12.0,
    outer_annulus: float = 20.0,
) -> dict[int, list[dict]]:
    """Perform aperture photometry on every frame for every source position.

    Uses circular apertures with a circular-annulus sky background estimator
    (sigma-clipped median) from ``photutils``.

    Parameters
    ----------
    image_stack : np.ndarray
        3-D array of shape ``(N_frames, height, width)`` in calibrated ADU.
    positions : list[tuple[float, float]]
        List of ``(x, y)`` pixel positions (0-indexed, column-major) for the
        target and all comparison stars.
    aperture_radius : float
        Source aperture radius in pixels.  Default is 8.
    inner_annulus : float
        Inner radius of the sky background annulus in pixels.  Default is 12.
    outer_annulus : float
        Outer radius of the sky background annulus in pixels.  Default is 20.

    Returns
    -------
    dict[int, list[dict]]
        Mapping of ``frame_index`` → list of result dicts, one per position.
        Each dict contains keys ``x``, ``y``, ``flux``, ``flux_err``, and
        ``sky_per_pixel``.

    Raises
    ------
    PhotometryError
        If ``photutils`` is unavailable, *image_stack* is not 3-D, or no
        positions are provided.
    """
    raise NotImplementedError(
        "run_aperture_photometry() is not yet implemented. "
        "It will iterate over frames in image_stack, apply photutils "
        "CircularAperture + CircularAnnulus, and return net flux measurements."
    )
