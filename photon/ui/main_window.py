"""Main application window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
)

from photon.core.session import PhotonSession
from photon.ui.fits_canvas import FitsCanvas
from photon.workers.fits_worker import FitsLoaderWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level application window for Photon.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = PhotonSession()

        self.setWindowTitle("Photon")
        self.setMinimumSize(900, 600)

        self._build_central()
        self._build_menu()
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        """Create the splitter layout with file list and canvas."""
        splitter = QSplitter(Qt.Horizontal)

        self._file_list = QListWidget()
        self._file_list.setFixedWidth(280)
        self._file_list.currentRowChanged.connect(self._on_row_changed)
        splitter.addWidget(self._file_list)

        self._canvas = FitsCanvas()
        splitter.addWidget(self._canvas)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    def _build_menu(self) -> None:
        """Create the menu bar."""
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Open FITS Sequence…", self._open_sequence, "Ctrl+O")
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close, "Ctrl+Q")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_sequence(self) -> None:
        """Open a file dialog and load the selected FITS files."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open FITS Sequence",
            "",
            "FITS Files (*.fits *.fit);;All Files (*)",
        )
        if not paths:
            return

        self.statusBar().showMessage("Loading…")
        worker = FitsLoaderWorker([Path(p) for p in paths])
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_loaded(self, payload: object) -> None:
        """Populate the session, file list, and canvas on success.

        Parameters
        ----------
        payload : tuple[np.ndarray, list]
            ``(image_stack, headers)`` from :class:`FitsLoaderWorker`.
        """
        stack, headers = payload  # type: ignore[misc]

        self.session.image_stack = stack
        self.session.headers = headers
        self.session.fits_paths = []  # paths not stored separately by worker

        self._file_list.clear()
        for i in range(stack.shape[0]):
            obj = headers[i].get("OBJECT", f"Frame {i}")
            filt = headers[i].get("FILTER", "")
            label = f"{obj}  [{filt}]" if filt else obj
            self._file_list.addItem(label)

        self._canvas.display_frame(stack[0], headers[0])
        self._file_list.setCurrentRow(0)

        n = stack.shape[0]
        self.statusBar().showMessage(f"Loaded {n} frame{'s' if n != 1 else ''}")
        logger.info("Loaded stack shape %s", stack.shape)

    def _on_error(self, traceback_str: str) -> None:
        """Show a critical dialog on worker failure.

        Parameters
        ----------
        traceback_str : str
            Formatted traceback from the worker.
        """
        last_line = traceback_str.strip().splitlines()[-1]
        self.statusBar().showMessage("Error")
        logger.error("FitsLoaderWorker error:\n%s", traceback_str)
        QMessageBox.critical(self, "Load Error", last_line)

    def _on_row_changed(self, row: int) -> None:
        """Display the frame corresponding to *row* in the file list.

        Parameters
        ----------
        row : int
            Selected row index (equals frame index in the stack).
        """
        if self.session.image_stack is None:
            return
        if row < 0 or row >= self.session.image_stack.shape[0]:
            return
        header = self.session.headers[row] if row < len(self.session.headers) else None
        self._canvas.display_frame(self.session.image_stack[row], header)
