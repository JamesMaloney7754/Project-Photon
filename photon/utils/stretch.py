"""Astropy visualization stretch helpers.

Converts raw science arrays to display-ready normalised arrays using
``astropy.visualization`` interval and stretch transforms.  These functions
are for display only — never feed stretched data to photometry or astrometry.
"""

from __future__ import annotations

import numpy as np


def stretch_image(
    data: np.ndarray,
    stretch: str = "asinh",
    percentile_low: float = 1.0,
    percentile_high: float = 99.5,
) -> np.ndarray:
    """Apply an interval and stretch transform to *data* for display.

    Uses :class:`astropy.visualization.PercentileInterval` to clip outliers,
    then applies the requested stretch to map the result to ``[0, 1]``.

    Parameters
    ----------
    data : np.ndarray
        2-D science frame in raw calibrated ADU (any numeric dtype).
    stretch : str
        Stretch algorithm.  One of ``"linear"``, ``"sqrt"``, ``"log"``,
        ``"asinh"``.
    percentile_low : float
        Lower percentile bound for the interval clip (default ``1.0``).
    percentile_high : float
        Upper percentile bound for the interval clip (default ``99.5``).

    Returns
    -------
    np.ndarray
        Float32 array with values normalised to ``[0, 1]``, suitable for
        passing directly to Matplotlib's ``imshow``.

    Raises
    ------
    ValueError
        If *stretch* is not one of the supported options.
    """
    from astropy.visualization import (  # type: ignore[import]
        AsinhStretch,
        ImageNormalize,
        LinearStretch,
        LogStretch,
        PercentileInterval,
        SqrtStretch,
    )

    stretch_map = {
        "linear": LinearStretch(),
        "sqrt": SqrtStretch(),
        "log": LogStretch(),
        "asinh": AsinhStretch(),
    }
    if stretch not in stretch_map:
        raise ValueError(
            f"Unknown stretch {stretch!r}. Choose from {list(stretch_map)}."
        )

    interval = PercentileInterval(
        # PercentileInterval accepts a single percentile p and clips to
        # [p_low, p_high] symmetrically only when given one argument, so we
        # use the two-argument upper_percentile / lower_percentile directly.
        # For asymmetric bounds we build the interval manually.
        100.0  # placeholder — overridden below
    )
    # Compute vmin/vmax directly for asymmetric percentile bounds
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return np.zeros_like(data, dtype=np.float32)

    vmin = float(np.percentile(finite, percentile_low))
    vmax = float(np.percentile(finite, percentile_high))
    if vmax <= vmin:
        vmax = vmin + 1.0  # prevent degenerate interval

    norm = ImageNormalize(
        data,
        vmin=vmin,
        vmax=vmax,
        stretch=stretch_map[stretch],
        clip=True,
    )
    return norm(data).astype(np.float32)


def compute_percentile_limits(
    data: np.ndarray,
    percentile_low: float = 1.0,
    percentile_high: float = 99.5,
) -> tuple[float, float]:
    """Return ``(vmin, vmax)`` for a percentile interval of *data*.

    Parameters
    ----------
    data : np.ndarray
        2-D science array.
    percentile_low : float
        Lower percentile (default ``1.0``).
    percentile_high : float
        Upper percentile (default ``99.5``).

    Returns
    -------
    tuple[float, float]
        ``(vmin, vmax)`` as plain Python floats.
    """
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    return float(np.percentile(finite, percentile_low)), float(
        np.percentile(finite, percentile_high)
    )
