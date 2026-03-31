"""Main application window — Observatory Glass layout."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from photon.core.session import PhotonSession
from photon.ui.bottom_bar import BottomBarWidget
from photon.ui.fits_canvas import FitsCanvas
from photon.ui.inspector_panel import InspectorPanel
from photon.ui.pipeline_stepper import PipelineStepperWidget
from photon.ui.session_sidebar import SessionSidebar
from photon.ui.theme import Colors, Typography
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
        self._pending_paths: list[Path] = []
        self._current_frame: int = 0
        self._current_step: int = 0

        # Frame playback timer (10 fps)
        self._play_timer = QTimer(self)
        self._play_timer.setInterval(100)
        self._play_timer.timeout.connect(self._advance_frame)

        self.setWindowTitle("Photon")
        self.setMinimumSize(1100, 680)
        # Remove the default QMenuBar — navigation lives in the logo menu
        self.setMenuBar(None)  # type: ignore[arg-type]

        self._build_components()
        self._build_layout()
        self._connect_signals()
        self._register_shortcuts()

        logger.info("MainWindow initialised.")

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_components(self) -> None:
        """Instantiate all child widgets."""
        self._stepper  = PipelineStepperWidget()
        self._sidebar  = SessionSidebar()
        self._canvas   = FitsCanvas()
        self._inspector = InspectorPanel()
        self._bottom   = BottomBarWidget()

    def _build_layout(self) -> None:
        """Assemble the full window layout."""
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────
        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        # ── Main splitter ─────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._canvas)
        self._splitter.addWidget(self._inspector)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(2, False)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        root_layout.addWidget(self._splitter, 1)

        # ── Bottom bar ────────────────────────────────────────────────
        root_layout.addWidget(self._bottom)

        self.setCentralWidget(root)

    def _build_top_bar(self) -> QWidget:
        """Return the 48 px top bar with logo and pipeline stepper."""
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            f"background-color: {Colors.SURFACE};"
            f"border-bottom: 1px solid {Colors.BORDER};"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        # Logo tool-button with popup menu (right-click or click arrow)
        self._logo_btn = QToolButton()
        self._logo_btn.setText("⬡  PHOTON")
        self._logo_btn.setStyleSheet(
            f"""
            QToolButton {{
                font-size: {Typography.SIZE_LG}px;
                font-weight: bold;
                color: {Colors.ACCENT_PRIMARY};
                background: transparent;
                border: none;
                padding: 4px 8px;
                letter-spacing: 2px;
            }}
            QToolButton:hover {{
                background-color: {Colors.SURFACE_ALT};
                border-radius: 6px;
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
            """
        )
        self._logo_btn.setPopupMode(QToolButton.InstantPopup)
        self._logo_btn.setToolTip("Click for application menu")

        logo_menu = QMenu(self._logo_btn)
        logo_menu.setStyleSheet(
            f"QMenu {{ background-color: {Colors.SURFACE}; border: 1px solid {Colors.BORDER};"
            f" border-radius: 6px; padding: 4px 0; color: {Colors.TEXT_PRIMARY}; }}"
            f"QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; margin: 1px 4px; }}"
            f"QMenu::item:selected {{ background-color: {Colors.ACCENT_PRIMARY}; }}"
            f"QMenu::separator {{ height: 1px; background-color: {Colors.BORDER};"
            f" margin: 4px 8px; }}"
        )
        logo_menu.addAction("Open Sequence…", self._open_sequence, "Ctrl+O")
        logo_menu.addSeparator()
        logo_menu.addAction("Quit", self.close, "Ctrl+Q")
        self._logo_btn.setMenu(logo_menu)

        layout.addWidget(self._logo_btn)
        layout.addSpacing(40)
        layout.addWidget(self._stepper, 1)

        return bar

    def _connect_signals(self) -> None:
        """Wire all inter-widget signals."""
        self._sidebar.open_requested.connect(self._open_sequence)
        self._canvas.files_dropped.connect(self._load_paths)
        self._sidebar.frame_selected.connect(self._show_frame)
        self._bottom.frame_scrubbed.connect(self._show_frame)
        self._stepper.step_clicked.connect(self._set_pipeline_step)

    def _register_shortcuts(self) -> None:
        """Register global keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._open_sequence)
        QShortcut(QKeySequence("Left"),   self).activated.connect(self._prev_frame)
        QShortcut(QKeySequence("Right"),  self).activated.connect(self._next_frame)
        QShortcut(QKeySequence("Space"),  self).activated.connect(self._toggle_play)
        QShortcut(QKeySequence("1"), self).activated.connect(lambda: self._set_pipeline_step(0))
        QShortcut(QKeySequence("2"), self).activated.connect(lambda: self._set_pipeline_step(1))
        QShortcut(QKeySequence("3"), self).activated.connect(lambda: self._set_pipeline_step(2))
        QShortcut(QKeySequence("4"), self).activated.connect(lambda: self._set_pipeline_step(3))
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    # ------------------------------------------------------------------
    # Loading flow
    # ------------------------------------------------------------------

    def _open_sequence(self) -> None:
        """Open a file dialog and kick off the loading worker."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open FITS Sequence",
            "",
            "FITS Files (*.fits *.fit);;All Files (*)",
        )
        if paths:
            self._load_paths([Path(p) for p in paths])

    def _load_paths(self, paths: list[Path]) -> None:
        """Start a :class:`~photon.workers.fits_worker.FitsLoaderWorker` for *paths*.

        Parameters
        ----------
        paths : list[Path]
            Ordered FITS paths to load.
        """
        self._pending_paths = list(paths)
        self._bottom.set_status("Loading…")
        self._bottom.show_progress(True)
        self._bottom.set_progress(0, 0)  # indeterminate

        worker = FitsLoaderWorker(paths)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._bottom.show_progress(False))
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_loaded(self, payload: object) -> None:
        """Populate the session and all widgets on successful load.

        Parameters
        ----------
        payload : tuple[np.ndarray, list]
            ``(image_stack, headers)`` from the worker.
        """
        stack, headers = payload  # type: ignore[misc]

        self.session.image_stack = stack
        self.session.headers     = headers
        self.session.fits_paths  = self._pending_paths

        n = stack.shape[0]
        self._current_frame = 0

        self._bottom.configure_scrubber(n)
        self._sidebar.populate(self.session, headers)
        self._show_frame(0)

        self._stepper.set_step_complete(0)
        self._stepper.set_active_step(0)
        self._inspector.set_step(0)

        self._bottom.set_status(f"Loaded {n} frame{'s' if n != 1 else ''}")
        logger.info("Stack loaded: shape %s", stack.shape)

    def _on_error(self, traceback_str: str) -> None:
        """Show a critical dialog on worker failure."""
        last_line = traceback_str.strip().splitlines()[-1]
        self._bottom.set_status(f"Error: {last_line}")
        logger.error("FitsLoaderWorker error:\n%s", traceback_str)
        QMessageBox.critical(self, "Load Error", last_line)

    # ------------------------------------------------------------------
    # Frame navigation
    # ------------------------------------------------------------------

    def _show_frame(self, index: int) -> None:
        """Display frame *index* and sync all widgets.

        Parameters
        ----------
        index : int
            Frame index into ``session.image_stack``.
        """
        if self.session.image_stack is None:
            return
        n = self.session.image_stack.shape[0]
        index = max(0, min(index, n - 1))
        self._current_frame = index

        header = (
            self.session.headers[index]
            if index < len(self.session.headers)
            else None
        )
        self._canvas.display_frame(self.session.image_stack[index], header)
        self._inspector.update_file_info(header)
        if index < len(self.session.fits_paths):
            self._inspector.set_current_frame_path(self.session.fits_paths[index])

        # Sync sidebar and scrubber without re-triggering their signals
        self._sidebar.set_selected_frame(index)
        self._bottom.set_frame(index)

    def _prev_frame(self) -> None:
        self._show_frame(self._current_frame - 1)

    def _next_frame(self) -> None:
        self._show_frame(self._current_frame + 1)

    def _advance_frame(self) -> None:
        if self.session.image_stack is None:
            return
        n = self.session.image_stack.shape[0]
        self._show_frame((self._current_frame + 1) % n)

    def _toggle_play(self) -> None:
        if self._play_timer.isActive():
            self._play_timer.stop()
            self._bottom.set_status("Paused")
        else:
            if self.session.image_stack is not None:
                self._play_timer.start()
                self._bottom.set_status("Playing…")

    # ------------------------------------------------------------------
    # Pipeline step switching
    # ------------------------------------------------------------------

    def _set_pipeline_step(self, index: int) -> None:
        """Switch the active pipeline step.

        Parameters
        ----------
        index : int
            Step index ``[0, 3]``.
        """
        index = max(0, min(index, 3))
        self._current_step = index
        self._stepper.set_active_step(index)
        self._inspector.set_step(index)
