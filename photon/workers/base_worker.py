"""QRunnable base class with typed signals.

All long-running operations (FITS loading, plate solving, photometry, catalog
queries) must be dispatched via QThreadPool using a subclass of BaseWorker.
The UI emits a signal to start work and receives results via signals —
the main thread is never blocked.

Usage pattern::

    worker = MyWorker(arg1, arg2)
    worker.signals.result.connect(self.on_result)
    worker.signals.error.connect(self.on_error)
    worker.signals.finished.connect(self.on_finished)
    QThreadPool.globalInstance().start(worker)
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Signals emitted by :class:`BaseWorker`.

    Qt requires signals to be defined on a ``QObject``; ``QRunnable`` is not a
    ``QObject``, so signals live on a separate helper object.

    Signals
    -------
    started
        Emitted immediately before the worker function runs.
    result
        Emitted with the return value of :meth:`BaseWorker.run_task`.
    error
        Emitted with ``(exception_type, exception_value, traceback_str)`` when
        an unhandled exception escapes :meth:`BaseWorker.run_task`.
    progress
        Emitted with an integer 0–100 progress value from inside the task.
    finished
        Emitted after :meth:`BaseWorker.run_task` returns (success or error).
    """

    started: Signal = Signal()
    result: Signal = Signal(object)
    error: Signal = Signal(object, object, str)
    progress: Signal = Signal(int)
    finished: Signal = Signal()


class BaseWorker(QRunnable):
    """Abstract QRunnable that emits typed signals.

    Subclasses override :meth:`run_task` and may call
    ``self.signals.progress.emit(n)`` to report incremental progress.

    Parameters
    ----------
    *args : Any
        Positional arguments forwarded to :meth:`run_task`.
    **kwargs : Any
        Keyword arguments forwarded to :meth:`run_task`.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.signals = WorkerSignals()
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        """Called by QThreadPool — do not override; override :meth:`run_task`."""
        self.signals.started.emit()
        try:
            result = self.run_task(*self._args, **self._kwargs)
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Worker %s failed: %s\n%s", type(self).__name__, exc, tb)
            self.signals.error.emit(type(exc), exc, tb)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

    def run_task(self, *args: Any, **kwargs: Any) -> Any:
        """Override this method to implement the actual work.

        Parameters
        ----------
        *args : Any
            Forwarded from the constructor.
        **kwargs : Any
            Forwarded from the constructor.

        Returns
        -------
        Any
            Returned value is emitted via ``signals.result``.

        Raises
        ------
        Exception
            Any unhandled exception is caught by :meth:`run`, logged, and
            emitted via ``signals.error``.
        """
        raise NotImplementedError(f"{type(self).__name__}.run_task() is not implemented.")
