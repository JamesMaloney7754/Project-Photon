"""Session sidebar — left panel showing loaded files and sequence metadata."""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from photon.ui.glass_panel import GlassPanel
from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)

_ITEM_HEIGHT = 52


# ── Frame item delegate ─────────────────────────────────────────────────────


class _FrameItemDelegate(QStyledItemDelegate):
    """Two-line item delegate: filename + frame index / time in gold mono."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: object,
    ) -> None:
        painter.save()

        is_selected = bool(option.state & 0x0002)   # QStyle.State_Selected
        is_hovered  = bool(option.state & 0x2000)   # QStyle.State_MouseOver

        rect = option.rect
        pad_x = 14
        pad_y = 8

        # ── Background ──────────────────────────────────────────────────
        if is_selected:
            painter.fillRect(rect, QColor(124, 58, 237, 35))   # VIOLET_DIM
        elif is_hovered:
            painter.fillRect(rect, QColor(255, 255, 255, 10))

        # ── Left accent bar (selected only) ─────────────────────────────
        if is_selected:
            bar_rect = rect.adjusted(0, 0, 0, 0)
            bar_rect.setWidth(2)
            painter.fillRect(bar_rect, QColor(Colors.VIOLET))

        # ── Line 1 — filename ─────────────────────────────────────────
        font1 = QFont("Inter")
        font1.setPixelSize(Typography.SIZE_BASE)
        font1.setWeight(QFont.Weight(Typography.WEIGHT_MEDIUM))
        painter.setFont(font1)
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        line1_rect = rect.adjusted(pad_x, pad_y, -pad_x, 0)
        line1_rect.setHeight(Typography.SIZE_BASE + 2)
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""  # type: ignore[union-attr]
        painter.drawText(
            line1_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            name,
        )

        # ── Line 2 — frame info in gold mono ─────────────────────────
        font2 = QFont()
        font2.setFamily(Typography.FONT_MONO)
        font2.setPixelSize(Typography.SIZE_XS)
        painter.setFont(font2)
        painter.setPen(QColor(Colors.TEXT_GOLD))
        line2_rect = rect.adjusted(
            pad_x, pad_y + Typography.SIZE_BASE + 4, -pad_x, -pad_y
        )
        secondary = (
            index.data(Qt.ItemDataRole.UserRole) or ""  # type: ignore[union-attr]
        )
        painter.drawText(
            line2_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            secondary,
        )

        # ── Bottom separator ──────────────────────────────────────────
        painter.setPen(QColor(Colors.BORDER_SUBTLE))
        painter.drawLine(pad_x, rect.bottom(), rect.right() - pad_x, rect.bottom())

        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: object
    ) -> QSize:  # type: ignore[override]
        return QSize(option.rect.width(), _ITEM_HEIGHT)


# ── Stat card widget ──────────────────────────────────────────────────────


class _StatCard(QWidget):
    """A small rounded card displaying a label + value pair.

    Parameters
    ----------
    label : str
        Short description text shown above the value.
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {Colors.SURFACE_ALT};"
            f"border-radius: 6px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-weight: {Typography.WEIGHT_REGULAR};"
            f"background-color: transparent;"
        )
        layout.addWidget(self._label_lbl)

        self._value_lbl = QLabel("—")
        self._value_lbl.setStyleSheet(
            f"color: {Colors.TEXT_GOLD};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_MD}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"background-color: transparent;"
        )
        layout.addWidget(self._value_lbl)

    def set_value(self, text: str) -> None:
        """Update the displayed value.

        Parameters
        ----------
        text : str
            New value string.
        """
        self._value_lbl.setText(text)

    def reset(self) -> None:
        """Reset the value to the dash placeholder."""
        self._value_lbl.setText("—")


# ── SessionSidebar ────────────────────────────────────────────────────────


