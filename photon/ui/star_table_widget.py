"""StarTableWidget — target + comparison star table with action buttons."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from photon.core.settings_manager import get_settings_manager
from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)


# ── Dot-column delegate ────────────────────────────────────────────────────────


class _DotDelegate(QStyledItemDelegate):
    """Paints a small filled circle for the first column."""

    _R = 4

    def paint(
        self,
        painter: object,
        option: QStyleOptionViewItem,
        index: object,
    ) -> None:  # type: ignore[override]
        from PySide6.QtGui import QPainter
        from PySide6.QtCore import Qt as _Qt

        color_str = index.data(_Qt.ItemDataRole.UserRole)  # type: ignore[attr-defined]
        if not color_str:
            return

        p = painter  # type: ignore[assignment]
        p.save()  # type: ignore[attr-defined]
        p.setRenderHint(QPainter.RenderHint.Antialiasing)  # type: ignore[attr-defined]
        cx = option.rect.center().x()  # type: ignore[attr-defined]
        cy = option.rect.center().y()  # type: ignore[attr-defined]
        r  = self._R
        p.setPen(_Qt.PenStyle.NoPen)  # type: ignore[attr-defined]
        p.setBrush(QColor(color_str))  # type: ignore[attr-defined]
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)  # type: ignore[attr-defined]
        p.restore()  # type: ignore[attr-defined]


# ── StarTableWidget ────────────────────────────────────────────────────────────


class StarTableWidget(QWidget):
    """Table showing detected / selected stars plus photometry action buttons.

    Columns: dot (20) | ID (50) | Role (60) | x,y (100) | SNR (50)

    Signals
    -------
    select_target_clicked : Signal()
    auto_select_clicked : Signal()
    run_photometry_clicked : Signal()
    row_clicked : Signal(str)
        Emits the star ID string for the clicked row.
    target_clear_requested : Signal()
    comparisons_clear_requested : Signal()
    aperture_changed : Signal(float, float, float)
        Emits (aperture_radius, annulus_inner, annulus_outer) on spinbox change.
    """

    select_target_clicked:       Signal = Signal()
    auto_select_clicked:         Signal = Signal()
    run_photometry_clicked:      Signal = Signal()
    row_clicked:                 Signal = Signal(str)
    target_clear_requested:      Signal = Signal()
    comparisons_clear_requested: Signal = Signal()
    aperture_changed:            Signal = Signal(float, float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        sm = get_settings_manager()
        self._ap_r  = float(sm.get("photometry/aperture_radius_px"))
        self._an_in = float(sm.get("photometry/annulus_inner_px"))
        self._an_out = float(sm.get("photometry/annulus_outer_px"))

        self._target_xy: Optional[tuple[float, float]] = None
        self._comparison_xys: list[tuple[float, float]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(6)

        self._build_top_buttons(root)
        self._build_table(root)
        self._build_subtitle(root)
        self._build_aperture_section(root)
        self._build_run_button(root)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_top_buttons(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(6)

        self._select_target_btn = QPushButton("Select Target")
        self._select_target_btn.clicked.connect(self.select_target_clicked)
        row.addWidget(self._select_target_btn)

        self._auto_btn = QPushButton("Auto-select")
        self._auto_btn.setFlat(True)
        self._auto_btn.clicked.connect(self.auto_select_clicked)
        row.addWidget(self._auto_btn)

        clear_t_btn = QPushButton("✕ Target")
        clear_t_btn.setFlat(True)
        clear_t_btn.setFixedHeight(28)
        clear_t_btn.clicked.connect(self.target_clear_requested)
        row.addWidget(clear_t_btn)

        clear_c_btn = QPushButton("✕ Comps")
        clear_c_btn.setFlat(True)
        clear_c_btn.setFixedHeight(28)
        clear_c_btn.clicked.connect(self.comparisons_clear_requested)
        row.addWidget(clear_c_btn)

        root.addLayout(row)

    def _build_table(self, root: QVBoxLayout) -> None:
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["", "ID", "Role", "x, y", "SNR"])
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)

        # Column widths
        hh = self._table.horizontalHeader()
        hh.resizeSection(0, 20)
        hh.resizeSection(1, 50)
        hh.resizeSection(2, 60)
        hh.resizeSection(3, 100)
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)

        # Row height
        self._table.verticalHeader().setDefaultSectionSize(28)

        # Dot delegate for column 0
        self._table.setItemDelegateForColumn(0, _DotDelegate(self._table))

        self._table.cellClicked.connect(self._on_cell_clicked)

        root.addWidget(self._table, 1)

    def _build_subtitle(self, root: QVBoxLayout) -> None:
        self._subtitle_lbl = QLabel("No stars detected")
        self._subtitle_lbl.setStyleSheet(
            f"color: {Colors.FG_4};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-style: italic;"
            f"background-color: transparent;"
        )
        root.addWidget(self._subtitle_lbl)

    def _build_aperture_section(self, root: QVBoxLayout) -> None:
        ap_lbl = QLabel("APERTURE")
        ap_lbl.setStyleSheet(
            f"color: {Colors.FG_4};"
            f"font-size: 8px;"
            f"letter-spacing: 1px;"
            f"background-color: transparent;"
        )
        root.addWidget(ap_lbl)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(3)

        def _sb(val: float, suffix: str) -> QDoubleSpinBox:
            sb = QDoubleSpinBox()
            sb.setRange(1.0, 60.0)
            sb.setSingleStep(0.5)
            sb.setSuffix(suffix)
            sb.setValue(val)
            sb.setFixedHeight(24)
            sb.setStyleSheet(
                f"color: {Colors.AMBER};"
                f"font-family: {Typography.FONT_MONO};"
                f"font-size: {Typography.SIZE_SM}px;"
            )
            return sb

        self._ap_sb  = _sb(self._ap_r,  " px")
        self._in_sb  = _sb(self._an_in, " px")
        self._out_sb = _sb(self._an_out, " px")

        for col, (lbl_txt, sb) in enumerate(
            [("Ap", self._ap_sb), ("Inner", self._in_sb), ("Outer", self._out_sb)]
        ):
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet(
                f"color: {Colors.FG_4}; font-size: 8px; background-color: transparent;"
            )
            grid.addWidget(lbl, 0, col)
            grid.addWidget(sb,  1, col)

        for sb in (self._ap_sb, self._in_sb, self._out_sb):
            sb.valueChanged.connect(self._on_aperture_changed)

        root.addLayout(grid)

    def _build_run_button(self, root: QVBoxLayout) -> None:
        self._run_btn = QPushButton("Run Aperture Photometry")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self.run_photometry_clicked)
        root.addWidget(self._run_btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate_detected(self, count: int) -> None:
        """Update the subtitle with the detection count."""
        self._subtitle_lbl.setText(
            f"{count} star{'s' if count != 1 else ''} detected"
        )

    def add_target(self, x: float, y: float, snr: float = 0.0) -> None:
        """Add or replace the target row."""
        self._target_xy = (x, y)
        self._refresh_table()
        self._check_enable_run()

    def add_comparison(
        self, index: int, x: float, y: float, snr: float = 0.0
    ) -> None:
        """Add or update comparison star *index* (0-based)."""
        while len(self._comparison_xys) <= index:
            self._comparison_xys.append((0.0, 0.0))
        self._comparison_xys[index] = (x, y)
        self._refresh_table()
        self._check_enable_run()

    def set_target(self, xy: tuple[float, float] | None) -> None:
        """Set target from (x, y) tuple or None."""
        self._target_xy = xy
        self._refresh_table()
        self._check_enable_run()

    def set_comparisons(self, xys: list[tuple[float, float]]) -> None:
        """Replace comparison list."""
        self._comparison_xys = list(xys)
        self._refresh_table()
        self._check_enable_run()

    def clear_target(self) -> None:
        """Clear target selection."""
        self._target_xy = None
        self._refresh_table()
        self._check_enable_run()

    def clear_comparisons(self) -> None:
        """Clear all comparison stars."""
        self._comparison_xys = []
        self._refresh_table()
        self._check_enable_run()

    def update_comparison_catalog_names(self, name_map: dict[int, str]) -> None:
        """Append catalog names to comparison rows in the table.

        Parameters
        ----------
        name_map : dict[int, str]
            Mapping of comparison index (0-based) to catalog name.
        """
        row_offset = 1 if self._target_xy is not None else 0
        for comp_idx, name in name_map.items():
            row = row_offset + comp_idx
            if row < self._table.rowCount():
                id_item = self._table.item(row, 1)
                xy_item = self._table.item(row, 3)
                if id_item is not None:
                    id_item.setText(name[:10] if len(name) > 10 else name)
                if xy_item is not None:
                    cx, cy = self._comparison_xys[comp_idx]
                    xy_item.setToolTip(
                        f"({cx:.1f}, {cy:.1f})  {name}"
                    )

    def get_aperture_params(self) -> tuple[float, float, float]:
        """Return ``(aperture_radius, annulus_inner, annulus_outer)``."""
        return self._ap_sb.value(), self._in_sb.value(), self._out_sb.value()

    def set_running(self, running: bool) -> None:
        """Enable/disable the run button while photometry is in progress."""
        self._run_btn.setEnabled(not running)
        self._run_btn.setText(
            "Running…" if running else "Run Aperture Photometry"
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        """Rebuild table rows from current target/comparison state."""
        self._table.setRowCount(0)

        # Target row
        if self._target_xy is not None:
            x, y = self._target_xy
            self._add_row(
                dot_color=Colors.AMBER,
                star_id="TGT",
                role="target",
                xy=f"({x:.1f}, {y:.1f})",
                snr="—",
            )

        # Comparison rows
        for i, (cx, cy) in enumerate(self._comparison_xys):
            self._add_row(
                dot_color=Colors.ACCENT,
                star_id=f"C{i + 1}",
                role="comp",
                xy=f"({cx:.1f}, {cy:.1f})",
                snr="—",
            )

    def _add_row(
        self,
        dot_color: str,
        star_id: str,
        role: str,
        xy: str,
        snr: str,
    ) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 28)

        # Col 0: dot (stored as UserRole data for delegate)
        dot_item = QTableWidgetItem()
        dot_item.setData(Qt.ItemDataRole.UserRole, dot_color)
        self._table.setItem(row, 0, dot_item)

        # Col 1: ID
        id_item = QTableWidgetItem(star_id)
        id_item.setForeground(QColor(Colors.FG))
        mono_font = QFont("JetBrains Mono")
        mono_font.setPixelSize(Typography.SIZE_SM)
        id_item.setFont(mono_font)
        self._table.setItem(row, 1, id_item)

        # Col 2: Role
        role_item = QTableWidgetItem(role)
        role_item.setForeground(QColor(Colors.FG_3))
        self._table.setItem(row, 2, role_item)

        # Col 3: x, y
        xy_item = QTableWidgetItem(xy)
        xy_item.setForeground(QColor(Colors.AMBER))
        xy_item.setFont(mono_font)
        self._table.setItem(row, 3, xy_item)

        # Col 4: SNR
        snr_item = QTableWidgetItem(snr)
        snr_item.setForeground(QColor(Colors.FG_3))
        snr_item.setFont(mono_font)
        self._table.setItem(row, 4, snr_item)

    def _check_enable_run(self) -> None:
        self._run_btn.setEnabled(
            self._target_xy is not None and len(self._comparison_xys) > 0
        )

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        id_item = self._table.item(row, 1)
        if id_item is not None:
            self.row_clicked.emit(id_item.text())

    def _on_aperture_changed(self) -> None:
        self.aperture_changed.emit(
            self._ap_sb.value(),
            self._in_sb.value(),
            self._out_sb.value(),
        )
