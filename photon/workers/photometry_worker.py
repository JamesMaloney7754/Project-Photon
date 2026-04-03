"""Worker that runs differential aperture photometry off the main thread."""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

from photon.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PhotometryWorker(BaseWorker):
    """Runs aperture photometry and builds a light curve in a thread pool.

    Parameters
    ----------
    image_stack : np.ndarray
        3-D array ``(N_frames, H, W)`` in calibrated ADU.
    target_xy : tuple[float, float]
        Pixel coordinates of the target star.
    comparison_xys : list[tuple[float, float]]
        Pixel coordinates of comparison stars.
    aperture_radius : float
        Source aperture radius in pixels.
    annulus_inner : float
        Sky annulus inner radius in pixels.
    annulus_outer : float
        Sky annulus outer radius in pixels.
    observation_times : object or None
        ``astropy.time.Time`` array for the frames, or ``None``.
    frame_flags : np.ndarray or None
        Boolean exclusion mask, same length as N_frames.
    """

    def __init__(
        self,
        image_stack: np.ndarray,
        target_xy: tuple[float, float],
        comparison_xys: list[tuple[float, float]],
        *,
        aperture_radius: float = 8.0,
        annulus_inner: float = 12.0,
        annulus_outer: float = 20.0,
        observation_times: Optional[object] = None,
        frame_flags: Optional[np.ndarray] = None,
    ) -> None:
        super().__init__()
        self._image_stack      = image_stack
        self._target_xy        = target_xy
        self._comparison_xys   = comparison_xys
        self._aperture_radius  = aperture_radius
        self._annulus_inner    = annulus_inner
        self._annulus_outer    = annulus_outer
        self._observation_times = observation_times
        self._frame_flags      = frame_flags

    def execute(self) -> Any:
        """Run photometry and build a light curve.

        Returns
        -------
        dict
            ``{"photometry": result_dict, "light_curve": table}`` where
            *result_dict* is from
            :func:`~photon.core.photometry.run_aperture_photometry` and
            *table* is from :func:`~photon.core.photometry.build_light_curve`.
        """
        from photon.core.photometry import build_light_curve, run_aperture_photometry

        logger.debug(
            "PhotometryWorker: stack %s, target %s, %d comparisons",
            self._image_stack.shape, self._target_xy, len(self._comparison_xys),
        )
        result = run_aperture_photometry(
            self._image_stack,
            self._target_xy,
            self._comparison_xys,
            aperture_radius=self._aperture_radius,
            annulus_inner=self._annulus_inner,
            annulus_outer=self._annulus_outer,
        )
        table = build_light_curve(
            result["differential_mag"],
            self._observation_times,
            frame_flags=self._frame_flags,
        )
        return {"photometry": result, "light_curve": table}
