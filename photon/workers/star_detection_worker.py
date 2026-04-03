"""Worker that runs star detection off the main thread."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from photon.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class StarDetectionWorker(BaseWorker):
    """Runs :func:`photon.core.star_detector.detect_stars` in a thread pool.

    Parameters
    ----------
    image : np.ndarray
        2-D calibrated frame to search for stars.
    fwhm : float
        Expected stellar FWHM in pixels.
    threshold_sigma : float
        Detection threshold in background-sigma units.
    """

    def __init__(
        self,
        image: np.ndarray,
        fwhm: float = 3.0,
        threshold_sigma: float = 5.0,
    ) -> None:
        super().__init__()
        self._image = image
        self._fwhm = fwhm
        self._threshold_sigma = threshold_sigma

    def execute(self) -> Any:
        """Detect stars and return an ``astropy.table.Table``.

        Returns
        -------
        astropy.table.Table
            Detection results from :func:`~photon.core.star_detector.detect_stars`.
        """
        from photon.core.star_detector import detect_stars

        logger.debug(
            "StarDetectionWorker: image shape %s, fwhm=%.1f, sigma=%.1f",
            self._image.shape, self._fwhm, self._threshold_sigma,
        )
        return detect_stars(
            self._image,
            fwhm=self._fwhm,
            threshold_sigma=self._threshold_sigma,
        )
