"""Plate-solver interface and concrete implementations.

This module defines the abstract ``PlateSolver`` base class and the
``AstrometryNetSolver`` concrete implementation that submits images to the
Astrometry.net cloud API via ``astroquery``.

Architecture note: UI code must only call ``PlateSolver.solve()`` — never
touch ``astroquery.astrometry_net`` or subprocess plate-solve binaries
directly from the UI layer.  Future backends (e.g. a local ``solve-field``
subprocess) implement the same interface.
"""

from __future__ import annotations

import abc

import numpy as np


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
        image: np.ndarray,
        header: object,
    ) -> object:
        """Attempt to plate-solve *image* and return an astropy WCS object.

        Parameters
        ----------
        image : np.ndarray
            2-D science image array (float64, calibrated ADU).
        header : astropy.io.fits.Header
            FITS header associated with *image*.  May contain RA/Dec hint
            keywords (``OBJCTRA``, ``OBJCTDEC``) used to seed the search.

        Returns
        -------
        astropy.wcs.WCS
            Fully initialised WCS object representing the plate solution.

        Raises
        ------
        PlateSolverError
            If the solve attempt fails, times out, or returns no solution.
        """


class AstrometryNetSolver(PlateSolver):
    """Cloud plate solver using the Astrometry.net web API via astroquery.

    Parameters
    ----------
    api_key : str
        Astrometry.net API key obtained from https://nova.astrometry.net.
    timeout_s : int
        Maximum seconds to wait for the job to complete.  Default is 120.
    """

    def __init__(self, api_key: str, timeout_s: int = 120) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def solve(
        self,
        image: np.ndarray,
        header: object,
    ) -> object:
        """Submit *image* to Astrometry.net and return a WCS solution.

        Parameters
        ----------
        image : np.ndarray
            2-D science image array (float64, calibrated ADU).
        header : astropy.io.fits.Header
            FITS header; ``OBJCTRA`` / ``OBJCTDEC`` are used as search hints
            when present.

        Returns
        -------
        astropy.wcs.WCS
            Plate solution as an astropy WCS object.

        Raises
        ------
        PlateSolverError
            On any failure: network error, bad API key, timeout, or no
            solution found within the search radius.
        """
        raise NotImplementedError(
            "AstrometryNetSolver.solve() is not yet implemented. "
            "It will use astroquery.astrometry_net to submit the image "
            "and poll for the WCS solution."
        )
