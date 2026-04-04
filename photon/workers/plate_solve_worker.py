"""Plate-solve worker — off-thread wrapper for :func:`photon.core.plate_solver.get_solver`.

Dispatches via :class:`~photon.workers.base_worker.BaseWorker` so the main
thread is never blocked.  Adds a ``progress`` signal for streaming solver
output lines back to the UI.

Usage::

    worker = PlateSolveWorker(image=frame.data, header=frame.header)
    worker.signals.progress.connect(self._on_solve_progress)
    worker.signals.result.connect(self._on_solve_result)
    worker.signals.error.connect(self._on_solve_error)
    worker.signals.finished.connect(self._on_solve_finished)
    QThreadPool.globalInstance().start(worker)
"""

from __future__ import annotations

import logging

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal

logger = logging.getLogger(__name__)


# ── Extended signals ────────────────────────────────────────────────────────────


class PlateSolveSignals(QObject):
    """Signals for :class:`PlateSolveWorker`.

    Signals
    -------
    result : Signal(object)
        Emitted with the ``astropy.wcs.WCS`` on successful solve.
    error : Signal(str)
        Emitted with a formatted traceback string on failure.
    finished : Signal()
        Always emitted when the worker exits.
    progress : Signal(str)
        Emitted with each progress message line streamed from the solver.
    """

    result:   Signal = Signal(object)
    error:    Signal = Signal(str)
    finished: Signal = Signal()
    progress: Signal = Signal(str)


# ── PlateSolveWorker ────────────────────────────────────────────────────────────


class PlateSolveWorker(QRunnable):
    """Off-thread plate-solve worker with a streaming progress signal.

    Parameters
    ----------
    image : np.ndarray
        2-D science image array (float64, calibrated ADU).
    header : astropy.io.fits.Header
        FITS header associated with *image*, used for RA/Dec hints and
        written to the temporary input FITS file.
    """

    def __init__(self, image: np.ndarray, header: object) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._image  = image
        self._header = header
        self.signals = PlateSolveSignals()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _emit_progress(self, msg: str) -> None:
        """Forward a solver status line to the UI via the progress signal."""
        self.signals.progress.emit(msg)

    # ------------------------------------------------------------------
    # QRunnable
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Called by QThreadPool.  Runs the solver; emits result or error."""
        import traceback

        from photon.core.plate_solver import get_solver

        try:
            solver = get_solver()
            wcs = solver.solve(
                self._image,
                self._header,
                progress_callback=self._emit_progress,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("PlateSolveWorker raised %s:\n%s", exc, tb)
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(wcs)
        finally:
            self.signals.finished.emit()
