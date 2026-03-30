"""Session sidebar — left panel showing loaded files and sequence metadata."""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
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

from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)

_ITEM_HEIGHT = 46


class _FrameItemDelegate(QStyledItemDelegate):
    """Two-line item delegate for the file list.

    Line 1: filename in ``TEXT_PRIMARY``.
    Line 2: frame info (index + observation time) in ``TEXT_SECONDARY SIZE_XS``.
    """

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: object,
    ) -> None:
        painter.save()

        # Background
        if option.state & 0x0002:  # QStyle.State_Selected
            painter.fillRect(option.rect, QColor(Colors.ACCENT_PRIMARY))
            primary_color = QColor(Colors.TEXT_PRIMARY)
            secondary_color = QColor(Colors.TEXT_PRIMARY)
            secondary_color.setAlphaF(0.7)
        elif option.state & 0x2000:  # QStyle.State_MouseOver
            painter.fillRect(option.rect, QColor(Colors.SURFACE_ALT))
            primary_color = QColor(Colors.TEXT_PRIMARY)
            secondary_color = QColor(Colors.TEXT_SECONDARY)
        else:
            primary_color = QColor(Colors.TEXT_PRIMARY)
            secondary_color = QColor(Colors.TEXT_SECONDARY)

        rect = option.rect
        pad_x = 12
        pad_y = 6

        # Line 1 — filename
        font1 = QFont("Inter")
        font1.setPixelSize(Typography.SIZE_SM)
        painter.setFont(font1)
        painter.setPen(primary_color)
        line1_rect = rect.adjusted(pad_x, pad_y, -pad_x, 0)
        line1_rect.setHeight(Typography.SIZE_SM + 2)
        name = index.data(Qt.DisplayRole) or ""  # type: ignore[union-attr]
        painter.drawText(line1_rect, Qt.AlignLeft | Qt.AlignVCenter, name)

        # Line 2 — frame info
        font2 = QFont("JetBrains Mono, Consolas")
        font2.setPixelSize(Typography.SIZE_XS)
        painter.setFont(font2)
        painter.setPen(secondary_color)
        line2_rect = rect.adjusted(pad_x, pad_y + Typography.SIZE_SM + 4, -pad_x, -pad_y)
        secondary = index.data(Qt.UserRole) or ""  # type: ignore[union-attr]
        painter.drawText(line2_rect, Qt.AlignLeft | Qt.AlignVCenter, secondary)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: object) -> QSize:  # type: ignore[override]
        return QSize(option.rect.width(), _ITEM_HEIGHT)


class SessionSidebar(QWidget):
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
        Emitted when the user clicks the "Open Sequence…" button.
    """

    frame_selected: Signal = Signal(int)
    open_requested: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setStyleSheet(f"background-color: {Colors.SURFACE};")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        # ── Header label ──────────────────────────────────────────────
        header_lbl = QLabel("S E S S I O N")
        header_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-weight: bold;"
            f"letter-spacing: 1px;"
            f"padding: 0 12px 8px 12px;"
        )
        layout.addWidget(header_lbl)

        # ── File list ─────────────────────────────────────────────────
        self.file_list = QListWidget()
        self.file_list.setItemDelegate(_FrameItemDelegate(self.file_list))
        self.file_list.setUniformItemSizes(True)
        self.file_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.file_list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.file_list)

        # ── Separator ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {Colors.BORDER}; max-height: 1px; margin: 8px 0;")
        layout.addWidget(sep)

        # ── Metadata grid ─────────────────────────────────────────────
        meta_container = QWidget()
        meta_container.setStyleSheet("background-color: transparent;")
        meta_layout = QGridLayout(meta_container)
        meta_layout.setContentsMargins(12, 4, 12, 4)
        meta_layout.setHorizontalSpacing(8)
        meta_layout.setVerticalSpacing(4)

        _meta_keys = ["Frames", "Dimensions", "Filter", "Date Range", "Sky"]
        self._meta_values: dict[str, QLabel] = {}

        for row, key in enumerate(_meta_keys):
            key_lbl = QLabel(key)
            key_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_XS}px;"
            )
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY};"
                f"font-family: {Typography.FONT_MONO};"
                f"font-size: {Typography.SIZE_XS}px;"
            )
            meta_layout.addWidget(key_lbl, row, 0)
            meta_layout.addWidget(val_lbl, row, 1)
            self._meta_values[key] = val_lbl

        layout.addWidget(meta_container)

        # ── Spacer + open button ──────────────────────────────────────
        layout.addStretch(0)

        btn_container = QWidget()
        btn_container.setStyleSheet("background-color: transparent; padding: 0 12px;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(12, 8, 12, 0)

        self._open_btn = QPushButton("Open Sequence…")
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
        from photon.core.session import PhotonSession

        if not isinstance(session, PhotonSession):
            return

        self.file_list.clear()

        # Populate file list items
        for i, path in enumerate(session.fits_paths):
            header = headers[i] if i < len(headers) else {}
            # Try to get observation time for secondary line
            time_str = ""
            try:
                from photon.core.fits_loader import get_observation_times
                t = get_observation_times([header])
                time_str = t[0].isot if len(t) > 0 else ""
            except Exception:
                pass

            secondary = f"Frame {i}" + (f"  ·  {time_str}" if time_str else "")
            item = QListWidgetItem(path.name)
            item.setData(Qt.UserRole, secondary)
            self.file_list.addItem(item)

        # Populate metadata
        if session.image_stack is not None:
            n, h, w = session.image_stack.shape
            first_hdr = headers[0] if headers else {}

            self._meta_values["Frames"].setText(str(n))
            self._meta_values["Dimensions"].setText(f"{h} × {w}")
            self._meta_values["Filter"].setText(str(first_hdr.get("FILTER", "—")))

            # Date range
            date_str = "—"
            try:
                from photon.core.fits_loader import get_observation_times
                times = get_observation_times(headers)
                if len(times) == 1:
                    date_str = times[0].isot[:10]
                else:
                    date_str = f"{times[0].isot[:10]} → {times[-1].isot[:10]}"
            except Exception:
                pass
            self._meta_values["Date Range"].setText(date_str)

            # Sky background estimate
            sky_str = "—"
            try:
                from photon.core.fits_loader import summarize_sequence
                summary = summarize_sequence(
                    session.fits_paths, session.image_stack, headers
                )
                sky_str = f"{summary['median_sky']:.1f} ADU"
            except Exception:
                pass
            self._meta_values["Sky"].setText(sky_str)

    def clear(self) -> None:
        """Reset the file list and all metadata values to their defaults."""
        self.file_list.clear()
        for lbl in self._meta_values.values():
            lbl.setText("—")

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
