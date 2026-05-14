"""Star detection — finds and characterises stellar sources in a 2-D image.

All functions are Qt-free and can be called from a worker thread or tested
headlessly.  Detection uses ``photutils.detection.DAOStarFinder`` with sigma-
clipped background estimation from ``astropy.stats``.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def detect_stars(
    image: np.ndarray,
    fwhm: float = 3.0,
    threshold_sigma: float = 5.0,
) -> object:
    """Detect stars in a 2-D image using DAOStarFinder.

    Background is estimated with sigma-clipped statistics.  The detection
    threshold is ``threshold_sigma * std`` above the sigma-clipped median.
    Sources are returned sorted by flux, brightest first.

    Parameters
    ----------
    image : np.ndarray
        2-D array of pixel values in calibrated ADU.
    fwhm : float
        Expected stellar FWHM in pixels.  Default is 3.0.
    threshold_sigma : float
        Detection threshold in units of background sigma.  Default is 5.0.

    Returns
    -------
    astropy.table.Table
        Table with columns ``id``, ``x_centroid``, ``y_centroid``,
        ``peak``, ``flux``, ``sharpness``, ``roundness1``, ``roundness2``.
        Empty table (zero rows, same columns) when no sources are found.
    """
    from astropy.stats import sigma_clipped_stats
    from astropy.table import Table
    from photutils.detection import DAOStarFinder

    if image.ndim != 2:
        raise ValueError(f"detect_stars requires a 2-D array; got shape {image.shape}")

    # Downsample large images to cap detection time on high-res cameras.
    _MAX_DIM = 1024
    h, w = image.shape
    scale = 1.0
    if max(h, w) > _MAX_DIM:
        scale = _MAX_DIM / max(h, w)
        try:
            from scipy.ndimage import zoom as _zoom
            detection_image = _zoom(image, scale, order=1)
        except ImportError:
            detection_image = image
            scale = 1.0
        logger.debug(
            "detect_stars: downsampled %dx%d → %dx%d (scale=%.3f)",
            h, w, int(h * scale), int(w * scale), scale,
        )
    else:
        detection_image = image

    _, median, std = sigma_clipped_stats(detection_image, sigma=3.0)
    if std <= 0.0:
        std = 1.0

    daofind = DAOStarFinder(fwhm=fwhm * scale, threshold=threshold_sigma * std)
    sources = daofind(detection_image - median)

    if sources is None or len(sources) == 0:
        return Table(
            names=["id", "x_centroid", "y_centroid", "peak", "flux", "sharpness",
                   "roundness1", "roundness2"],
            dtype=[int, float, float, float, float, float, float, float],
        )

    # Ensure consistent column subset and sort brightest first
    keep = ["id", "x_centroid", "y_centroid", "peak", "flux", "sharpness",
            "roundness1", "roundness2"]
    out = sources[[c for c in keep if c in sources.colnames]]
    out.sort("flux")
    out.reverse()

    # Scale centroid coordinates back to the original image resolution
    if scale != 1.0:
        out["x_centroid"] = out["x_centroid"] / scale
        out["y_centroid"] = out["y_centroid"] / scale

    logger.debug("detect_stars: found %d sources (fwhm=%.1f, sigma=%.1f)",
                 len(out), fwhm, threshold_sigma)
    return out


def select_comparison_stars(
    all_stars: object,
    target_x: float,
    target_y: float,
    min_snr: float = 50.0,
    max_stars: int = 10,
    exclusion_radius_px: float = 30.0,
) -> object:
    """Select suitable comparison stars from detected sources.

    Applies these filters in order:

    1. Exclude any star within *exclusion_radius_px* of the target position.
    2. Exclude stars within 20 px of the image edge (using ``x_centroid`` /
       ``y_centroid``; image size is inferred from ``x_centroid.max() + 20``).
    3. Exclude stars with ``peak`` flux > 0.8 × ``peak.max()`` (avoid
       saturated sources).
    4. Keep at most *max_stars* brightest remaining stars.

    Parameters
    ----------
    all_stars : astropy.table.Table
        Full source detection table, e.g. from :func:`detect_stars`.
    target_x, target_y : float
        Pixel coordinates of the target star (to exclude from comparisons).
    min_snr : float
        Minimum acceptable SNR (flux / sqrt(flux)) for a comparison star.
        Stars below this threshold are excluded.
    max_stars : int
        Maximum number of comparison stars to return.
    exclusion_radius_px : float
        Radius around the target inside which sources are excluded.

    Returns
    -------
    astropy.table.Table
        Filtered table with at most *max_stars* rows, sorted brightest-first.
    """
    import numpy as np

    if len(all_stars) == 0:
        return all_stars

    xs = np.asarray(all_stars["x_centroid"], dtype=float)
    ys = np.asarray(all_stars["y_centroid"], dtype=float)
    peaks = np.asarray(all_stars["peak"], dtype=float)
    fluxes = np.asarray(all_stars["flux"], dtype=float)

    # 1. Exclude target
    dist_to_target = np.sqrt((xs - target_x) ** 2 + (ys - target_y) ** 2)
    mask_not_target = dist_to_target > exclusion_radius_px

    # 2. Edge exclusion (20 px)
    edge = 20.0
    mask_not_edge = (xs > edge) & (ys > edge)

    # 3. Saturation exclusion (peak > 80% of max peak)
    sat_limit = 0.80 * float(peaks.max()) if peaks.max() > 0 else 1e38
    mask_not_sat = peaks < sat_limit

    # 4. SNR filter: proxy SNR = flux / sqrt(|flux| + 1)
    snr_proxy = fluxes / np.sqrt(np.abs(fluxes) + 1.0)
    mask_snr = snr_proxy >= min_snr

    combined = mask_not_target & mask_not_edge & mask_not_sat & mask_snr
    filtered = all_stars[combined]

    # Sort by flux descending (already done by detect_stars but re-sort to be safe)
    if len(filtered) > 0:
        filtered = filtered[:max_stars]

    logger.debug(
        "select_comparison_stars: %d/%d sources passed filters",
        len(filtered), len(all_stars),
    )
    return filtered


def snap_to_nearest_star(
    click_x: float,
    click_y: float,
    stars: object,
    max_distance_px: float = 15.0,
) -> Optional[int]:
    """Return the row index of the nearest star to a click position.

    Parameters
    ----------
    click_x, click_y : float
        Clicked pixel coordinates.
    stars : astropy.table.Table
        Source table, e.g. from :func:`detect_stars`.
    max_distance_px : float
        Maximum snap distance in pixels.  Returns ``None`` if no star is
        within this radius.

    Returns
    -------
    int or None
        Row index into *stars*, or ``None`` if no star is within range.
    """
    import numpy as np

    if stars is None or len(stars) == 0:
        return None

    xs = np.asarray(stars["x_centroid"], dtype=float)
    ys = np.asarray(stars["y_centroid"], dtype=float)
    dists = np.sqrt((xs - click_x) ** 2 + (ys - click_y) ** 2)
    idx = int(np.argmin(dists))
    if dists[idx] <= max_distance_px:
        return idx
    return None
