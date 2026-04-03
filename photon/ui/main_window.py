"""Main application window — Observatory Glass layout."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, QThreadPool, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPen, QPolygon
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QShortcut,
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


# ── Logo widget ─────────────────────────────────────────────────────────────────


class _LogoWidget(QWidget):
    """Paints a violet hexagon followed by the "PHOTON" wordmark."""

    _SIZE = 14

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._SIZE * 2 + 8 + 80, 40)
        self.setStyleSheet("background-color: transparent;")

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self._SIZE + 2, self.height() // 2
        r = self._SIZE
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
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)
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
        bg = BackgroundWidget()
        root_layout = QVBoxLayout(bg)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        # ── Content area with 8px margins ─────────────────────────────────
        splitter_wrapper = QWidget()
        splitter_wrapper.setStyleSheet("background-color: transparent;")
        sw_layout = QVBoxLayout(splitter_wrapper)
        sw_layout.setContentsMargins(8, 8, 8, 8)
        sw_layout.setSpacing(0)

        # Outer horizontal splitter: sidebar | center | right-panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setStyleSheet("QSplitter { background-color: transparent; }")

        # Center: vertical splitter (canvas / light curve)
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setChildrenCollapsible(False)
        self._v_splitter.setStyleSheet("QSplitter { background-color: transparent; }")
        self._v_splitter.addWidget(self._canvas)
        self._v_splitter.addWidget(self._lc_panel)
        self._v_splitter.setStretchFactor(0, 3)
        self._v_splitter.setStretchFactor(1, 2)
        self._lc_panel.setVisible(False)

        # Right panel: stack — InspectorPanel (steps 0-2) / PhotometryPanel (step 3)
        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(self._inspector)    # page 0
        self._right_stack.addWidget(self._phot_panel)   # page 1

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
        root_layout.addWidget(self._bottom)

        self.setCentralWidget(bg)

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            f"background-color: {Colors.SURFACE};"
            f"border-bottom: 1px solid {Colors.BORDER};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        logo = _LogoWidget()
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch(1)
        layout.addWidget(self._stepper, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

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
        gear_menu.addSeparator()
        gear_menu.addAction("Quit", self.close, "Ctrl+Q")
        self._gear_btn.setMenu(gear_menu)

        layout.addWidget(self._gear_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        return bar

    def _connect_signals(self) -> None:
        """Wire all inter-widget signals."""
        self._sidebar.open_requested.connect(self._open_sequence)
        self._canvas.files_dropped.connect(self._load_paths)
        self._sidebar.frame_selected.connect(self._show_frame)
        self._bottom.frame_scrubbed.connect(self._show_frame)
        self._stepper.step_clicked.connect(self._set_pipeline_step)

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
        """Register global keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._open_sequence)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._open_settings)
        QShortcut(QKeySequence("Left"),   self).activated.connect(self._prev_frame)
        QShortcut(QKeySequence("Right"),  self).activated.connect(self._next_frame)
        QShortcut(QKeySequence("Space"),  self).activated.connect(self._toggle_play)
        QShortcut(QKeySequence("1"), self).activated.connect(lambda: self._set_pipeline_step(0))
        QShortcut(QKeySequence("2"), self).activated.connect(lambda: self._set_pipeline_step(1))
        QShortcut(QKeySequence("3"), self).activated.connect(lambda: self._set_pipeline_step(2))
        QShortcut(QKeySequence("4"), self).activated.connect(lambda: self._set_pipeline_step(3))
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    # ------------------------------------------------------------------
    # Launch animation
    # ------------------------------------------------------------------

    def showEvent(self, event: object) -> None:  # type: ignore[override]
        super().showEvent(event)  # type: ignore[arg-type]
        self._run_launch_animations()

    def _run_launch_animations(self) -> None:
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

        def _cleanup() -> None:
            for panel in panels:
                panel.setGraphicsEffect(None)

        QTimer.singleShot(offsets_ms[-1] + 350, _cleanup)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        if self._settings_window is None:
            from photon.ui.settings_window import SettingsWindow
            self._settings_window = SettingsWindow(self)
        self._settings_window.exec()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Loading flow
    # ------------------------------------------------------------------

    def _open_sequence(self) -> None:
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
        self._bottom.set_progress(0, 0)  # indeterminate

        worker = FitsLoaderWorker(paths)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._bottom.show_progress(False))
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Load slot
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
        worker.signals.error.connect(lambda tb: logger.warning("Star detection failed:\n%s", tb))
        QThreadPool.globalInstance().start(worker)

    def _on_stars_detected(self, stars: object) -> None:
        self.session.detected_stars = stars
        self._canvas.display_stars(stars)
        n_stars = len(stars) if stars is not None else 0
        self._bottom.set_status(f"Detected {n_stars} stars")
        logger.info("Star detection complete: %d sources", n_stars)

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
        mode = self._canvas._interaction_mode
        stars = self.session.detected_stars

        if mode == "select_target":
            row = snap_to_nearest_star(x, y, stars) if stars is not None else None
            if row is not None and stars is not None:
                snap_x = float(stars["xcentroid"][row])
                snap_y = float(stars["ycentroid"][row])
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
                snap_x = float(stars["xcentroid"][row])
                snap_y = float(stars["ycentroid"][row])
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
            (float(comps["xcentroid"][i]), float(comps["ycentroid"][i]))
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

        # Gather observation times if available
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
