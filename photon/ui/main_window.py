"""Main application window — Deep Field layout with glass panels."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QPoint, QPropertyAnimation, QThreadPool, QTimer, Qt
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
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from photon.core.session import PhotonSession
from photon.core.settings_manager import get_settings_manager
from photon.core.star_detector import select_comparison_stars, snap_to_nearest_star
from photon.ui.background_widget import BackgroundWidget
from photon.ui.bottom_bar import BottomBarWidget
from photon.ui.fits_canvas import FitsCanvas
from photon.ui.inspector_panel import InspectorPanel
from photon.ui.light_curve_panel import LightCurvePanel
from photon.ui.photometry_panel import PhotometryPanel
from photon.ui.pipeline_stepper import PipelineStepperWidget
from photon.ui.session_sidebar import SessionSidebar
from photon.ui.theme import Colors, Typography
from photon.workers.fits_worker import FitsLoaderWorker
from photon.workers.photometry_worker import PhotometryWorker
from photon.workers.star_detection_worker import StarDetectionWorker

logger = logging.getLogger(__name__)


# ── Diagnostics log handler + dialog ────────────────────────────────────────────────


class QtLogHandler(logging.Handler):
    """A logging.Handler that appends formatted records to a QPlainTextEdit."""

    def __init__(self, widget: QPlainTextEdit) -> None:
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        QMetaObject.invokeMethod(
            self.widget,
            "appendPlainText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, msg),
        )


class _DiagnosticsDialog(QDialog):
    """A floating window showing the application log stream."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Photon Diagnostics")
        self.resize(700, 400)
        self.setWindowFlag(Qt.WindowType.Window)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.text_widget = QPlainTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setMaximumBlockCount(2000)
        self.text_widget.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background-color: {Colors.CANVAS_BG};"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  font-family: {Typography.FONT_MONO};"
            f"  font-size: {Typography.SIZE_SM}px;"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: 6px;"
            f"}}"
        )
        layout.addWidget(self.text_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(copy_btn)
        save_btn = QPushButton("Save Log…")
        save_btn.clicked.connect(self._save_log)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.text_widget.clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    def _copy_to_clipboard(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text_widget.toPlainText())

    def _save_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", str(Path.home() / "photon_debug.log"),
            "Text Files (*.log *.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.text_widget.toPlainText())
            except OSError as exc:
                logger.error("Failed to save log: %s", exc)


# ── Logo widget (painted hexagon + wordmark) ───────────────────────────────────────────────


class _LogoWidget(QWidget):
    """Paints a violet hexagon followed by the \"PHOTON\" wordmark."""

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
        points = [
            QPoint(int(cx + r * math.cos(math.radians(60 * k - 30))),
                   int(cy + r * math.sin(math.radians(60 * k - 30))))
            for k in range(6)
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Colors.VIOLET))
        painter.drawPolygon(QPolygon(points))

        # "PHOTON" wordmark
        font = QFont("Inter")
        font.setPixelSize(Typography.SIZE_LG)
        font.setWeight(QFont.Weight(Typography.WEIGHT_BOLD))
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        text_x = cx + r + 8
        painter.drawText(text_x, 0, self.width() - text_x, self.height(), 0, "PHOTON")

        painter.end()


# ── Settings gear button ─────────────────────────────────────────────────────────────


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


