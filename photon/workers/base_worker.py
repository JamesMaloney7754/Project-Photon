"""QRunnable base class with typed signals.

All long-running operations (FITS loading, plate solving, photometry, catalog
queries) must be dispatched via QThreadPool using a subclass of BaseWorker.
The UI emits a signal to start work and receives results via signals —
the main thread is never blocked.

Usage pattern::

    class MyWorker(BaseWorker):
        def __init__(self, value: int) -> None:
            super().__init__()
            self._value = value

        def execute(self) -> int:
            return self._value * 2

    worker = MyWorker(21)
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


class Signals(QObject):
    """Signals emitted by :class:`BaseWorker`.

    Qt requires signals to be defined on a ``QObject``; ``QRunnable`` is not a
    ``QObject``, so signals live on this separate helper object.

    Signals
    -------
    result : Signal(object)
        Emitted with the return value of :meth:`BaseWorker.execute` on success.
    error : Signal(str)
        Emitted with a formatted traceback string when an unhandled exception
        escapes :meth:`BaseWorker.execute`.
    finished : Signal()
        Always emitted after :meth:`BaseWorker.execute` returns, whether it
        succeeded or raised.
    """

    result: Signal = Signal(object)
    error: Signal = Signal(str)
    finished: Signal = Signal()


class BaseWorker(QRunnable):
    """Abstract QRunnable that wraps ``execute()`` with signal emission.

    Subclasses override :meth:`execute` to implement their work.  The base
    class ``run()`` method calls ``execute()``, emits ``signals.result`` on
    success or ``signals.error`` on exception, then always emits
    ``signals.finished``.

    Do not override ``run()`` — override ``execute()`` instead.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.signals = Signals()

    def run(self) -> None:
        """Called by QThreadPool.  Do not override; override :meth:`execute`."""
        try:
            result = self.execute()
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Worker %s raised %s:\n%s", type(self).__name__, exc, tb)
            self.signals.error.emit(tb)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

    def execute(self) -> Any:
        """Override this method to implement the actual work.

        Returns
        -------
        Any
            The return value is emitted via ``signals.result``.

        Raises
        ------
        Exception
            Any unhandled exception is caught by :meth:`run`, logged, and
            emitted as a formatted traceback string via ``signals.error``.
        """
        raise NotImplementedError(f"{type(self).__name__}.execute() is not implemented.")
