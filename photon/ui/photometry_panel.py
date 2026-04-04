"""Photometry panel — target/comparison selection and aperture configuration."""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from photon.core.settings_manager import get_settings_manager
from photon.ui.glass_panel import GlassPanel
from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)


# ── Aperture preview diagram ────────────────────────────────────────────────────


class AperturePreviewWidget(QWidget):
    """Draws three concentric circles showing aperture and annulus geometry.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(110, 110)
        self._aperture = 8.0
        self._inner    = 12.0
        self._outer    = 20.0

    def set_params(self, aperture: float, inner: float, outer: float) -> None:
        """Update geometry and repaint.

        Parameters
        ----------
        aperture, inner, outer : float
            Radii in pixels (proportional display only).
        """
        self._aperture = aperture
        self._inner    = inner
        self._outer    = outer
        self.update()

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        margin = 8
        scale = (min(w, h) / 2 - margin) / max(self._outer, 1.0)

        # Background
        painter.fillRect(self.rect(), QColor(Colors.CANVAS_BG))

        # Outer annulus boundary — dashed gold
        r_outer_px = int(self._outer * scale)
        pen_outer = QPen(QColor(Colors.GOLD), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r_outer_px, cy - r_outer_px,
                            r_outer_px * 2, r_outer_px * 2)

        # Inner annulus boundary — dashed gold
        r_inner_px = int(self._inner * scale)
        pen_inner = QPen(QColor(Colors.GOLD), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawEllipse(cx - r_inner_px, cy - r_inner_px,
                            r_inner_px * 2, r_inner_px * 2)

        # Aperture — solid violet
        r_ap_px = int(self._aperture * scale)
        pen_ap = QPen(QColor(Colors.VIOLET), 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen_ap)
        painter.setBrush(QColor(124, 58, 237, 40))  # VIOLET dim fill
        painter.drawEllipse(cx - r_ap_px, cy - r_ap_px,
                            r_ap_px * 2, r_ap_px * 2)

        # Centre dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Colors.VIOLET))
        painter.drawEllipse(cx - 2, cy - 2, 4, 4)

        painter.end()


# ── PhotometryPanel ─────────────────────────────────────────────────────────────


class PhotometryPanel(GlassPanel):
    """Panel for selecting target/comparison stars and running photometry.

    Signals
    -------
    select_target_requested : Signal()
        Emitted when the user clicks "Select Target" — instructs FitsCanvas
        to enter ``select_target`` interaction mode.
    select_comparison_requested : Signal()
        Emitted when the user clicks "Add manually" — instructs FitsCanvas
        to enter ``select_comparison`` interaction mode.
    auto_select_requested : Signal()
        Emitted when the user clicks "Auto-select" comparisons.
    run_photometry_requested : Signal()
        Emitted when the user clicks "Run Aperture Photometry".
    aperture_changed : Signal(float, float, float)
        Emitted (aperture_radius, annulus_inner, annulus_outer) whenever a
        spinbox changes.
    photometry_complete : Signal(dict)
        Emitted by :meth:`on_photometry_done` with the result dict.
    """

    select_target_requested:     Signal = Signal()
    select_comparison_requested: Signal = Signal()
    auto_select_requested:       Signal = Signal()
    run_photometry_requested:    Signal = Signal()
    aperture_changed:            Signal = Signal(float, float, float)
    photometry_complete:         Signal = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        sm = get_settings_manager()
        self._ap_r  = sm.get("photometry/aperture_radius_px")
        self._an_in = sm.get("photometry/annulus_inner_px")
        self._an_out = sm.get("photometry/annulus_outer_px")

        self._target_xy: Optional[tuple[float, float]] = None
        self._comparison_xys: list[tuple[float, float]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self._build_target_section(root)
        self._build_comparison_section(root)
        self._build_aperture_section(root)
        self._build_run_section(root)

        root.addStretch()

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"letter-spacing: 1px;"
            f"background-color: transparent;"
        )
        return lbl

    def _build_target_section(self, root: QVBoxLayout) -> None:
        root.addWidget(self._section_label("TARGET STAR"))

        instruction = QLabel("Click a star on the image to select your target")
        instruction.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_SM}px;"
            f"font-style: italic;"
            f"background-color: transparent;"
        )
        instruction.setWordWrap(True)
        root.addWidget(instruction)

        self._target_coord_lbl = QLabel("—")
        self._target_coord_lbl.setStyleSheet(
            f"color: {Colors.TEXT_GOLD};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_SM}px;"
            f"background-color: transparent;"
        )
        root.addWidget(self._target_coord_lbl)

        btn_row = QHBoxLayout()
        self._select_target_btn = QPushButton("Select Target")
        self._select_target_btn.clicked.connect(self.select_target_requested)
        btn_row.addWidget(self._select_target_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFlat(True)
        clear_btn.clicked.connect(self._clear_target)
        btn_row.addWidget(clear_btn)
        root.addLayout(btn_row)

    def _build_comparison_section(self, root: QVBoxLayout) -> None:
        root.addWidget(self._section_label("COMPARISON STARS"))

        auto_btn = QPushButton("Auto-select")
        auto_btn.clicked.connect(self.auto_select_requested)
        root.addWidget(auto_btn)

        self._comp_list = QListWidget()
        self._comp_list.setFixedHeight(90)
        self._comp_list.setStyleSheet(
            "background-color: transparent; border: none;"
        )
        root.addWidget(self._comp_list)

        btn_row2 = QHBoxLayout()
        add_btn = QPushButton("Add manually")
        add_btn.setFlat(True)
        add_btn.clicked.connect(self.select_comparison_requested)
        btn_row2.addWidget(add_btn)

        clear_all_btn = QPushButton("Clear all")
        clear_all_btn.setFlat(True)
        clear_all_btn.clicked.connect(self._clear_comparisons)
        btn_row2.addWidget(clear_all_btn)
        root.addLayout(btn_row2)

    def _build_aperture_section(self, root: QVBoxLayout) -> None:
        root.addWidget(self._section_label("APERTURE"))

        # Preview diagram
        self._preview = AperturePreviewWidget()
        self._preview.set_params(self._ap_r, self._an_in, self._an_out)
        root.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignHCenter)

        def _make_sb(value: float, suffix: str) -> QDoubleSpinBox:
            sb = QDoubleSpinBox()
            sb.setRange(1.0, 50.0)
            sb.setSingleStep(0.5)
            sb.setSuffix(suffix)
            sb.setValue(value)
            sb.setStyleSheet(
                f"color: {Colors.TEXT_GOLD};"
                f"background-color: {Colors.SURFACE_ALT};"
                f"font-family: {Typography.FONT_MONO};"
            )
            return sb

        sb_rows = [
            ("Aperture",    self._ap_r,  " px"),
            ("Ann. inner",  self._an_in, " px"),
            ("Ann. outer",  self._an_out, " px"),
        ]
        self._ap_sb  = _make_sb(self._ap_r,  " px")
        self._in_sb  = _make_sb(self._an_in, " px")
        self._out_sb = _make_sb(self._an_out, " px")

        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        for row, (label, sb) in enumerate(
            [("Aperture", self._ap_sb), ("Ann. inner", self._in_sb),
             ("Ann. outer", self._out_sb)]
        ):
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;"
                f"background-color: transparent;"
            )
            grid.addWidget(lbl, row, 0)
            grid.addWidget(sb, row, 1)
        root.addLayout(grid)

        # Wire spinboxes
        for sb in (self._ap_sb, self._in_sb, self._out_sb):
            sb.valueChanged.connect(self._on_aperture_changed)

        defaults_btn = QPushButton("Use settings defaults")
        defaults_btn.setFlat(True)
        defaults_btn.clicked.connect(self._restore_aperture_defaults)
        root.addWidget(defaults_btn)

    def _build_run_section(self, root: QVBoxLayout) -> None:
        self._run_btn = QPushButton("Run Aperture Photometry")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self.run_photometry_requested)
        root.addWidget(self._run_btn)

        self._run_progress = QProgressBar()
        self._run_progress.setFixedHeight(3)
        self._run_progress.setTextVisible(False)
        self._run_progress.setMaximum(0)   # indeterminate
        self._run_progress.setVisible(False)
        root.addWidget(self._run_progress)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_target(self, xy: tuple[float, float]) -> None:
        """Display target coordinates and enable the run button.

        Parameters
        ----------
        xy : tuple[float, float]
            Target pixel position ``(x, y)``.
        """
        self._target_xy = xy
        self._target_coord_lbl.setText(f"({xy[0]:.1f}, {xy[1]:.1f}) px")
        self._update_run_btn()

    def set_comparisons(self, xys: list[tuple[float, float]]) -> None:
        """Populate the comparison list widget.

        Parameters
        ----------
        xys : list of tuple
            Comparison star pixel positions.
        """
        self._comparison_xys = list(xys)
        self._comp_list.clear()
        for i, (cx, cy) in enumerate(xys):
            item = QListWidgetItem(f"C{i + 1}: ({cx:.1f}, {cy:.1f})")
            item.setForeground(QColor(Colors.TEXT_GOLD))
            self._comp_list.addItem(item)
        self._update_run_btn()

    def on_photometry_done(self, result: dict) -> None:
        """Called when the photometry worker completes.

        Parameters
        ----------
        result : dict
            Return value from :class:`~photon.workers.photometry_worker.PhotometryWorker`.
        """
        self._run_progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self.photometry_complete.emit(result)

    def set_running(self, running: bool) -> None:
        """Show or hide the indeterminate progress bar."""
        self._run_progress.setVisible(running)
        self._run_btn.setEnabled(not running)

    def get_aperture_params(self) -> tuple[float, float, float]:
        """Return current aperture parameters as ``(radius, inner, outer)``."""
        return (
            self._ap_sb.value(),
            self._in_sb.value(),
            self._out_sb.value(),
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _clear_target(self) -> None:
        self._target_xy = None
        self._target_coord_lbl.setText("—")
        self._update_run_btn()

    def _clear_comparisons(self) -> None:
        self._comparison_xys.clear()
        self._comp_list.clear()
        self._update_run_btn()

    def _update_run_btn(self) -> None:
        self._run_btn.setEnabled(
            self._target_xy is not None and len(self._comparison_xys) > 0
        )

    def _on_aperture_changed(self) -> None:
        r   = self._ap_sb.value()
        inn = self._in_sb.value()
        out = self._out_sb.value()
        self._preview.set_params(r, inn, out)
        self.aperture_changed.emit(r, inn, out)

    def _restore_aperture_defaults(self) -> None:
        sm = get_settings_manager()
        self._ap_sb.setValue(sm.get("photometry/aperture_radius_px"))
        self._in_sb.setValue(sm.get("photometry/annulus_inner_px"))
        self._out_sb.setValue(sm.get("photometry/annulus_outer_px"))
