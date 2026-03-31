"""Pipeline stepper widget — animated floating pill progress indicator."""

from __future__ import annotations

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from photon.ui.theme import Colors, Typography

_STEPS = ["Load", "Solve", "Photometry", "Transit"]
_PILL_W  = 480
_PILL_H  = 52
_CIRCLE_D = 20
_CIRCLE_R = _CIRCLE_D // 2
_LINE_W   = 32
_LABEL_GAP = 4


class PipelineStepperWidget(QWidget):
    """Floating pill-shaped four-step pipeline progress indicator.

    The pill contains four step circles connected by lines.  The active step
    has a slow breathing glow-ring animation.  Steps are marked complete with
    a painted checkmark.

    Signals
    -------
    step_clicked : Signal(int)
        Emitted when a step circle or its label is clicked (0-indexed).
    """

    step_clicked: Signal = Signal(int)

    # ── Animated properties ───────────────────────────────────────────────

    def _get_glow_radius(self) -> int:
        return self._glow_radius

    def _set_glow_radius(self, value: int) -> None:
        self._glow_radius = value
        self.update()

    glow_radius = Property(int, _get_glow_radius, _set_glow_radius)

    def _get_bg_opacity(self) -> int:
        return self._bg_opacity

    def _set_bg_opacity(self, value: int) -> None:
        self._bg_opacity = value
        self.update()

    bg_opacity = Property(int, _get_bg_opacity, _set_bg_opacity)

    # ─────────────────────────────────────────────────────────────────────

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_PILL_W, _PILL_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._active: int = 0
        self._completed: set[int] = set()
        self._step_hit_rects: list[QRect] = []
        self._glow_radius: int = 6
        self._bg_opacity: int = 180

        # ── Glow pulse animation ──────────────────────────────────────────
        self._glow_anim = QPropertyAnimation(self, b"glow_radius", self)
        self._glow_anim.setStartValue(6)
        self._glow_anim.setEndValue(10)
        self._glow_anim.setDuration(1200)
        self._glow_anim.setLoopCount(-1)
        self._glow_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._glow_anim.start()

        # ── Hover background animation ────────────────────────────────────
        self._hover_anim = QPropertyAnimation(self, b"bg_opacity", self)
        self._hover_anim.setDuration(150)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_active_step(self, index: int) -> None:
        """Set the currently active step (0-indexed).

        Parameters
        ----------
        index : int
            Step index in ``[0, 3]``.
        """
        self._active = max(0, min(index, len(_STEPS) - 1))
        self.update()

    def set_step_complete(self, index: int) -> None:
        """Mark step *index* as completed (shows a checkmark).

        Parameters
        ----------
        index : int
            Step index in ``[0, 3]``.
        """
        self._completed.add(index)
        self.update()

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(_PILL_W, _PILL_H)

    def enterEvent(self, event: object) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._bg_opacity)
        self._hover_anim.setEndValue(210)
        self._hover_anim.start()
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._bg_opacity)
        self._hover_anim.setEndValue(180)
        self._hover_anim.start()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = _PILL_W
        h = _PILL_H
        pill_r = h // 2

        # ── Drop shadow (concentric semi-transparent ellipses below pill) ─
        shadow_cx = w // 2
        shadow_cy = h + 6
        for i in range(4):
            alpha = 40 - i * 9
            expand = i * 3
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawEllipse(
                shadow_cx - (w // 2 + expand),
                shadow_cy - (6 + expand // 2),
                w + expand * 2,
                12 + expand,
            )

        # ── Pill background ───────────────────────────────────────────────
        painter.setBrush(QColor(10, 15, 26, self._bg_opacity))
        pen = QPen(QColor(255, 255, 255, 25), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(0, 0, w - 1, h - 1, pill_r, pill_r)

        # ── Step layout geometry ──────────────────────────────────────────
        n = len(_STEPS)
        total_content = n * _CIRCLE_D + (n - 1) * _LINE_W
        x_start = (w - total_content) // 2
        cy = h // 2 - 6           # circle centre y (upper half of pill)
        label_y = cy + _CIRCLE_R + _LABEL_GAP

        self._step_hit_rects = []

        for i, label in enumerate(_STEPS):
            cx = x_start + i * (_CIRCLE_D + _LINE_W) + _CIRCLE_R

            # ── Connector line ────────────────────────────────────────────
            if i < n - 1:
                line_x0 = cx + _CIRCLE_R
                line_x1 = cx + _CIRCLE_R + _LINE_W
                line_y  = cy
                if i < len(self._completed) and (i + 1) in self._completed:
                    # Completed connector: violet → success gradient
                    conn_grad = QLinearGradient(line_x0, line_y, line_x1, line_y)
                    conn_grad.setColorAt(0.0, QColor(124, 58, 237))   # VIOLET
                    conn_grad.setColorAt(1.0, QColor(16, 185, 129))   # SUCCESS
                    conn_pen = QPen()
                    conn_pen.setBrush(conn_grad)
                    conn_pen.setWidth(1)
                    painter.setPen(conn_pen)
                else:
                    painter.setPen(QPen(QColor(Colors.BORDER), 1))
                painter.drawLine(line_x0, line_y, line_x1, line_y)

            # ── Active glow ring ──────────────────────────────────────────
            if i == self._active and i not in self._completed:
                gr = self._glow_radius
                glow_grad = QRadialGradient(cx, cy, gr + 4)
                glow_grad.setColorAt(0.0, QColor(124, 58, 237, 80))   # VIOLET
                glow_grad.setColorAt(1.0, QColor(124, 58, 237, 0))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow_grad)
                painter.drawEllipse(
                    cx - (_CIRCLE_R + gr), cy - (_CIRCLE_R + gr),
                    _CIRCLE_D + gr * 2,    _CIRCLE_D + gr * 2,
                )

            # ── Circle fill ───────────────────────────────────────────────
            if i in self._completed:
                fill = QColor(Colors.SUCCESS)
            elif i == self._active:
                fill = QColor(Colors.VIOLET)
            else:
                fill = QColor(255, 255, 255, 15)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawEllipse(cx - _CIRCLE_R, cy - _CIRCLE_R, _CIRCLE_D, _CIRCLE_D)

            # ── Circle content: checkmark or number ───────────────────────
            font = QFont("Inter")
            font.setPixelSize(Typography.SIZE_SM)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)

            if i in self._completed:
                # Draw checkmark with QPainter lines
                painter.setPen(QPen(QColor(Colors.TEXT_PRIMARY), 1.5))
                mid_x = cx - 3
                mid_y = cy + 2
                painter.drawLine(cx - 5, cy, mid_x, mid_y)
                painter.drawLine(mid_x, mid_y, cx + 5, cy - 4)
            else:
                text_color = (
                    QColor(Colors.TEXT_PRIMARY)
                    if i == self._active
                    else QColor(Colors.TEXT_DISABLED)
                )
                painter.setPen(QPen(text_color))
                painter.drawText(
                    QRect(cx - _CIRCLE_R, cy - _CIRCLE_R, _CIRCLE_D, _CIRCLE_D),
                    Qt.AlignmentFlag.AlignCenter,
                    str(i + 1),
                )

            # ── Label below circle ────────────────────────────────────────
            lbl_font = QFont("Inter")
            lbl_font.setPixelSize(Typography.SIZE_XS)
            painter.setFont(lbl_font)

            if i in self._completed or i == self._active:
                lbl_color = QColor(Colors.TEXT_PRIMARY)
            else:
                lbl_color = QColor(Colors.TEXT_DISABLED)
            painter.setPen(QPen(lbl_color))

            fm = QFontMetrics(lbl_font)
            lbl_w = fm.horizontalAdvance(label) + 4
            lbl_rect = QRect(cx - lbl_w // 2, label_y, lbl_w, fm.height() + 2)
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, label)

            # ── Hit rect ──────────────────────────────────────────────────
            hit = QRect(
                cx - _CIRCLE_R - 4, cy - _CIRCLE_R - 4,
                _CIRCLE_D + 8, _CIRCLE_D + _LABEL_GAP + fm.height() + 12,
            )
            self._step_hit_rects.append(hit)

        painter.end()

    def mousePressEvent(self, event: object) -> None:
        pos = event.pos()  # type: ignore[attr-defined]
        for i, rect in enumerate(self._step_hit_rects):
            if rect.contains(pos):
                self.step_clicked.emit(i)
                return
        super().mousePressEvent(event)  # type: ignore[arg-type]