class SessionSidebar(GlassPanel):
    """Left panel showing loaded filenames and session metadata.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.

    Signals
    -------
    frame_selected : Signal(int)
        Emitted when the user clicks a filename; carries the frame index.
    open_requested : Signal()
        Emitted when the user clicks the open button.
    """

    frame_selected: Signal = Signal(int)
    open_requested: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        # ── Header row: dot + "Session" + "+" button ────────────────────
        header_row = QWidget()
        header_row.setStyleSheet("background-color: transparent;")
        hrow_layout = QHBoxLayout(header_row)
        hrow_layout.setContentsMargins(12, 0, 8, 0)
        hrow_layout.setSpacing(6)

        # Status dot
        dot_lbl = QLabel()
        dot_lbl.setFixedSize(8, 8)
        dot_lbl.setStyleSheet(
            f"background-color: {Colors.VIOLET};"
            f"border-radius: 4px;"
        )
        hrow_layout.addWidget(dot_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        session_lbl = QLabel("Session")
        session_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_SM}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"background-color: transparent;"
        )
        hrow_layout.addWidget(session_lbl, 1, Qt.AlignmentFlag.AlignVCenter)

        add_btn = QPushButton("+")
        add_btn.setFlat(True)
        add_btn.setFixedSize(24, 24)
        add_btn.setToolTip("Open Sequence… (Ctrl+O)")
        add_btn.clicked.connect(self.open_requested)
        add_btn.setStyleSheet(
            f"QPushButton {{"
            f"  color: {Colors.TEXT_SECONDARY};"
            f"  font-size: {Typography.SIZE_LG}px;"
            f"  font-weight: {Typography.WEIGHT_LIGHT};"
            f"  border-radius: 4px;"
            f"  background-color: transparent;"
            f"  border: none;"
            f"  padding: 0;"
            f"}}"
            f"QPushButton:hover {{"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  background-color: rgba(255, 255, 255, 15);"
            f"}}"
        )
        hrow_layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(header_row)
        layout.addSpacing(6)

        # ── File list ─────────────────────────────────────────────────────
        self.file_list = QListWidget()
        self.file_list.setItemDelegate(_FrameItemDelegate(self.file_list))
        self.file_list.setUniformItemSizes(True)
        self.file_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.file_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.file_list.setStyleSheet("background-color: transparent; border: none;")
        self.file_list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.file_list)

        layout.addSpacing(8)

        # ── Metadata stat cards (2-column grid) ─────────────────────────
        meta_container = QWidget()
        meta_container.setStyleSheet("background-color: transparent;")
        meta_grid = QGridLayout(meta_container)
        meta_grid.setContentsMargins(10, 4, 10, 4)
        meta_grid.setHorizontalSpacing(6)
        meta_grid.setVerticalSpacing(6)

        self._stat_frames  = _StatCard("Frames")
        self._stat_dims    = _StatCard("Dimensions")
        self._stat_filter  = _StatCard("Filter")
        self._stat_date    = _StatCard("Date")
        self._stat_sky     = _StatCard("Sky BG")

        cards = [
            self._stat_frames, self._stat_dims,
            self._stat_filter, self._stat_date,
            self._stat_sky,
        ]
        for i, card in enumerate(cards):
            meta_grid.addWidget(card, i // 2, i % 2)

        layout.addWidget(meta_container)
        layout.addSpacing(8)

        # ── Open Sequence button ────────────────────────────────────────
        btn_container = QWidget()
        btn_container.setStyleSheet("background-color: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(10, 0, 10, 0)

        self._open_btn = QPushButton("Open Sequence")
        self._open_btn.setShortcut("Ctrl+O")
        self._open_btn.setToolTip("Open one or more FITS files (Ctrl+O)")
        self._open_btn.clicked.connect(self.open_requested)
        btn_layout.addWidget(self._open_btn)

        layout.addWidget(btn_container)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, session: object, headers: list) -> None:
        """Fill the file list and metadata block from *session*.

        Parameters
        ----------
        session : PhotonSession
            Current session with ``fits_paths``, ``image_stack``, etc.
        headers : list of astropy.io.fits.Header
            Per-frame FITS headers.
        """
        if not hasattr(session, "fits_paths") or not hasattr(session, "image_stack"):
            logger.warning("SessionSidebar.populate: invalid session object; skipping")
            return

        self.file_list.clear()

        for i, path in enumerate(session.fits_paths):
            try:
                header = headers[i] if i < len(headers) else {}
                time_str = ""
                try:
                    from photon.core.fits_loader import get_observation_times
                    t = get_observation_times([header])
                    time_str = t[0].isot if len(t) > 0 else ""
                except Exception:
                    pass

                secondary = f"Frame {i}" + (f"  ·  {time_str}" if time_str else "")
                item = QListWidgetItem(path.name)
                item.setData(Qt.ItemDataRole.UserRole, secondary)
                self.file_list.addItem(item)
            except Exception:
                logger.exception("SessionSidebar.populate: error adding item %d", i)

        if session.image_stack is not None:
            n, h, w = session.image_stack.shape
            first_hdr = headers[0] if headers else {}

            self._stat_frames.set_value(str(n))
            self._stat_dims.set_value(f"{h}×{w}")
            self._stat_filter.set_value(str(first_hdr.get("FILTER", "—")))

            date_str = "—"
            try:
                from photon.core.fits_loader import get_observation_times
                times = get_observation_times(headers)
                if len(times) == 1:
                    date_str = times[0].isot[:10]
                elif len(times) > 1:
                    date_str = times[0].isot[:10]
            except Exception:
                pass
            self._stat_date.set_value(date_str)

            sky_str = "—"
            try:
                from photon.core.fits_loader import summarize_sequence
                summary = summarize_sequence(
                    session.fits_paths, session.image_stack, headers
                )
                sky_str = f"{summary['median_sky']:.1f}"
            except Exception:
                pass
            self._stat_sky.set_value(sky_str)

    def clear(self) -> None:
        """Reset the file list and all metadata values to their defaults."""
        self.file_list.clear()
        for card in (
            self._stat_frames, self._stat_dims, self._stat_filter,
            self._stat_date, self._stat_sky,
        ):
            card.reset()

    def set_selected_frame(self, index: int) -> None:
        """Select *index* in the list without emitting :attr:`frame_selected`.

        Parameters
        ----------
        index : int
            Frame index to select.
        """
        self.file_list.blockSignals(True)
        self.file_list.setCurrentRow(index)
        self.file_list.blockSignals(False)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            self.frame_selected.emit(row)
