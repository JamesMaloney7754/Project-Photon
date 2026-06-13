"""PipelineBadgeBar — horizontal row of pill-shaped pipeline stage badges."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from photon.ui.theme import Colors, Typography

_STAGES = ["LOADED", "SOLVED", "PHOTOMETRY", "TRANSIT"]
_PENDING  = 0
_ACTIVE   = 1
_COMPLETE = 2


class PipelineBadgeBar(QWidget):
    """A horizontal row of pill badges representing pipeline progress.

    Each badge shows a 6 px coloured dot and uppercase stage name text.
    The entire bar is painted via :meth:`paintEvent` — no child widgets.

    States
    ------
    pending  : FG_4 dot + text
    active   : ACCENT dot (with subtle glow) + ACCENT text
    complete : SUCCESS dot + FG_3 text

    Signals
    -------
    badge_clicked : Signal(int)
        Emitted with the badge index (0-3) when a badge is clicked.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    badge_clicked: Signal = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._states: list[int] = [_PENDING] * len(_STAGES)
        self._badge_rects: list[QRect] = []   # populated each paintEvent for hit-testing
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_stage_complete(self, index: int) -> None:
        """Mark *index* as completed."""
        if 0 <= index < len(_STAGES):
            self._states[index] = _COMPLETE
            self.update()

    def set_stage_active(self, index: int) -> None:
        """Mark *index* as the current active stage."""
        if 0 <= index < len(_STAGES):
            self._states[index] = _ACTIVE
            self.update()

    def set_stage_pending(self, index: int) -> None:
        """Reset *index* to pending (not yet started)."""
        if 0 <= index < len(_STAGES):
            self._states[index] = _PENDING
            self.update()

    # ------------------------------------------------------------------
    # Mouse hit-testing
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        from PySide6.QtCore import QPoint as _QPoint
        pos: _QPoint = event.pos()  # type: ignore[attr-defined]
        for i, rect in enumerate(self._badge_rects):
            if rect.contains(pos):
                self.badge_clicked.emit(i)
                return
        super().mousePressEvent(event)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        badge_font = QFont("JetBrains Mono")
        badge_font.setStyleHint(QFont.StyleHint.Monospace)
        badge_font.setPixelSize(9)
        badge_font.setWeight(QFont.Weight(Typography.WEIGHT_SEMIBOLD))
        painter.setFont(badge_font)
        fm = QFontMetrics(badge_font)

        pad_x   = 10   # horizontal text padding inside badge
        dot_r   = 3    # dot radius
        dot_gap = 5    # gap between dot and text
        gap     = 6    # gap between badges
        h       = self.height()

        x = 0
        new_rects: list[QRect] = []

        for i, stage in enumerate(_STAGES):
            state = self._states[i]

            # Colours by state
            if state == _COMPLETE:
                dot_color  = Colors.SUCCESS
                text_color = Colors.FG_3
            elif state == _ACTIVE:
                dot_color  = Colors.ACCENT
                text_color = Colors.ACCENT
            else:
                dot_color  = Colors.FG_4
                text_color = Colors.FG_4

            text_w  = fm.horizontalAdvance(stage)
            badge_w = pad_x + dot_r * 2 + dot_gap + text_w + pad_x
            badge_h = h - 2
            radius  = badge_h // 2

            # Store rect for hit-testing (include the +1 y offset)
            new_rects.append(QRect(x, 1, badge_w, badge_h))

            # Background pill
            painter.setPen(QPen(QColor(Colors.BORDER), 1))
            painter.setBrush(QColor(Colors.BG_PANEL))
            painter.drawRoundedRect(x, 1, badge_w, badge_h, radius, radius)

            # Active glow behind dot
            if state == _ACTIVE:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(220, 38, 38, 30))  # ACCENT dim
                painter.drawEllipse(
                    x + pad_x - dot_r,
                    badge_h // 2 + 1 - dot_r - 2,
                    (dot_r + 2) * 2, (dot_r + 2) * 2,
                )

            # Dot
            dot_cx = x + pad_x + dot_r
            dot_cy = badge_h // 2 + 1
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(dot_color))
            painter.drawEllipse(dot_cx - dot_r, dot_cy - dot_r, dot_r * 2, dot_r * 2)

            # Text
            painter.setPen(QColor(text_color))
            text_x = dot_cx + dot_r + dot_gap
            text_y = 1 + (badge_h - fm.height()) // 2 + fm.ascent()
            painter.drawText(text_x, text_y, stage)

            x += badge_w + gap

        self._badge_rects = new_rects
        painter.end()

    def sizeHint(self) -> object:  # type: ignore[override]
        badge_font = QFont("JetBrains Mono")
        badge_font.setPixelSize(9)
        fm = QFontMetrics(badge_font)
        total_w = 0
        for stage in _STAGES:
            tw = fm.horizontalAdvance(stage)
            total_w += 10 + 6 + 5 + tw + 10 + 6
        return QSize(total_w, 28)
