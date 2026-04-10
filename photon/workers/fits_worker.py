"""Worker that loads a FITS sequence off the main thread.

Dispatches :func:`photon.core.fits_loader.load_fits_sequence` via the
:class:`~photon.workers.base_worker.BaseWorker` pattern so the UI thread is
never blocked by disk I/O.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from photon.core.fits_loader import load_fits_sequence
from photon.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class FitsLoaderWorker(BaseWorker):
    """Load a sequence of FITS files asynchronously.

    On success, ``signals.result`` is emitted with a
    ``(stack, headers)`` tuple where *stack* is an ``np.ndarray`` of shape
    ``(N, height, width)`` and *headers* is a list of
    ``astropy.io.fits.Header`` objects.

    On failure, ``signals.error`` is emitted with a formatted traceback string.

    Parameters
    ----------
    paths : list[Path]
        Ordered list of FITS file paths to load.

    Examples
    --------
    ::

        worker = FitsLoaderWorker([Path("frame1.fits"), Path("frame2.fits")])
        worker.signals.result.connect(self._on_stack_loaded)
        worker.signals.error.connect(self._on_load_error)
        worker.signals.finished.connect(self._on_finished)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, paths: list[Path]) -> None:
        super().__init__()
        self._paths = [Path(p) for p in paths]

    def execute(self) -> tuple[np.ndarray, list]:
        """Load all paths and return ``(image_stack, headers)``.

        Returns
        -------
        tuple[np.ndarray, list]
            ``(stack, headers)`` as returned by
            :func:`~photon.core.fits_loader.load_fits_sequence`.

        Raises
        ------
        FileNotFoundError
            If any path does not exist.
        ValueError
            If the sequence is empty or frames have inconsistent dimensions.
        OSError
            If any file is not a valid FITS file.
        """
        try:
            return load_fits_sequence(self._paths)
        except Exception:
            logger.exception(
                "FitsLoaderWorker: failed to load sequence %s",
                [str(p) for p in self._paths],
            )
            raise
