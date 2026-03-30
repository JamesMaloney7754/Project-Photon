"""Main application window.

Owns a single ``PhotonSession`` and orchestrates all user interactions.
All I/O is dispatched through workers — the main thread is never blocked.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QDockWidget,
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
from photon.workers.fits_worker import FitsWorker

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

        # Left: FITS canvas
        self._fits_canvas = FitsCanvas()
        self._fits_canvas.pixel_clicked.connect(self._on_pixel_clicked)
        splitter.addWidget(self._fits_canvas)

        # Right: tabbed analysis panels
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
        view_menu.addAction("ZScale stretch", lambda: self._apply_stretch("asinh", "zscale"))
        view_menu.addAction("Linear stretch", lambda: self._apply_stretch("linear", "minmax"))
        view_menu.addAction("Sqrt stretch", lambda: self._apply_stretch("sqrt", "zscale"))

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
        """Show a file dialog and dispatch a FitsWorker to load the selection."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open FITS File(s)",
            "",
            "FITS Files (*.fits *.fit *.fts);;All Files (*)",
        )
        if not paths:
            return
        for path in paths:
            self._load_fits_async(Path(path))

    def _load_fits_async(self, path: Path) -> None:
        """Dispatch a :class:`~photon.workers.fits_worker.FitsWorker` for *path*.

        Parameters
        ----------
        path : Path
            FITS file to load.
        """
        self._set_status(f"Loading {path.name}…")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # indeterminate

        worker = FitsWorker(path)
        worker.signals.result.connect(self._on_fits_loaded)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(self._on_worker_finished)
        self._thread_pool.start(worker)

    def _apply_stretch(self, stretch: str, interval: str) -> None:
        """Restretch the currently displayed frame.

        Parameters
        ----------
        stretch : str
            Stretch algorithm name.
        interval : str
            Interval algorithm name.
        """
        if not self._session.frames:
            return
        frame = self._session.frames[-1]
        self._fits_canvas.display_frame(frame.data, stretch=stretch, interval=interval)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_fits_loaded(self, frame: object) -> None:
        """Handle a successfully loaded FitsFrame.

        Parameters
        ----------
        frame : FitsFrame
            The loaded frame (typed as ``object`` to satisfy Qt signal rules).
        """
        from photon.core.session import FitsFrame

        if not isinstance(frame, FitsFrame):
            logger.error("Unexpected result type from FitsWorker: %s", type(frame))
            return

        self._session.add_frame(frame)
        self._fits_canvas.display_frame(frame.data)
        wcs_status = " (WCS present)" if frame.wcs is not None else ""
        self._set_status(f"Loaded {frame.path.name}{wcs_status} — {self._session.frame_count} frame(s).")
        logger.info("Frame added to session: %s", frame.path.name)

    def _on_worker_error(self, exc_type: object, exc: object, tb: str) -> None:
        """Display worker error in the status bar.

        Parameters
        ----------
        exc_type : type
            Exception class.
        exc : Exception
            Exception instance.
        tb : str
            Formatted traceback string.
        """
        self._set_status(f"Error: {exc}")
        logger.error("Worker error: %s\n%s", exc, tb)

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
        if not self._session.frames:
            return
        data = self._session.frames[-1].data
        xi, yi = int(round(x)), int(round(y))
        if 0 <= yi < data.shape[0] and 0 <= xi < data.shape[1]:
            value = data[yi, xi]
            self._set_status(f"Pixel ({xi}, {yi}) = {value:.1f} ADU")
        # Check WCS
        wcs = self._session.frames[-1].wcs
        if wcs is not None:
            try:
                sky = wcs.pixel_to_world(x, y)
                self._set_status(
                    self._status_label.text()
                    + f"  |  RA {sky.ra.deg:.5f}° Dec {sky.dec.deg:.5f}°"
                )
            except Exception:
                pass

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
