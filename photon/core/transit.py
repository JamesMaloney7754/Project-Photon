"""Exoplanet transit detection and model-fitting stubs.

This module will implement:
1. ``detect_transit_events`` — identify candidate transit-like dips in a
   detrended light curve using a Box Least Squares (BLS) periodogram.
2. ``fit_transit_model`` — fit a Mandel-Agol (or trapezoidal) transit model
   to a phase-folded light curve using ``scipy.optimize`` or ``batman``.

All functions operate on plain numpy arrays and astropy tables; no Qt imports.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class TransitError(Exception):
    """Raised when transit detection or fitting fails."""


@dataclass
class TransitCandidate:
    """A candidate transit event found by the BLS periodogram.

    Parameters
    ----------
    period_days : float
        Best-fit orbital period in days.
    t0 : float
        Mid-transit time of the strongest event (same units as input time array).
    duration_hours : float
        Estimated transit duration in hours.
    depth : float
        Transit depth as a fractional flux drop (0 < depth < 1).
    snr : float
        Signal-to-noise ratio of the BLS peak.
    """

    period_days: float
    t0: float
    duration_hours: float
    depth: float
    snr: float


@dataclass
class TransitFitResult:
    """Result of a parametric transit model fit.

    Parameters
    ----------
    t0 : float
        Fitted mid-transit time (same units as input time array).
    period_days : float
        Fitted orbital period in days.
    rp_over_rs : float
        Planet-to-star radius ratio Rp/Rs.
    duration_hours : float
        Fitted transit duration in hours.
    impact_parameter : float
        Transit impact parameter b (0 = central transit).
    chi2_reduced : float
        Reduced chi-squared of the best-fit model.
    """

    t0: float
    period_days: float
    rp_over_rs: float
    duration_hours: float
    impact_parameter: float
    chi2_reduced: float


def detect_transit_events(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    *,
    period_min: float = 0.5,
    period_max: float = 30.0,
    n_candidates: int = 5,
) -> list[TransitCandidate]:
    """Search a detrended light curve for transit-like periodic dips.

    Uses a Box Least Squares (BLS) periodogram (``astropy.timeseries.BoxLeastSquares``
    or ``lightkurve``) to identify the most significant periodic signals.

    Parameters
    ----------
    time : np.ndarray
        Array of observation times in days (BJD or similar).
    flux : np.ndarray
        Detrended, normalised flux array (median ≈ 1.0).
    flux_err : np.ndarray
        1-sigma flux uncertainties, same length as *flux*.
    period_min : float
        Minimum trial period in days.  Default is 0.5.
    period_max : float
        Maximum trial period in days.  Default is 30.0.
    n_candidates : int
        Number of top candidates to return.  Default is 5.

    Returns
    -------
    list[TransitCandidate]
        Up to *n_candidates* transit candidates sorted by descending SNR.

    Raises
    ------
    TransitError
        If fewer than 10 data points are provided, or if the periodogram
        fails to converge.
    """
    raise NotImplementedError(
        "detect_transit_events() is not yet implemented. "
        "It will run a BLS periodogram over the supplied time/flux arrays "
        "and return the top-N candidates ranked by SNR."
    )


def fit_transit_model(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    candidate: TransitCandidate,
) -> TransitFitResult:
    """Fit a parametric transit model to a phase-folded light curve.

    Uses ``scipy.optimize.minimize`` (or ``batman`` if available) to find the
    maximum-likelihood Mandel-Agol transit parameters given an initial
    ``TransitCandidate`` from :func:`detect_transit_events`.

    Parameters
    ----------
    time : np.ndarray
        Array of observation times in days.
    flux : np.ndarray
        Normalised flux array (median ≈ 1.0).
    flux_err : np.ndarray
        1-sigma flux uncertainties.
    candidate : TransitCandidate
        Initial parameter estimate from :func:`detect_transit_events`.

    Returns
    -------
    TransitFitResult
        Fitted transit parameters and goodness-of-fit statistics.

    Raises
    ------
    TransitError
        If the optimiser fails to converge or the fitted parameters are
        physically implausible (e.g. Rp/Rs > 1).
    """
    raise NotImplementedError(
        "fit_transit_model() is not yet implemented. "
        "It will phase-fold the light curve using candidate.period_days and "
        "candidate.t0, then optimise a Mandel-Agol model with scipy.optimize."
    )
