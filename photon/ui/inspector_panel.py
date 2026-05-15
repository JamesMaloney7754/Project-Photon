"""Inspector panel — context-sensitive right panel with animated data rows."""

from __future__ import annotations

import logging
import math
from typing import Any

from PySide6.QtCore import (
    Property,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import Signal as _Signal
from photon.ui.glass_panel import GlassPanel
from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)


# ── DataRow ────────────────────────────────────────────────────────────────────


class DataRow(QWidget):
    """A single key-value row with a flash animation on value change.

    Parameters
    ----------
    key : str
        Label text shown on the left.
    placeholder : str
        Initial value text (default ``"—"``).
    parent : QWidget | None
        Optional parent widget.
    """

    # Animated flash property (0.0 = TEXT_GOLD, 1.0 = white)
    def _get_flash(self) -> float:
        return self._flash

    def _set_flash(self, value: float) -> None:
        self._flash = value
        self.update()

    flash = Property(float, _get_flash, _set_flash)

    def __init__(
        self,
        key: str,
        placeholder: str = "—",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(32)
        self._key = key
        self._value = placeholder
        self._flash: float = 0.0

        self._flash_anim = QPropertyAnimation(self, b"flash", self)
        self._flash_anim.setDuration(300)

    def set_value(self, text: str) -> None:
        """Update the displayed value with a brief flash effect.

        Parameters
        ----------
        text : str
            New value to display.
        """
        self._value = text
        self._flash_anim.stop()
        self._flash_anim.setStartValue(1.0)
        self._flash_anim.setEndValue(0.0)
        self._flash_anim.start()
        self.update()

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # ── Key label ─────────────────────────────────────────────────────
        key_font = QFont("Inter")
        key_font.setPixelSize(Typography.SIZE_SM)
        key_font.setWeight(QFont.Weight(Typography.WEIGHT_REGULAR))
        painter.setFont(key_font)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        painter.drawText(0, 0, w // 2 - 4, h - 1, Qt.AlignmentFlag.AlignVCenter, self._key)

        # ── Value label (gold → white flash) ──────────────────────────────
        # TEXT_GOLD = #fbbf24 = (251, 191, 36); white = (255, 255, 255)
        f = self._flash
        vr = int(251 + (255 - 251) * f)
        vg = int(191 + (255 - 191) * f)
        vb = int(36  + (255 - 36)  * f)
        val_font = QFont("Inter")
        val_font.setPixelSize(Typography.SIZE_SM)
        val_font.setWeight(QFont.Weight(Typography.WEIGHT_SEMIBOLD))
        val_font.setFamily(Typography.FONT_MONO)
        painter.setFont(val_font)
        painter.setPen(QColor(vr, vg, vb))
        painter.drawText(
            w // 2 + 4, 0, w // 2 - 4, h - 1,
            Qt.AlignmentFlag.AlignVCenter,
            self._value,
        )

        # ── Bottom separator ──────────────────────────────────────────────
        painter.setPen(QColor(Colors.BORDER_SUBTLE))
        painter.drawLine(0, h - 1, w, h - 1)

        painter.end()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _section_header(text: str) -> QWidget:
    """Return a styled section-header label widget."""
    from PySide6.QtWidgets import QLabel
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECONDARY};"
        f"font-size: {Typography.SIZE_XS}px;"
        f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
        f"letter-spacing: 1px;"
        f"padding-bottom: 6px;"
        f"background-color: transparent;"
    )
    return lbl


def _page_wrapper(inner: QWidget) -> QScrollArea:
    """Wrap *inner* in a scrollable area with consistent padding."""
    scroll = QScrollArea()
    scroll.setWidget(inner)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(
        "QScrollArea { background-color: transparent; border: none; }"
        "QScrollArea > QWidget { background-color: transparent; }"
    )
    return scroll


# ── _RadarWidget ───────────────────────────────────────────────────────────────


