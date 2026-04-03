"""Aperture photometry — differential flux measurement across a FITS image stack.

All computations use raw calibrated ADU counts.  Never pass stretched or
display-normalised arrays to functions in this module.

Pipeline:
1. :func:`run_aperture_photometry` — circular aperture + annulus background
   subtraction on every frame, returns flux and magnitude arrays.
2. :func:`build_light_curve` — assembles the differential magnitudes and
   timestamps into an ``astropy.table.Table``.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class PhotometryError(Exception):
    """Raised when aperture photometry cannot be performed."""


def run_aperture_photometry(
    image_stack: np.ndarray,
    target_xy: tuple[float, float],
    comparison_xys: list[tuple[float, float]],
    aperture_radius: float = 8.0,
    annulus_inner: float = 12.0,
    annulus_outer: float = 20.0,
) -> dict:
    """Run differential aperture photometry on a stack of frames.

    For each frame:

    1. Create :class:`photutils.aperture.CircularAperture` for the target and
       every comparison star.
    2. Create :class:`photutils.aperture.CircularAnnulus` for sky background.
    3. Run ``aperture_photometry()`` from ``photutils``.
    4. Subtract background (median of annulus pixels × aperture area).
    5. Compute instrumental magnitude: ``-2.5 × log10(net_flux)``.
    6. Compute differential magnitude: ``target_mag - mean(comparison_mags)``.

    Parameters
    ----------
    image_stack : np.ndarray
        3-D array of shape ``(N_frames, height, width)`` in calibrated ADU.
    target_xy : tuple[float, float]
        ``(x, y)`` pixel position of the target star (0-indexed, col-major).
    comparison_xys : list[tuple[float, float]]
        Pixel positions of comparison stars.
    aperture_radius : float
        Source aperture radius in pixels.
    annulus_inner : float
        Inner radius of the sky annulus in pixels.
    annulus_outer : float
        Outer radius of the sky annulus in pixels.

    Returns
    -------
    dict
        Keys:

        - ``"target_flux"`` : np.ndarray, shape ``(N_frames,)``
        - ``"target_mag"`` : np.ndarray, shape ``(N_frames,)``
        - ``"comparison_fluxes"`` : np.ndarray, shape ``(N_frames, N_comp)``
        - ``"differential_mag"`` : np.ndarray, shape ``(N_frames,)``
        - ``"scatter"`` : float — RMS scatter of differential magnitudes
        - ``"snr"`` : np.ndarray, shape ``(N_frames,)``

    Raises
    ------
    PhotometryError
        If photutils is unavailable, the stack is not 3-D, no positions are
        provided, or an aperture falls outside the image bounds.
    """
    try:
        from photutils.aperture import (
            CircularAnnulus,
            CircularAperture,
            aperture_photometry,
        )
    except ImportError as exc:
        raise PhotometryError("photutils is required for aperture photometry") from exc

    if image_stack.ndim != 3:
        raise PhotometryError(
            f"image_stack must be 3-D (N, H, W); got shape {image_stack.shape}"
        )
    if not comparison_xys:
        raise PhotometryError("At least one comparison star is required.")

    n_frames, h, w = image_stack.shape
    n_comp = len(comparison_xys)
    all_positions = [target_xy] + list(comparison_xys)

    # Validate that all apertures fit within the image
    for pos_x, pos_y in all_positions:
        if not (annulus_outer <= pos_x < w - annulus_outer and
                annulus_outer <= pos_y < h - annulus_outer):
            raise PhotometryError(
                f"Position ({pos_x:.1f}, {pos_y:.1f}) is too close to the "
                f"image edge for the requested annulus outer radius "
                f"({annulus_outer} px)."
            )

    target_fluxes = np.zeros(n_frames)
    target_mags   = np.zeros(n_frames)
    comp_fluxes   = np.zeros((n_frames, n_comp))

    aperture = CircularAperture(all_positions, r=aperture_radius)
    annulus  = CircularAnnulus(all_positions, r_in=annulus_inner, r_out=annulus_outer)

    for frame_idx in range(n_frames):
        frame = image_stack[frame_idx].astype(float)

        phot   = aperture_photometry(frame, aperture)
        bkg_phot = aperture_photometry(frame, annulus)

        # Background per pixel in the annulus
        bkg_per_px = np.asarray(bkg_phot["aperture_sum"], dtype=float) / annulus.area
        net_flux   = (
            np.asarray(phot["aperture_sum"], dtype=float)
            - bkg_per_px * aperture.area
        )

        # Clamp to a small positive floor to avoid log(0)
        net_flux = np.clip(net_flux, 1e-6, None)

        target_fluxes[frame_idx] = net_flux[0]
        target_mags[frame_idx]   = -2.5 * np.log10(net_flux[0])

        for c_idx in range(n_comp):
            comp_fluxes[frame_idx, c_idx] = net_flux[c_idx + 1]

    # Differential magnitudes
    comp_mags      = -2.5 * np.log10(comp_fluxes)
    mean_comp_mag  = np.mean(comp_mags, axis=1)
    diff_mag       = target_mags - mean_comp_mag

    scatter = float(np.std(diff_mag)) if n_frames > 1 else 0.0

    # Approximate per-frame SNR: flux / sqrt(flux + n_pix * bkg²)
    # Simplified: flux / sqrt(flux) = sqrt(flux) as Poisson estimate
    snr = np.sqrt(np.clip(target_fluxes, 0, None))

    logger.debug(
        "run_aperture_photometry: %d frames, %d comparisons, scatter=%.4f mag",
        n_frames, n_comp, scatter,
    )
    return {
        "target_flux":        target_fluxes,
        "target_mag":         target_mags,
        "comparison_fluxes":  comp_fluxes,
        "differential_mag":   diff_mag,
        "scatter":            scatter,
        "snr":                snr,
    }


def build_light_curve(
    differential_mags: np.ndarray,
    observation_times: object,
    frame_flags: Optional[np.ndarray] = None,
) -> object:
    """Assemble photometry results into a light curve Table.

    Parameters
    ----------
    differential_mags : np.ndarray
        Per-frame differential magnitudes, shape ``(N_frames,)``.
    observation_times : astropy.time.Time
        Observation times, one per frame.  If ``None``, an integer frame index
        is stored in the ``time`` column.
    frame_flags : np.ndarray or None
        Boolean mask — ``True`` means the frame is flagged / excluded from
        analysis.  Flagged frames are included in the output but marked
        ``flagged=True``.

    Returns
    -------
    astropy.table.Table
        Columns: ``time``, ``mag``, ``mag_err``, ``flagged``, ``frame_index``.
    """
    from astropy.table import Table
    import astropy.time

    n = len(differential_mags)
    if frame_flags is None:
        frame_flags = np.zeros(n, dtype=bool)

    good = ~frame_flags
    scatter = float(np.std(differential_mags[good])) if good.sum() > 1 else 0.0
    mag_err = np.full(n, scatter if scatter > 0 else 0.001)

    if observation_times is None:
        times_col = np.arange(n, dtype=float)
    elif isinstance(observation_times, astropy.time.Time):
        times_col = observation_times
    else:
        times_col = np.asarray(observation_times, dtype=float)

    table = Table(
        {
            "time":        times_col,
            "mag":         differential_mags.copy(),
            "mag_err":     mag_err,
            "flagged":     frame_flags.copy(),
            "frame_index": np.arange(n, dtype=int),
        }
    )
    logger.debug("build_light_curve: %d frames, scatter=%.4f mag", n, scatter)
    return table