# ── MainWindow ────────────────────────────────────────────────────────────────────────────


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

        self._diag_dialog = _DiagnosticsDialog(self)
        self.log_widget = self._diag_dialog.text_widget

        # Defer solver-installation check until after the window is shown
        QTimer.singleShot(500, self._check_solver_installation)

        logger.info("MainWindow initialised.")

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_components(self) -> None:
        self._stepper        = PipelineStepperWidget()
        self._sidebar        = SessionSidebar()
        self._canvas         = FitsCanvas()
        self._inspector      = InspectorPanel()
        self._bottom         = BottomBarWidget()
        self._phot_panel     = PhotometryPanel()
        self._lc_panel       = LightCurvePanel()

        # Lazy-import settings window to avoid Qt startup cost
        self._settings_window: object | None = None

    def _build_layout(self) -> None:
        """Assemble the full window layout with BackgroundWidget as root."""
        bg = BackgroundWidget()
        root_layout = QVBoxLayout(bg)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ─────────────────────────────────────────────────────────────
        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        # ── Main splitter (8px margins so gradient shows around panels) ───
        splitter_wrapper = QWidget()
        splitter_wrapper.setStyleSheet("background-color: transparent;")
        sw_layout = QVBoxLayout(splitter_wrapper)
        sw_layout.setContentsMargins(8, 8, 8, 8)
        sw_layout.setSpacing(0)

        # Outer horizontal splitter: sidebar | center | right-panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setStyleSheet("QSplitter { background-color: transparent; }")

        # Center: vertical splitter (canvas / light curve), ratio 60/40
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setChildrenCollapsible(False)
        self._v_splitter.setStyleSheet("QSplitter { background-color: transparent; }")
        self._v_splitter.addWidget(self._canvas)
        self._v_splitter.addWidget(self._lc_panel)
        self._v_splitter.setStretchFactor(0, 3)
        self._v_splitter.setStretchFactor(1, 2)
        self._lc_panel.setVisible(False)

        # Right panel: InspectorPanel (steps 0-2) / PhotometryPanel (step 3)
        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(self._inspector)   # page 0
        self._right_stack.addWidget(self._phot_panel)  # page 1

        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._v_splitter)
        self._splitter.addWidget(self._right_stack)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(2, False)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        sw_layout.addWidget(self._splitter)

        root_layout.addWidget(splitter_wrapper, 1)

        # ── Bottom bar ────────────────────────────────────────────────
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

        layout.addSpacing(12)

        # Catalog overlay toggle button (flat, checkable)
        from PySide6.QtWidgets import QPushButton
        self._catalog_toggle_btn = QPushButton("Catalog")
        self._catalog_toggle_btn.setCheckable(True)
        self._catalog_toggle_btn.setChecked(True)
        self._catalog_toggle_btn.setFixedHeight(28)
        self._catalog_toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: transparent;"
            f"  color: {Colors.TEXT_SECONDARY};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: 6px;"
            f"  padding: 0 10px;"
            f"  font-size: {Typography.SIZE_XS}px;"
            f"}}"
            f"QPushButton:checked {{"
            f"  background-color: rgba(124,58,237,40);"  # Colors.VIOLET_GLOW
            f"  color: {Colors.VIOLET_BRIGHT};"
            f"  border-color: {Colors.VIOLET};"
            f"}}"
            f"QPushButton:hover:!checked {{"
            f"  background-color: {Colors.SURFACE_ALT};"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"}}"
        )
        self._catalog_toggle_btn.toggled.connect(self._canvas.toggle_catalog_overlay)
        layout.addWidget(self._catalog_toggle_btn, 0, Qt.AlignmentFlag.AlignVCenter)

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
        gear_menu.addAction("Settings…",      self._open_settings,  "Ctrl+,")
        gear_menu.addAction("View Diagnostics…", self._open_diagnostics)
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

        # Wire the inspector solve button to this MainWindow (which has .session)
        self._inspector.wire_solve_button(self)
        self._inspector.solve_complete.connect(self._on_solve_complete)

        # Photometry panel signals
        self._phot_panel.select_target_requested.connect(
            lambda: self._canvas.set_interaction_mode("select_target")
        )
        self._phot_panel.select_comparison_requested.connect(
            lambda: self._canvas.set_interaction_mode("select_comparison")
        )
        self._phot_panel.auto_select_requested.connect(self._auto_select_comparisons)
        self._phot_panel.run_photometry_requested.connect(self._run_photometry)
        self._phot_panel.aperture_changed.connect(self._on_aperture_changed)
        self._phot_panel.photometry_complete.connect(self._on_photometry_complete)

        self._canvas.star_clicked.connect(self._on_star_clicked)
        self._lc_panel.frame_flagged.connect(self._on_frame_flagged)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._open_sequence)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._open_settings)
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
        panels = [self._sidebar, self._v_splitter, self._right_stack]
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
        for anim, delay in zip(anims, offsets_ms):
            QTimer.singleShot(delay, anim.start)

        # Remove effects after all animations complete to avoid paint artifacts
        def _cleanup() -> None:
            for panel in panels:
                panel.setGraphicsEffect(None)

        QTimer.singleShot(offsets_ms[-1] + 350, _cleanup)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _check_solver_installation(self) -> None:
        """Warn once per session if no plate solver is available or configured."""
        sm = get_settings_manager()
        backend = sm.get("platesolve/backend")

        show_warning = False

        if backend == "astap":
            binary = sm.get("platesolve/astap_binary_path")
            if not binary:
                # No path configured — check PATH/common locations
                from photon.core.plate_solver import ASTAPSolver
                found, _ = ASTAPSolver.detect_installation()
                show_warning = not found
            else:
                from photon.core.plate_solver import ASTAPSolver
                found, _ = ASTAPSolver.detect_installation(binary)
                show_warning = not found

        elif backend == "local":
            if sm.get("platesolve/local_binary_path"):
                return  # path explicitly set — trust the user
            from photon.core.plate_solver import LocalAstrometrySolver
            show_warning = LocalAstrometrySolver.detect_installation() is None

        # Cloud backend never needs a local binary
        if not show_warning:
            return

        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Plate Solving")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            "Local plate solving requires the astrometry.net solver to be installed.\n\n"
            "You can configure this in Settings → Plate Solving, "
            "or use the Astrometry.net cloud API instead."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowModality(Qt.WindowModality.NonModal)
        msg.show()

    def _open_settings(self) -> None:
        if self._settings_window is None:
            from photon.ui.settings_window import SettingsWindow
            self._settings_window = SettingsWindow(self)
        self._settings_window.exec()  # type: ignore[union-attr]

    def _open_diagnostics(self) -> None:
        self._diag_dialog.show()
        self._diag_dialog.raise_()

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

        # Auto-dispatch star detection on the first frame
        self._dispatch_star_detection(stack[0])

    def _dispatch_star_detection(self, frame: object) -> None:
        sm = get_settings_manager()
        worker = StarDetectionWorker(
            frame,  # type: ignore[arg-type]
            fwhm=sm.get("photometry/detection_fwhm"),
            threshold_sigma=sm.get("photometry/detection_threshold_sigma"),
        )
        worker.signals.result.connect(self._on_stars_detected)
        worker.signals.error.connect(self._on_star_detection_error)
        QThreadPool.globalInstance().start(worker)

    def _on_stars_detected(self, stars: object) -> None:
        self.session.detected_stars = stars
        self._canvas.display_stars(stars)
        n_stars = len(stars) if stars is not None else 0
        self._bottom.set_status(f"Detected {n_stars} stars")
        logger.info("Star detection complete: %d sources", n_stars)

    def _on_star_detection_error(self, tb: str) -> None:
        logger.warning("Star detection failed:\n%s", tb)
        self._bottom.set_status("Star detection failed — check diagnostics")
        self._bottom.set_dot_warning(True)

    def _on_error(self, traceback_str: str) -> None:
        last_line = traceback_str.strip().splitlines()[-1]
        self._bottom.set_status(f"Error: {last_line}")
        logger.error("Worker error:\n%s", traceback_str)
        QMessageBox.critical(self, "Error", last_line)

    # ------------------------------------------------------------------
    # Frame navigation
    # ------------------------------------------------------------------

    def _show_frame(self, index: int) -> None:
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
        index = max(0, min(index, 3))
        self._current_step = index
        self._stepper.set_active_step(index)
        self._inspector.set_step(index)

        if index == 2:
            # Photometry step: show PhotometryPanel + LightCurvePanel
            self._right_stack.setCurrentIndex(1)
            self._lc_panel.setVisible(True)
        else:
            self._right_stack.setCurrentIndex(0)
            self._lc_panel.setVisible(False)

    # ------------------------------------------------------------------
    # Star interaction
    # ------------------------------------------------------------------

    def _on_star_clicked(self, x: float, y: float) -> None:
        """Handle a canvas click in select_target or select_comparison mode."""
        mode  = self._canvas._interaction_mode
        stars = self.session.detected_stars

        if mode == "select_target":
            row = snap_to_nearest_star(x, y, stars) if stars is not None else None
            if row is not None and stars is not None:
                snap_x = float(stars["x_centroid"][row])
                snap_y = float(stars["y_centroid"][row])
                self.session.target_xy = (snap_x, snap_y)
                self.session.target_star_row = row
            else:
                self.session.target_xy = (x, y)
                self.session.target_star_row = None
            self._phot_panel.set_target(self.session.target_xy)
            self._canvas.set_target(
                self.session.target_xy,
                self.session.comparison_xys,
            )
            self._canvas.set_interaction_mode("none")

        elif mode == "select_comparison":
            row = snap_to_nearest_star(x, y, stars) if stars is not None else None
            if row is not None and stars is not None:
                snap_x = float(stars["x_centroid"][row])
                snap_y = float(stars["y_centroid"][row])
                pos = (snap_x, snap_y)
            else:
                pos = (x, y)

            if row not in self.session.comparison_star_rows:
                self.session.comparison_xys.append(pos)
                if row is not None:
                    self.session.comparison_star_rows.append(row)
            self._phot_panel.set_comparisons(self.session.comparison_xys)
            self._canvas.set_target(
                self.session.target_xy,
                self.session.comparison_xys,
            )
            self._canvas.set_interaction_mode("none")

    # ------------------------------------------------------------------
    # Plate solve → catalog pipeline
    # ------------------------------------------------------------------

    def _on_solve_complete(self, wcs: object) -> None:
        """Handle a successful plate solve: advance stepper, query catalogs."""
        self._stepper.set_step_complete(1)
        self._stepper.set_active_step(1)
        self._bottom.set_status("Plate solved — querying catalogs…")
        logger.info("Plate solve complete; dispatching catalog queries.")
        self._dispatch_catalog_query(wcs)

    def _dispatch_catalog_query(self, wcs: object) -> None:
        """Dispatch off-thread catalog queries for the solved field."""
        from photon.core.settings_manager import get_settings_manager as _gsm
        from photon.workers.catalog_worker import CatalogWorker

        sm = _gsm()
        radius = float(sm.get("catalog/search_radius_arcmin"))

        worker = CatalogWorker(wcs=wcs, radius_arcmin=radius)
        worker.signals.result.connect(self._on_catalog_results)
        worker.signals.error.connect(
            lambda tb: self._bottom.set_status("Catalog query failed.")
        )
        QThreadPool.globalInstance().start(worker)

    def _on_catalog_results(self, results: dict) -> None:
        """Store catalog results, update overlay, and annotate comparisons."""
        import math

        self.session.catalog_matches = results

        n_simbad = len(results.get("simbad") or [])
        n_gaia   = len(results.get("gaia")   or [])
        n_vsx    = len(results.get("vsx")    or [])
        self._bottom.set_status(
            f"Catalogs loaded — SIMBAD {n_simbad}, Gaia {n_gaia}, VSX {n_vsx}"
        )
        logger.info("Catalog results: SIMBAD=%d, Gaia=%d, VSX=%d", n_simbad, n_gaia, n_vsx)

        if self.session.wcs is not None:
            self._canvas.display_catalog_overlay(self.session.wcs, results)
            self._canvas.toggle_catalog_overlay(self._catalog_toggle_btn.isChecked())

        # Annotate comparison stars with catalog names where match < 5px
        self._update_comparison_catalog_names(results)

    def _update_comparison_catalog_names(self, results: dict) -> None:
        """Find catalog names within 5px of each comparison star and update panel."""
        import numpy as np
        from astropy.coordinates import SkyCoord
        import astropy.units as u

        wcs = self.session.wcs
        comp_xys = self.session.comparison_xys
        if wcs is None or not comp_xys:
            return

        name_map: dict[int, str] = {}

        # Build combined SIMBAD + VSX name lookup (RA/Dec in degrees + name)
        cat_ra:   list[float] = []
        cat_dec:  list[float] = []
        cat_name: list[str]   = []

        for cat_key in ("simbad", "vsx"):
            tbl = results.get(cat_key)
            if tbl is None or len(tbl) == 0 or "name" not in tbl.colnames:
                continue
            ra_col  = tbl["ra"]
            dec_col = tbl["dec"]
            names   = tbl["name"]

            for i in range(len(tbl)):
                try:
                    ra_v  = ra_col[i]
                    dec_v = dec_col[i]
                    # SIMBAD stores sexagesimal strings
                    if isinstance(ra_v, (bytes, str)):
                        sc = SkyCoord(str(ra_v), str(dec_v), unit=(u.hourangle, u.deg))
                        cat_ra.append(float(sc.ra.deg))
                        cat_dec.append(float(sc.dec.deg))
                    else:
                        cat_ra.append(float(ra_v))
                        cat_dec.append(float(dec_v))
                    cat_name.append(str(names[i]).strip())
                except Exception:
                    pass

        if not cat_ra:
            return

        cat_ra_arr  = np.array(cat_ra,  dtype=float)
        cat_dec_arr = np.array(cat_dec, dtype=float)

        try:
            cat_coords = SkyCoord(cat_ra_arr, cat_dec_arr, unit=u.deg)
            # Convert catalog positions to pixels
            cat_xs, cat_ys = wcs.world_to_pixel(cat_coords)
            cat_xs = np.asarray(cat_xs, dtype=float)
            cat_ys = np.asarray(cat_ys, dtype=float)
        except Exception:
            return

        MATCH_RADIUS_PX = 5.0

        for c_idx, (cx, cy) in enumerate(comp_xys):
            dx = cat_xs - cx
            dy = cat_ys - cy
            dist = np.sqrt(dx * dx + dy * dy)
            best = int(np.argmin(dist))
            if dist[best] < MATCH_RADIUS_PX:
                name_map[c_idx] = cat_name[best]

        if name_map:
            self._phot_panel.update_comparison_catalog_names(name_map)

    def _auto_select_comparisons(self) -> None:
        """Auto-select comparison stars using star detection results."""
        stars = self.session.detected_stars
        txy   = self.session.target_xy
        if stars is None or txy is None:
            self._bottom.set_status("Detect stars and select a target first.")
            return

        sm = get_settings_manager()
        comps = select_comparison_stars(
            stars,
            txy[0], txy[1],
            min_snr=sm.get("photometry/min_comparison_snr"),
            max_stars=sm.get("photometry/max_comparison_stars"),
        )
        xys = [
            (float(comps["x_centroid"][i]), float(comps["y_centroid"][i]))
            for i in range(len(comps))
        ]
        self.session.comparison_xys = xys
        self._phot_panel.set_comparisons(xys)
        self._canvas.set_target(self.session.target_xy, xys)
        self._bottom.set_status(f"Auto-selected {len(xys)} comparison stars.")

    def _on_aperture_changed(
        self, radius: float, inner: float, outer: float
    ) -> None:
        self._canvas.set_aperture_params(radius, inner, outer)

    # ------------------------------------------------------------------
    # Photometry
    # ------------------------------------------------------------------

    def _run_photometry(self) -> None:
        if (
            self.session.image_stack is None
            or self.session.target_xy is None
            or not self.session.comparison_xys
        ):
            return

        self._phot_panel.set_running(True)
        self._bottom.set_status("Running photometry…")

        ap_r, ann_in, ann_out = self._phot_panel.get_aperture_params()

        obs_times = None
        try:
            from photon.core.fits_loader import get_observation_times
            obs_times = get_observation_times(self.session.headers)
        except Exception:
            pass

        worker = PhotometryWorker(
            self.session.image_stack,
            self.session.target_xy,
            self.session.comparison_xys,
            aperture_radius=ap_r,
            annulus_inner=ann_in,
            annulus_outer=ann_out,
            observation_times=obs_times,
            frame_flags=self.session.frame_flags,
        )
        worker.signals.result.connect(self._on_phot_worker_done)
        worker.signals.error.connect(self._on_phot_error)
        QThreadPool.globalInstance().start(worker)

    def _on_phot_worker_done(self, payload: object) -> None:
        self._phot_panel.on_photometry_done(payload)  # type: ignore[arg-type]

    def _on_phot_error(self, traceback_str: str) -> None:
        self._phot_panel.set_running(False)
        last_line = traceback_str.strip().splitlines()[-1]
        self._bottom.set_status(f"Photometry error: {last_line}")
        logger.error("PhotometryWorker error:\n%s", traceback_str)
        QMessageBox.critical(self, "Photometry Error", last_line)

    def _on_photometry_complete(self, result: dict) -> None:
        """Store results and update light curve panel."""
        self.session.photometry_result = result.get("photometry")
        lc = result.get("light_curve")
        self.session.light_curve = lc

        if lc is not None:
            self._lc_panel.update_light_curve(lc)
            self._lc_panel.setVisible(True)

        scatter = (result.get("photometry") or {}).get("scatter", 0.0)
        self._bottom.set_status(f"Photometry complete — scatter {scatter:.4f} mag")
        self._stepper.set_step_complete(2)
        self._stepper.set_active_step(3)
        self._set_pipeline_step(3)

    def _on_frame_flagged(self, frame_index: int, flagged: bool) -> None:
        """Update session frame flags when the user flags/unflags a frame."""
        import numpy as np
        if self.session.image_stack is None:
            return
        n = self.session.image_stack.shape[0]
        if self.session.frame_flags is None:
            self.session.frame_flags = np.zeros(n, dtype=bool)
        if 0 <= frame_index < n:
            self.session.frame_flags[frame_index] = flagged
