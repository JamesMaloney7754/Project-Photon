"""Astropy visualization stretch helpers.

Converts raw science arrays to display-ready normalised arrays using
``astropy.visualization`` interval and stretch transforms.  These functions
are for display only — never feed stretched data to photometry or astrometry.
"""

from __future__ import annotations

import numpy as np


def stretch_data(
    data: np.ndarray,
    stretch: str = "asinh",
    interval: str = "zscale",
) -> np.ndarray:
    """Normalise *data* to [0, 1] for display using astropy visualisation.

    Parameters
    ----------
    data : np.ndarray
        2-D science frame in raw calibrated ADU.
    stretch : str
        Stretch algorithm name.  One of ``"linear"``, ``"sqrt"``, ``"log"``,
        ``"asinh"``, ``"power"``.
    interval : str
        Interval algorithm for setting vmin/vmax.  One of ``"zscale"``,
        ``"minmax"``, ``"percentile"``.

    Returns
    -------
    np.ndarray
        Float32 array with values in [0, 1], suitable for display.

    Raises
    ------
    ValueError
        If *stretch* or *interval* is unrecognised.
    """
    from astropy.visualization import (  # type: ignore[import]
        AsinhStretch,
        LinearStretch,
        LogStretch,
        PowerStretch,
        SqrtStretch,
        ZScaleInterval,
        MinMaxInterval,
        PercentileInterval,
        ImageNormalize,
    )

    stretch_map = {
        "linear": LinearStretch(),
        "sqrt": SqrtStretch(),
        "log": LogStretch(),
        "asinh": AsinhStretch(),
        "power": PowerStretch(0.5),
    }
    interval_map = {
        "zscale": ZScaleInterval(),
        "minmax": MinMaxInterval(),
        "percentile": PercentileInterval(99.0),
    }

    if stretch not in stretch_map:
        raise ValueError(
            f"Unknown stretch {stretch!r}. Choose from {list(stretch_map)}."
        )
    if interval not in interval_map:
        raise ValueError(
            f"Unknown interval {interval!r}. Choose from {list(interval_map)}."
        )

    norm = ImageNormalize(data, interval=interval_map[interval], stretch=stretch_map[stretch])
    return norm(data).astype(np.float32)


def compute_zscale_limits(data: np.ndarray) -> tuple[float, float]:
    """Return (vmin, vmax) for the ZScale interval of *data*.

    Parameters
    ----------
    data : np.ndarray
        2-D science array.

    Returns
    -------
    tuple[float, float]
        ``(vmin, vmax)`` as plain Python floats.
    """
    from astropy.visualization import ZScaleInterval  # type: ignore[import]

    vmin, vmax = ZScaleInterval().get_limits(data)
    return float(vmin), float(vmax)
