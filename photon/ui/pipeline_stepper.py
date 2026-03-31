"""Pipeline stepper widget — horizontal progress indicator for the four-stage pipeline."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Signal, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget

from photon.ui.theme import Colors, Typography

_STEPS = ["Load", "Solve", "Photometry", "Transit"]
_CIRCLE_D = 24        # circle diameter px
_CIRCLE_R = _CIRCLE_D // 2
_LINE_W   = 40        # connector line width px
_LABEL_GAP = 5        # gap between circle bottom and label text


class PipelineStepperWidget(QWidget):
    """Horizontal four-step pipeline progress indicator.

    Each step is rendered as a 24-px circle with a step number, connected by
    40-px lines.  Steps are painted directly with ``QPainter``; no child
    widgets are used.

    Signals
    -------
    step_clicked : Signal(int)
        Emitted when a step circle or its label is clicked (0-indexed).
    """

    step_clicked: Signal = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._active: int = 0
        self._completed: set[int] = set()
        # Populated during paintEvent; used for click-hit detection
        self._step_hit_rects: list[QRect] = []

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
        """Preferred width fits all 4 steps and 3 connectors."""
        total_w = len(_STEPS) * _CIRCLE_D + (len(_STEPS) - 1) * _LINE_W + 80
        return QSize(total_w, 64)

    def paintEvent(self, _event: object) -> None:
        """Render all steps, connectors, and labels."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        n = len(_STEPS)
        total_content = n * _CIRCLE_D + (n - 1) * _LINE_W
        x_start = (w - total_content) // 2
        cy = _CIRCLE_R + 4          # vertical centre of circles
        label_y = cy + _CIRCLE_R + _LABEL_GAP

        self._step_hit_rects = []

        for i, label in enumerate(_STEPS):
            cx = x_start + i * (_CIRCLE_D + _LINE_W) + _CIRCLE_R

            # ── Connector line (drawn before circle so circle paints over it) ──
            if i < n - 1:
                line_x0 = cx + _CIRCLE_R
                line_x1 = cx + _CIRCLE_R + _LINE_W
                line_y  = cy
                pen = QPen(QColor(Colors.BORDER), 1)
                painter.setPen(pen)
                painter.drawLine(line_x0, line_y, line_x1, line_y)

            # ── Circle fill ──
            if i in self._completed:
                fill = QColor(Colors.ACCENT_SUCCESS)
            elif i == self._active:
                fill = QColor(Colors.ACCENT_PRIMARY)
            else:
                fill = QColor(Colors.BORDER)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawEllipse(cx - _CIRCLE_R, cy - _CIRCLE_R, _CIRCLE_D, _CIRCLE_D)

            # ── Circle content: checkmark or number ──
            font = QFont("Inter")
            font.setPixelSize(Typography.SIZE_SM)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)

            if i in self._completed:
                text_color = QColor(Colors.TEXT_PRIMARY)
                content = "✓"
            elif i == self._active:
                text_color = QColor(Colors.TEXT_PRIMARY)
                content = str(i + 1)
            else:
                text_color = QColor(Colors.TEXT_DISABLED)
                content = str(i + 1)

            painter.setPen(QPen(text_color))
            painter.drawText(
                QRect(cx - _CIRCLE_R, cy - _CIRCLE_R, _CIRCLE_D, _CIRCLE_D),
                Qt.AlignmentFlag.AlignCenter,
                content,
            )

            # ── Label below circle ──
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
            painter.drawText(lbl_rect, Qt.AlignCenter, label)

            # ── Hit rect (circle + label union) ──
            hit = QRect(cx - _CIRCLE_R - 4, cy - _CIRCLE_R - 4,
                        _CIRCLE_D + 8, _CIRCLE_D + _LABEL_GAP + fm.height() + 12)
            self._step_hit_rects.append(hit)

        painter.end()

    def mousePressEvent(self, event: object) -> None:
        """Emit :attr:`step_clicked` when a step is hit."""
        pos = event.pos()  # type: ignore[attr-defined]
        for i, rect in enumerate(self._step_hit_rects):
            if rect.contains(pos):
                self.step_clicked.emit(i)
                return
        super().mousePressEvent(event)  # type: ignore[arg-type]
