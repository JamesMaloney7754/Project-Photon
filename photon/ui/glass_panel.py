"""GlassPanel — base class for all floating glass-effect panels."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class GlassPanel(QWidget):
    """Base widget that paints a glass-morphism rounded rectangle.

    Subclass this instead of ``QWidget`` for sidebar, inspector, and any other
    floating panel.  The glass effect is painted manually in :meth:`paintEvent`
    so child widgets remain fully interactive.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    _RADIUS = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self._RADIUS
        rect = self.rect().adjusted(1, 1, -1, -1)

        # ── 1. Dark semi-transparent fill ────────────────────────────────
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(17, 24, 39, 220))   # GLASS_SURFACE @ ~86% opacity
        painter.drawRoundedRect(rect, r, r)

        # ── 2. Gradient border (light top-left → dark bottom-right) ──────
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(255, 255, 255, 45))
        grad.setColorAt(0.4, QColor(255, 255, 255, 12))
        grad.setColorAt(1.0, QColor(255, 255, 255, 4))
        pen = QPen()
        pen.setBrush(grad)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, r, r)

        # ── 3. Inner top-edge highlight (simulates glossy top rim) ───────
        inner = rect.adjusted(1, 1, -1, -1)
        clip_h = int(self.height() * 0.30)
        painter.setClipRect(inner.x(), inner.y(), inner.width(), clip_h)
        highlight_pen = QPen(QColor(255, 255, 255, 18), 1)
        painter.setPen(highlight_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner, r - 1, r - 1)
        painter.setClipping(False)

        painter.end()
