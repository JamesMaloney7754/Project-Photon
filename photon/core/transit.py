"""Transit parameter extraction stub.

Fits a trapezoidal or Mandel-Agol transit model to a detrended light curve.
Placeholder implementation — full fitting will be added in a future milestone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


class TransitFitError(Exception):
    """Raised when transit parameter extraction fails."""


@dataclass
class TransitParameters:
    """Fitted transit parameters.

    Parameters
    ----------
    t0 : float
        Mid-transit time (same units as *time* array, typically BJD).
    duration_hours : float
        Total transit duration in hours.
    depth : float
        Transit depth as a fractional flux drop (0 < depth < 1).
    ingress_hours : float
        Ingress/egress duration in hours.
    chi2_reduced : float
        Reduced chi-squared of the best-fit model.
    """

    t0: float
    duration_hours: float
    depth: float
    ingress_hours: float
    chi2_reduced: float


def extract_transit_parameters(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    *,
    period_hint: float | None = None,
    t0_hint: float | None = None,
) -> TransitParameters:
    """Fit a transit model to a detrended light curve (stub).

    Parameters
    ----------
    time : np.ndarray
        Array of observation times (BJD or similar).
    flux : np.ndarray
        Normalised flux array (median ~1.0).
    flux_err : np.ndarray
        1-sigma flux uncertainties.
    period_hint : float | None
        Known orbital period in days; used to fold the light curve if provided.
    t0_hint : float | None
        Initial guess for mid-transit time.

    Returns
    -------
    TransitParameters
        Fitted transit parameters.

    Raises
    ------
    TransitFitError
        If the fit fails or insufficient data are provided.

    Notes
    -----
    This is a placeholder.  The production implementation will use
    ``scipy.optimize.minimize`` with a Mandel-Agol model or ``batman``.
    """
    if len(time) < 10:
        raise TransitFitError("Insufficient data points for transit fit (need ≥ 10).")

    if len(time) != len(flux) or len(time) != len(flux_err):
        raise TransitFitError("time, flux, and flux_err must have the same length.")

    logger.warning(
        "transit.extract_transit_parameters is a stub — returning dummy parameters."
    )

    # Stub: return obviously dummy values so callers know this is not implemented.
    return TransitParameters(
        t0=float(np.median(time)),
        duration_hours=float("nan"),
        depth=float("nan"),
        ingress_hours=float("nan"),
        chi2_reduced=float("nan"),
    )
