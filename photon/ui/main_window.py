"""Main application window — Deep Field layout with glass panels."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, QThreadPool, QTimer, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QPen,
    QPolygon,
    QShortcut,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from photon.core.session import PhotonSession
from photon.ui.background_widget import BackgroundWidget
from photon.ui.bottom_bar import BottomBarWidget
from photon.ui.fits_canvas import FitsCanvas
from photon.ui.inspector_panel import InspectorPanel
from photon.ui.pipeline_stepper import PipelineStepperWidget
from photon.ui.session_sidebar import SessionSidebar
from photon.ui.theme import Colors, Typography
from photon.workers.fits_worker import FitsLoaderWorker

logger = logging.getLogger(__name__)


# ── Logo widget (painted hexagon + wordmark) ────────────────────────────────────


class _LogoWidget(QWidget):
    """Paints a violet hexagon followed by the "PHOTON" wordmark."""

    _SIZE = 14  # hexagon apothem in px

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        text_w = 80
        self.setFixedSize(self._SIZE * 2 + 8 + text_w, 40)
        self.setStyleSheet("background-color: transparent;")

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        import math
        cx, cy = self._SIZE + 2, self.height() // 2
        r = self._SIZE
        # Six-sided polygon
        pts = QPolygon()
        for k in range(6):
            angle = math.radians(60 * k - 30)
            pts.append_point(
                int(cx + r * math.cos(angle)),
                int(cy + r * math.sin(angle)),
            )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Colors.VIOLET))
        painter.drawPolygon(pts)

        # "PHOTON" wordmark
        font = QFont("Inter")
        font.setPixelSize(Typography.SIZE_LG)
        font.setWeight(QFont.Weight(Typography.WEIGHT_BOLD))
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        text_x = cx + r + 8
        painter.drawText(text_x, 0, self.width() - text_x, self.height(), 0, "PHOTON")

        painter.end()


# ── Settings gear button ────────────────────────────────────────────────────────


class _GearButton(QToolButton):
    """A 32×32 flat button that paints a gear icon."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setStyleSheet(
            "QToolButton { background-color: transparent; border: none; }"
            "QToolButton:hover { background-color: rgba(255,255,255,10);"
            " border-radius: 6px; }"
        )

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2
        painter.setPen(QPen(QColor(Colors.TEXT_SECONDARY), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Inner circle
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)
        # Outer ring with 8 notches
        for k in range(8):
            angle = math.radians(45 * k)
            x0 = cx + int(7 * math.cos(angle))
            y0 = cy + int(7 * math.sin(angle))
            x1 = cx + int(10 * math.cos(angle))
            y1 = cy + int(10 * math.sin(angle))
            painter.drawLine(x0, y0, x1, y1)
        painter.drawEllipse(cx - 6, cy - 6, 12, 12)
        painter.end()


# ── MainWindow ─────────────────────────────────────────────────────────────────


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
        self.setMinimumSize(1100, 700)
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
        self._stepper   = PipelineStepperWidget()
        self._sidebar   = SessionSidebar()
        self._canvas    = FitsCanvas()
        self._inspector = InspectorPanel()
        self._bottom    = BottomBarWidget()

    def _build_layout(self) -> None:
        """Assemble the full window layout with BackgroundWidget as root."""
        bg = BackgroundWidget()
        root_layout = QVBoxLayout(bg)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ───────────────────────────────────────────────────────
        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        # ── Main splitter (8px margins so gradient shows around panels) ───
        splitter_wrapper = QWidget()
        splitter_wrapper.setStyleSheet("background-color: transparent;")
        sw_layout = QVBoxLayout(splitter_wrapper)
        sw_layout.setContentsMargins(8, 8, 8, 8)
        sw_layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setStyleSheet("QSplitter { background-color: transparent; }")
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._canvas)
        self._splitter.addWidget(self._inspector)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(2, False)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        sw_layout.addWidget(self._splitter)

        root_layout.addWidget(splitter_wrapper, 1)

        # ── Bottom bar ────────────────────────────────────────────────────
        root_layout.addWidget(self._bottom)

        self.setCentralWidget(bg)

    def _build_top_bar(self) -> QWidget:
        """Return the 56px top bar with logo, stepper, and gear button."""
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "background-color: rgba(6, 8, 16, 160);"
            "border-bottom: 1px solid rgba(255, 255, 255, 15);"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        # Logo
        logo = _LogoWidget()
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        # Stepper — centered
        layout.addStretch(1)
        layout.addWidget(self._stepper, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        # Settings gear button with popup menu
        self._gear_btn = _GearButton()
        self._gear_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._gear_btn.setToolTip("Application menu")

        gear_menu = QMenu(self._gear_btn)
        gear_menu.setStyleSheet(
            f"QMenu {{ background-color: {Colors.SURFACE_RAISED};"
            f" border: 1px solid rgba(255,255,255,20); border-radius: 10px;"
            f" padding: 6px 0; color: {Colors.TEXT_PRIMARY}; }}"
            f"QMenu::item {{ padding: 7px 24px 7px 14px; border-radius: 6px;"
            f" margin: 1px 6px; }}"
            f"QMenu::item:selected {{ background-color: {Colors.VIOLET}; }}"
            f"QMenu::separator {{ height: 1px; background-color: {Colors.BORDER};"
            f" margin: 4px 10px; }}"
        )
        gear_menu.addAction("Open Sequence…", self._open_sequence, "Ctrl+O")
        gear_menu.addSeparator()
        gear_menu.addAction("Quit", self.close, "Ctrl+Q")
        self._gear_btn.setMenu(gear_menu)

        layout.addWidget(self._gear_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        return bar

    def _connect_signals(self) -> None:
        self._sidebar.open_requested.connect(self._open_sequence)
        self._canvas.files_dropped.connect(self._load_paths)
        self._sidebar.frame_selected.connect(self._show_frame)
        self._bottom.frame_scrubbed.connect(self._show_frame)
        self._stepper.step_clicked.connect(self._set_pipeline_step)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._open_sequence)
        QShortcut(QKeySequence("Left"),   self).activated.connect(self._prev_frame)
        QShortcut(QKeySequence("Right"),  self).activated.connect(self._next_frame)
        QShortcut(QKeySequence("Space"),  self).activated.connect(self._toggle_play)
        QShortcut(QKeySequence("1"), self).activated.connect(
            lambda: self._set_pipeline_step(0)
        )
        QShortcut(QKeySequence("2"), self).activated.connect(
            lambda: self._set_pipeline_step(1)
        )
        QShortcut(QKeySequence("3"), self).activated.connect(
            lambda: self._set_pipeline_step(2)
        )
        QShortcut(QKeySequence("4"), self).activated.connect(
            lambda: self._set_pipeline_step(3)
        )
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    # ------------------------------------------------------------------
    # Launch animation
    # ------------------------------------------------------------------

    def showEvent(self, event: object) -> None:  # type: ignore[override]
        super().showEvent(event)  # type: ignore[arg-type]
        self._run_launch_animations()

    def _run_launch_animations(self) -> None:
        """Fade the three panels in sequentially on first show."""
        panels = [self._sidebar, self._canvas, self._inspector]
        effects: list[QGraphicsOpacityEffect] = []
        anims:   list[QPropertyAnimation] = []

        for panel in panels:
            eff = QGraphicsOpacityEffect(panel)
            eff.setOpacity(0.0)
            panel.setGraphicsEffect(eff)
            effects.append(eff)

            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setDuration(300)
            anims.append(anim)

        offsets_ms = [0, 100, 200]
        for i, (anim, delay) in enumerate(zip(anims, offsets_ms)):
            QTimer.singleShot(delay, anim.start)

        # Remove effects after all animations complete to avoid paint artifacts
        def _cleanup() -> None:
            for panel in panels:
                panel.setGraphicsEffect(None)

        QTimer.singleShot(offsets_ms[-1] + 350, _cleanup)

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
        self._bottom.set_progress(0, 0)

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
