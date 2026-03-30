"""Main application window.

Owns a single ``PhotonSession`` and orchestrates all user interactions.
All I/O is dispatched through workers — the main thread is never blocked.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QTabWidget,
    QToolBar,
    QWidget,
)

from photon.core.session import PhotonSession
from photon.ui.fits_canvas import FitsCanvas
from photon.ui.light_curve_panel import LightCurvePanel
from photon.ui.transit_panel import TransitPanel
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
        self._session = PhotonSession()
        self._thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("Photon — Astrophotography Science")
        self.setMinimumSize(1100, 700)

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()

        logger.info("MainWindow initialised.")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Create central widget layout."""
        splitter = QSplitter(Qt.Horizontal)

        self._fits_canvas = FitsCanvas()
        self._fits_canvas.pixel_clicked.connect(self._on_pixel_clicked)
        splitter.addWidget(self._fits_canvas)

        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(LightCurvePanel(), "Light Curve")
        self._tab_widget.addTab(TransitPanel(), "Transit Fit")
        splitter.addWidget(self._tab_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    def _build_menu(self) -> None:
        """Create the application menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&Open FITS…", self._open_fits, "Ctrl+O")
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close, "Ctrl+Q")

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction("asinh stretch", lambda: self._apply_stretch("asinh"))
        view_menu.addAction("linear stretch", lambda: self._apply_stretch("linear"))
        view_menu.addAction("sqrt stretch", lambda: self._apply_stretch("sqrt"))
        view_menu.addAction("log stretch", lambda: self._apply_stretch("log"))

    def _build_toolbar(self) -> None:
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction("Open FITS", self._open_fits)

    def _build_status_bar(self) -> None:
        """Set up the status bar with a message label and progress bar."""
        self._status_label = QLabel("Ready.")
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(150)
        self._progress_bar.setVisible(False)

        self.statusBar().addWidget(self._status_label, 1)
        self.statusBar().addPermanentWidget(self._progress_bar)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_fits(self) -> None:
        """Show a file dialog and dispatch a FitsLoaderWorker for the selection."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open FITS File(s)",
            "",
            "FITS Files (*.fits *.fit *.fts);;All Files (*)",
        )
        if not paths:
            return
        self._load_fits_async([Path(p) for p in paths])

    def _load_fits_async(self, paths: list[Path]) -> None:
        """Dispatch a :class:`~photon.workers.fits_worker.FitsLoaderWorker`.

        Parameters
        ----------
        paths : list[Path]
            FITS files to load as a sequence.
        """
        names = ", ".join(p.name for p in paths[:3])
        suffix = f" (+{len(paths) - 3} more)" if len(paths) > 3 else ""
        self._set_status(f"Loading {names}{suffix}…")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # indeterminate

        worker = FitsLoaderWorker(paths)
        worker.signals.result.connect(self._on_stack_loaded)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(self._on_worker_finished)
        self._thread_pool.start(worker)

    def _apply_stretch(self, stretch: str) -> None:
        """Restretch the currently displayed frame.

        Parameters
        ----------
        stretch : str
            Stretch algorithm name passed to :func:`~photon.utils.stretch.stretch_image`.
        """
        if not self._session.is_loaded:
            return
        self._fits_canvas.display_data(self._session.image_stack[0], stretch=stretch)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_stack_loaded(self, payload: object) -> None:
        """Handle a successfully loaded ``(stack, headers)`` tuple.

        Parameters
        ----------
        payload : tuple[np.ndarray, list]
            Return value from :class:`~photon.workers.fits_worker.FitsLoaderWorker`.
        """
        if not isinstance(payload, tuple) or len(payload) != 2:
            logger.error("Unexpected payload type from FitsLoaderWorker: %s", type(payload))
            return

        stack, headers = payload
        self._session.image_stack = stack
        self._session.headers = headers

        n = stack.shape[0]
        h, w = stack.shape[1], stack.shape[2]
        self._fits_canvas.display_data(stack[0])
        self._set_status(
            f"Loaded {n} frame(s) — {h} × {w} px"
            + (" | WCS present" if self._session.is_plate_solved else "")
        )
        logger.info("Stack loaded: shape %s", stack.shape)

    def _on_worker_error(self, traceback_str: str) -> None:
        """Display a worker error in the status bar.

        Parameters
        ----------
        traceback_str : str
            Formatted traceback from the worker.
        """
        # Show just the last line (the exception message) in the status bar
        last_line = traceback_str.strip().splitlines()[-1]
        self._set_status(f"Error: {last_line}")
        logger.error("Worker error:\n%s", traceback_str)

    def _on_worker_finished(self) -> None:
        """Hide the progress bar when the worker finishes."""
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 100)

    def _on_pixel_clicked(self, x: float, y: float) -> None:
        """Show pixel coordinates and value in the status bar.

        Parameters
        ----------
        x : float
            Pixel x-coordinate (column).
        y : float
            Pixel y-coordinate (row).
        """
        if not self._session.is_loaded:
            return
        data = self._session.image_stack[0]
        xi, yi = int(round(x)), int(round(y))
        if 0 <= yi < data.shape[0] and 0 <= xi < data.shape[1]:
            value = data[yi, xi]
            msg = f"Pixel ({xi}, {yi}) = {value:.1f} ADU"
            if self._session.wcs is not None:
                try:
                    sky = self._session.wcs.pixel_to_world(x, y)
                    msg += f"  |  RA {sky.ra.deg:.5f}° Dec {sky.dec.deg:.5f}°"
                except Exception:
                    pass
            self._set_status(msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, message: str) -> None:
        """Update the status bar label.

        Parameters
        ----------
        message : str
            Message to display.
        """
        self._status_label.setText(message)
