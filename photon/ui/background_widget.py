"""BackgroundWidget — deep space radial gradient background canvas."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget


class BackgroundWidget(QWidget):
    """Paints a deep space radial gradient behind all other panels.

    Two gradient layers are composited:

    1. A full-widget radial gradient from deep navy at the centre to near-black
       at the edges — the base starfield void.
    2. A small offset radial gradient in the upper-right quadrant that produces
       a barely-visible violet nebula bloom, composited with ``Screen`` mode.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2
        radius = math.sqrt(cx * cx + cy * cy)

        # ── Layer 1: deep navy → near-black radial gradient ──────────────
        grad1 = QRadialGradient(cx, cy, radius)
        grad1.setColorAt(0.0, QColor(10, 15, 26))    # BASE_CENTER #0a0f1a
        grad1.setColorAt(1.0, QColor(5,  7,  9))     # BASE_EDGE   #060810 approx
        painter.setBrush(grad1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, h)

        # ── Layer 2: violet nebula bloom (Screen composite) ───────────────
        bloom_cx = w * 0.70
        bloom_cy = h * 0.20
        bloom_r  = w * 0.40
        grad2 = QRadialGradient(bloom_cx, bloom_cy, bloom_r)
        grad2.setColorAt(0.0, QColor(124, 58, 237, 18))   # VIOLET_GLOW hint
        grad2.setColorAt(1.0, QColor(0,   0,   0,   0))   # transparent

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        painter.setBrush(grad2)
        painter.drawRect(0, 0, w, h)

        painter.end()