class _RadarWidget(QWidget):
    """Animated radar-ping widget shown while plate solving.

    Draws a rotating sweep arc over concentric rings using the violet accent
    colour.  Drive with :meth:`start` / :meth:`stop`.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self._angle: float = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(30)  # ~33 fps
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        """Start the radar animation."""
        self._angle = 0.0
        self._timer.start()

    def stop(self) -> None:
        """Stop the radar animation."""
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360  # 6° per frame ≈ 1 revolution/s
        self.update()

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 2

        # Background
        painter.fillRect(self.rect(), QColor(Colors.CANVAS_BG))

        violet = QColor(Colors.VIOLET)

        # ── Concentric rings ──────────────────────────────────────────────
        for frac in (0.33, 0.67, 1.0):
            ring_r = int(r * frac)
            pen = QPen(QColor(124, 58, 237, 50), 1)  # Colors.VIOLET dim
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        # ── Sweep arc (90° wide, rotating) ────────────────────────────────
        from PySide6.QtGui import QConicalGradient
        grad = QConicalGradient(cx, cy, self._angle)
        grad.setColorAt(0.0,  QColor(124, 58, 237, 0))    # transparent tail
        grad.setColorAt(0.25, QColor(124, 58, 237, 180))  # Colors.VIOLET bright
        grad.setColorAt(1.0,  QColor(124, 58, 237, 0))

        from PySide6.QtGui import QBrush
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Crosshairs ────────────────────────────────────────────────────
        pen_cross = QPen(QColor(124, 58, 237, 80), 1)  # Colors.VIOLET
        painter.setPen(pen_cross)
        painter.drawLine(cx - r, cy, cx + r, cy)
        painter.drawLine(cx, cy - r, cx, cy + r)

        # ── Sweep tip dot ─────────────────────────────────────────────────
        angle_rad = math.radians(self._angle)
        tip_x = cx + int(r * math.cos(angle_rad))
        tip_y = cy - int(r * math.sin(angle_rad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(violet)
        painter.drawEllipse(tip_x - 3, tip_y - 3, 6, 6)

        painter.end()


# ── InspectorPanel ─────────────────────────────────────────────────────────────


class InspectorPanel(GlassPanel):
    """Context-sensitive inspector panel with one page per pipeline step.

    Use :meth:`set_step` to switch pages.  Each ``update_*`` method populates
    the corresponding page with live data using :class:`DataRow` widgets that
    flash on change.

    Signals
    -------
    solve_complete : Signal(object)
        Emitted with the ``astropy.wcs.WCS`` after a successful plate solve.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    solve_complete: _Signal = _Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._session_provider: object = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # ── Header: title that fades on step change ───────────────────────
        from PySide6.QtWidgets import QLabel
        self._title_lbl = QLabel("File Info")
        self._title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"letter-spacing: 1px;"
            f"background-color: transparent;"
        )
        self._title_effect = QGraphicsOpacityEffect(self._title_lbl)
        self._title_lbl.setGraphicsEffect(self._title_effect)
        self._title_fade_out = QPropertyAnimation(self._title_effect, b"opacity", self)
        self._title_fade_out.setDuration(150)
        self._title_fade_in = QPropertyAnimation(self._title_effect, b"opacity", self)
        self._title_fade_in.setDuration(150)
        root.addWidget(self._title_lbl)
        root.addSpacing(8)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background-color: transparent;")
        root.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_page0())
        self._stack.addWidget(self._build_page1())
        self._stack.addWidget(self._build_page2())
        self._stack.addWidget(self._build_page3())

        self._stack.setCurrentIndex(0)

        self._step_titles = ["File Info", "Plate Solution", "Photometry", "Transit Fit"]

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------

    def _build_page0(self) -> QScrollArea:
        """File info page."""
        w = QWidget()
        w.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._p0_filename  = DataRow("File")
        self._p0_filesize  = DataRow("Size")
        self._p0_telescop  = DataRow("Telescope")
        self._p0_instrume  = DataRow("Instrument")
        self._p0_exptime   = DataRow("Exposure")
        self._p0_gain      = DataRow("Gain")
        self._p0_object    = DataRow("Object")

        for row in (
            self._p0_filename, self._p0_filesize, self._p0_telescop,
            self._p0_instrume, self._p0_exptime, self._p0_gain, self._p0_object,
        ):
            layout.addWidget(row)
        layout.addStretch()
        return _page_wrapper(w)

    def _build_page1(self) -> QScrollArea:
        """Plate solution page."""
        w = QWidget()
        w.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._p1_ra       = DataRow("RA center")
        self._p1_dec      = DataRow("Dec center")
        self._p1_scale    = DataRow("Pixel scale")
        self._p1_rotation = DataRow("Rotation")
        self._p1_matches  = DataRow("Cat. matches")

        for row in (
            self._p1_ra, self._p1_dec, self._p1_scale,
            self._p1_rotation, self._p1_matches,
        ):
            layout.addWidget(row)

        layout.addSpacing(12)

        # ── Radar animation widget ────────────────────────────────────────
        self._radar = _RadarWidget()
        self._radar.setVisible(False)
        layout.addWidget(self._radar, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── Solving status label ──────────────────────────────────────────
        self._solve_status_lbl = QLabel("")
        self._solve_status_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-style: italic;"
            f"background-color: transparent;"
        )
        self._solve_status_lbl.setVisible(False)
        layout.addWidget(self._solve_status_lbl)

        # ── Progress log ──────────────────────────────────────────────────
        self._solve_log = QPlainTextEdit()
        self._solve_log.setReadOnly(True)
        self._solve_log.setFixedHeight(80)
        self._solve_log.setStyleSheet(
            f"background-color: {Colors.SURFACE};"
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"border: none;"
            f"padding: 4px;"
        )
        self._solve_log.setVisible(False)
        layout.addWidget(self._solve_log)

        # ── Error label ───────────────────────────────────────────────────
        self._solve_error_lbl = QLabel("")
        self._solve_error_lbl.setStyleSheet(
            f"color: {Colors.DANGER};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"background-color: transparent;"
        )
        self._solve_error_lbl.setWordWrap(True)
        self._solve_error_lbl.setVisible(False)
        layout.addWidget(self._solve_error_lbl)

        layout.addSpacing(8)

        # ── Buttons ───────────────────────────────────────────────────────
        self._solve_btn = QPushButton("Solve Field")
        self._solve_btn.setObjectName("solve_btn")
        self._solve_btn.clicked.connect(self._on_solve_clicked)
        layout.addWidget(self._solve_btn)

        self._solve_retry_btn = QPushButton("Retry")
        self._solve_retry_btn.setVisible(False)
        self._solve_retry_btn.clicked.connect(self._on_solve_clicked)
        layout.addWidget(self._solve_retry_btn)

        layout.addStretch()
        return _page_wrapper(w)

    # ------------------------------------------------------------------
    # Solve wiring (called by MainWindow after construction)
    # ------------------------------------------------------------------

    def wire_solve_button(self, session_provider: object) -> None:
        """Store a reference to the session provider.

        Parameters
        ----------
        session_provider : object
            Object with a ``session`` attribute exposing the current
            :class:`~photon.core.session.PhotonSession`.
        """
        self._session_provider = session_provider

    # ------------------------------------------------------------------
    # Solve button handler
    # ------------------------------------------------------------------

    def _on_solve_clicked(self) -> None:
        """Start a plate-solve worker for the current session frame."""
        import numpy as np
        from PySide6.QtCore import QThreadPool

        from photon.workers.plate_solve_worker import PlateSolveWorker

        session_provider = getattr(self, "_session_provider", None)
        if session_provider is None:
            self._show_solve_error("No session provider set.")
            return

        session = getattr(session_provider, "session", None)
        if session is None or session.image_stack is None:
            self._show_solve_error("No frame loaded.")
            return

        idx = getattr(session_provider, "_current_frame", 0) or 0
        stack = session.image_stack
        if idx >= stack.shape[0]:
            idx = 0

        image = np.asarray(stack[idx], dtype=np.float64)

        headers = getattr(session, "headers", [])
        header = headers[idx] if idx < len(headers) else None

        self._set_solving(True)

        worker = PlateSolveWorker(image=image, header=header)
        worker.signals.progress.connect(self._on_solve_progress)
        worker.signals.result.connect(self._on_solve_result)
        worker.signals.error.connect(self._on_solve_error_msg)
        worker.signals.finished.connect(lambda: self._set_solving(False))
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Solve state helpers
    # ------------------------------------------------------------------

    def _set_solving(self, active: bool) -> None:
        """Toggle the solving UI state."""
        self._solve_btn.setEnabled(not active)
        self._solve_btn.setText("Solving…" if active else "Solve Field")
        self._solve_retry_btn.setVisible(False)
        self._solve_error_lbl.setVisible(False)

        self._radar.setVisible(active)
        if active:
            self._radar.start()
            self._solve_log.clear()
            self._solve_log.setVisible(True)
            self._solve_status_lbl.setText("Solving…")
            self._solve_status_lbl.setVisible(True)
        else:
            self._radar.stop()

    def _on_solve_progress(self, msg: str) -> None:
        """Append a progress line to the log."""
        self._solve_log.appendPlainText(msg)
        # Auto-scroll to bottom
        sb = self._solve_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_solve_result(self, wcs: object) -> None:
        """Handle a successful plate solve."""
        self._solve_status_lbl.setText("Solved!")
        self._solve_status_lbl.setStyleSheet(
            f"color: {Colors.SUCCESS};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"background-color: transparent;"
        )
        self.update_wcs_info(wcs)

        # Store WCS back to session
        session_provider = getattr(self, "_session_provider", None)
        if session_provider is not None:
            session = getattr(session_provider, "session", None)
            if session is not None:
                session.wcs = wcs

        self.solve_complete.emit(wcs)

    def _on_solve_error_msg(self, tb: str) -> None:
        """Handle a solve failure."""
        self._show_solve_error(tb)

    def _show_solve_error(self, msg: str) -> None:
        """Display an error message with a retry button."""
        # Truncate for display — keep first 3 lines
        lines = msg.strip().splitlines()
        display = "\n".join(lines[:3])
        if len(lines) > 3:
            display += " …"
        self._solve_error_lbl.setText(display)
        self._solve_error_lbl.setVisible(True)
        self._solve_retry_btn.setVisible(True)
        self._solve_status_lbl.setText("Failed")
        self._solve_status_lbl.setStyleSheet(
            f"color: {Colors.DANGER};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"background-color: transparent;"
        )
        self._solve_status_lbl.setVisible(True)

    def _build_page2(self) -> QScrollArea:
        """Photometry page."""
        w = QWidget()
        w.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._p2_target    = DataRow("Target")
        self._p2_comp_n    = DataRow("Comp. stars")
        self._p2_aperture  = DataRow("Aperture")
        self._p2_ann_inner = DataRow("Ann. inner")
        self._p2_ann_outer = DataRow("Ann. outer")

        for row in (
            self._p2_target, self._p2_comp_n, self._p2_aperture,
            self._p2_ann_inner, self._p2_ann_outer,
        ):
            layout.addWidget(row)

        layout.addSpacing(12)
        run_btn = QPushButton("Run Photometry")
        layout.addWidget(run_btn)
        layout.addStretch()
        return _page_wrapper(w)

    def _build_page3(self) -> QScrollArea:
        """Transit parameters page."""
        w = QWidget()
        w.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._p3_t0       = DataRow("Mid-transit (BJD)")
        self._p3_duration = DataRow("Duration")
        self._p3_depth    = DataRow("Depth")
        self._p3_rprs     = DataRow("Rp/Rs")

        for row in (self._p3_t0, self._p3_duration, self._p3_depth, self._p3_rprs):
            layout.addWidget(row)
        layout.addStretch()
        return _page_wrapper(w)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_step(self, index: int) -> None:
        """Switch to the page corresponding to pipeline *index*.

        The title label fades out then fades back in with the new name.

        Parameters
        ----------
        index : int
            Step index ``[0, 3]``.
        """
        index = max(0, min(index, 3))
        self._stack.setCurrentIndex(index)

        new_title = self._step_titles[index]
        self._title_fade_out.stop()
        self._title_fade_in.stop()
        self._title_fade_out.setStartValue(1.0)
        self._title_fade_out.setEndValue(0.0)

        def _swap() -> None:
            self._title_lbl.setText(new_title)
            self._title_fade_in.setStartValue(0.0)
            self._title_fade_in.setEndValue(1.0)
            self._title_fade_in.start()

        self._title_fade_out.finished.connect(_swap)
        self._title_fade_out.start()

    def set_current_frame_path(self, path: object) -> None:
        """Populate the filename and file-size fields on page 0.

        Parameters
        ----------
        path : pathlib.Path
            Path to the FITS file for the currently selected frame.
        """
        from pathlib import Path as _Path

        if not isinstance(path, _Path):
            return
        self._p0_filename.set_value(path.name)
        try:
            size_bytes = path.stat().st_size
            if size_bytes >= 1_048_576:
                self._p0_filesize.set_value(f"{size_bytes / 1_048_576:.1f} MB")
            else:
                self._p0_filesize.set_value(f"{size_bytes / 1024:.1f} KB")
        except OSError:
            self._p0_filesize.set_value("—")

    def update_file_info(self, header: Any) -> None:
        """Populate page 0 from *header*.

        Parameters
        ----------
        header : astropy.io.fits.Header | dict | None
            FITS header for the selected frame.
        """
        if header is None:
            for row in (
                self._p0_telescop, self._p0_instrume,
                self._p0_exptime, self._p0_gain, self._p0_object,
            ):
                row.set_value("—")
            return

        def _get(key: str) -> str:
            try:
                val = header.get(key)
                return str(val) if val is not None else "—"
            except Exception:
                return "—"

        exptime = _get("EXPTIME")
        if exptime != "—":
            try:
                exptime = f"{float(exptime):.1f} s"
            except ValueError:
                pass

        self._p0_telescop.set_value(_get("TELESCOP"))
        self._p0_instrume.set_value(_get("INSTRUME"))
        self._p0_exptime.set_value(exptime)
        self._p0_gain.set_value(_get("GAIN"))
        self._p0_object.set_value(_get("OBJECT"))

    def update_wcs_info(self, wcs: Any) -> None:
        """Populate page 1 from a ``WCS`` object.

        Parameters
        ----------
        wcs : astropy.wcs.WCS | None
            Plate solution WCS, or ``None`` to reset to ``—``.
        """
        if wcs is None:
            for row in (
                self._p1_ra, self._p1_dec, self._p1_scale,
                self._p1_rotation, self._p1_matches,
            ):
                row.set_value("—")
            return

        try:
            nx = int(getattr(wcs, "pixel_shape", [None, None])[1] or 256)
            ny = int(getattr(wcs, "pixel_shape", [None, None])[0] or 256)
            sky = wcs.pixel_to_world(nx / 2, ny / 2)
            ra_str  = sky.ra.to_string(unit="hourangle", sep=":", precision=2, pad=True)
            dec_str = sky.dec.to_string(sep=":", precision=1, alwayssign=True)
            self._p1_ra.set_value(ra_str)
            self._p1_dec.set_value(dec_str)
        except Exception:
            self._p1_ra.set_value("—")
            self._p1_dec.set_value("—")

        try:
            from astropy.wcs.utils import proj_plane_pixel_scales
            import astropy.units as u
            scales = proj_plane_pixel_scales(wcs) * u.deg
            arcsec = scales[0].to(u.arcsec).value
            self._p1_scale.set_value(f"{arcsec:.3f} \"/px")
        except Exception:
            self._p1_scale.set_value("—")

        self._p1_rotation.set_value("—")
        self._p1_matches.set_value("—")

    def update_photometry_info(self, results: dict) -> None:
        """Populate page 2 from photometry configuration *results*.

        Parameters
        ----------
        results : dict
            Keys: ``target``, ``n_comp``, ``aperture``, ``ann_inner``,
            ``ann_outer``.
        """
        self._p2_target.set_value(str(results.get("target", "—")))
        self._p2_comp_n.set_value(str(results.get("n_comp", "—")))
        ap = results.get("aperture")
        self._p2_aperture.set_value(f"{ap} px" if ap is not None else "—")
        ai = results.get("ann_inner")
        self._p2_ann_inner.set_value(f"{ai} px" if ai is not None else "—")
        ao = results.get("ann_outer")
        self._p2_ann_outer.set_value(f"{ao} px" if ao is not None else "—")

    def update_transit_info(self, params: dict) -> None:
        """Populate page 3 from transit fit *params*.

        Parameters
        ----------
        params : dict
            Keys: ``t0``, ``duration_hours``, ``depth``, ``rp_over_rs``.
        """
        def _fmt(val: Any, fmt: str = "", suffix: str = "") -> str:
            if val is None:
                return "—"
            try:
                return f"{val:{fmt}}{suffix}"
            except (ValueError, TypeError):
                return str(val)

        self._p3_t0.set_value(_fmt(params.get("t0"), ".6f", " BJD"))
        self._p3_duration.set_value(_fmt(params.get("duration_hours"), ".2f", " h"))
        depth = params.get("depth")
        if depth is not None:
            try:
                self._p3_depth.set_value(f"{float(depth) * 100:.3f} %")
            except (TypeError, ValueError):
                self._p3_depth.set_value("—")
        else:
            self._p3_depth.set_value("—")
        self._p3_rprs.set_value(_fmt(params.get("rp_over_rs"), ".4f"))
