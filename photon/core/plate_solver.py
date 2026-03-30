"""Plate-solver interface and concrete implementations.

Architecture note: ``PlateSolver`` is an abstract base class.  UI code must
only call ``PlateSolver.solve()`` — never touch astroquery or subprocess
directly from the UI layer.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class PlateSolverError(Exception):
    """Raised when plate solving fails for any reason."""


class PlateSolver(abc.ABC):
    """Abstract interface for plate-solving backends.

    Subclasses implement :meth:`solve` and may expose backend-specific
    constructor parameters.
    """

    @abc.abstractmethod
    def solve(
        self,
        data: np.ndarray,
        header: dict[str, Any],
        *,
        ra_hint: float | None = None,
        dec_hint: float | None = None,
        radius_deg: float = 5.0,
    ) -> dict[str, Any]:
        """Attempt to plate-solve *data* and return WCS header keywords.

        Parameters
        ----------
        data : np.ndarray
            2-D image array (float32 counts).
        header : dict[str, Any]
            Original FITS header — may supply hints like OBJCTRA/OBJCTDEC.
        ra_hint : float | None
            Initial RA guess in degrees, or ``None`` for a blind solve.
        dec_hint : float | None
            Initial Dec guess in degrees, or ``None`` for a blind solve.
        radius_deg : float
            Search radius in degrees around the hint position.

        Returns
        -------
        dict[str, Any]
            Dictionary of WCS FITS header keywords (e.g. ``CRPIX1``, ``CRVAL1``,
            ``CD1_1``, …) that can be merged into the frame header.

        Raises
        ------
        PlateSolverError
            If solving fails or times out.
        """


class AstrometryNetSolver(PlateSolver):
    """Cloud plate solver using the Astrometry.net web API via astroquery.

    Parameters
    ----------
    api_key : str
        Astrometry.net API key.  Obtain one from https://nova.astrometry.net.
    timeout_s : int
        Maximum seconds to wait for the solve job to complete.
    """

    def __init__(self, api_key: str, timeout_s: int = 120) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def solve(
        self,
        data: np.ndarray,
        header: dict[str, Any],
        *,
        ra_hint: float | None = None,
        dec_hint: float | None = None,
        radius_deg: float = 5.0,
    ) -> dict[str, Any]:
        """Submit image to Astrometry.net and return WCS header keywords.

        Parameters
        ----------
        data : np.ndarray
            2-D image array.
        header : dict[str, Any]
            FITS header — used to extract RA/Dec hints if not supplied.
        ra_hint : float | None
            RA hint in degrees.
        dec_hint : float | None
            Dec hint in degrees.
        radius_deg : float
            Search radius in degrees.

        Returns
        -------
        dict[str, Any]
            WCS keywords from the solved header.

        Raises
        ------
        PlateSolverError
            On any failure (network, bad key, timeout, no solution).
        """
        # Import deferred so the core module doesn't pay the import cost unless used.
        try:
            from astroquery.astrometry_net import AstrometryNet  # type: ignore[import]
        except ImportError as exc:
            raise PlateSolverError(
                "astroquery.astrometry_net is not available. "
                "Ensure astroquery>=0.4.7 is installed."
            ) from exc

        ast = AstrometryNet()
        ast.api_key = self._api_key

        logger.info("Submitting image to Astrometry.net (timeout %ds)…", self._timeout_s)

        kwargs: dict[str, Any] = {
            "solve_timeout": self._timeout_s,
            "force_image_upload": True,
        }
        if ra_hint is not None and dec_hint is not None:
            kwargs["center_ra"] = ra_hint
            kwargs["center_dec"] = dec_hint
            kwargs["radius"] = radius_deg

        try:
            wcs_header = ast.solve_from_image(
                data,
                submission_id=None,
                **kwargs,
            )
        except Exception as exc:
            raise PlateSolverError(f"Astrometry.net solve failed: {exc}") from exc

        if not wcs_header:
            raise PlateSolverError("Astrometry.net returned no WCS solution.")

        logger.info("Astrometry.net solve succeeded.")
        return dict(wcs_header)
