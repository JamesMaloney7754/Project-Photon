"""BigStatWidget — single metric cell with accent left-bar and flash animation."""

from __future__ import annotations

from PySide6.QtCore import Property, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from photon.ui.theme import Colors, Typography


class BigStatWidget(QWidget):
    """A single stat cell matching the cockpit BigStat component.

    Paints:
    1. A 2 px vertical accent line on the left edge (full height).
    2. Label — 8 px, uppercase, letter-spaced, ``FG_4`` monospace.
    3. Value — 18 px, ``FG`` monospace.
    4. Error / unit — 9 px, ``FG_3`` monospace.

    A short flash animation (value colour → white → back) fires on each
    :meth:`set_value` call.

    Parameters
    ----------
    label : str
        Short key string (e.g. ``"RA Center"``).
    value : str
        Initial value text (default ``"—"``).
    error : str
        Initial error / unit string (default ``""``).
    parent : QWidget | None
        Optional parent widget.
    """

    # ── Flash animation property ───────────────────────────────────────────

    def _get_flash(self) -> float:
        return self._flash

    def _set_flash(self, v: float) -> None:
        self._flash = v
        self.update()

    flash = Property(float, _get_flash, _set_flash)

    # ──────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        label: str = "",
        value: str = "—",
        error: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumSize(120, 72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._label  = label
        self._value  = value
        self._error  = error
        self._accent = Colors.ACCENT
        self._flash: float = 0.0

        self._flash_anim = QPropertyAnimation(self, b"flash", self)
        self._flash_anim.setDuration(300)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_label(self, text: str) -> None:
        """Update the label text."""
        self._label = text
        self.update()

    def set_value(self, text: str) -> None:
        """Update the value and trigger the flash animation."""
        self._value = text
        self._flash_anim.stop()
        self._flash_anim.setStartValue(1.0)
        self._flash_anim.setEndValue(0.0)
        self._flash_anim.start()
        self.update()

    def set_error(self, text: str) -> None:
        """Update the error / unit sub-line."""
        self._error = text
        self.update()

    def set_accent(self, color: str) -> None:
        """Change the accent line colour."""
        self._accent = color
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()

        # 1. Left accent bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._accent))
        painter.drawRect(0, 0, 2, self.height())

        # 2. Label — 8 px mono, FG_4, uppercase
        lbl_font = QFont("JetBrains Mono")
        lbl_font.setStyleHint(QFont.StyleHint.Monospace)
        lbl_font.setPixelSize(8)
        lbl_font.setWeight(QFont.Weight(Typography.WEIGHT_REGULAR))
        painter.setFont(lbl_font)
        painter.setPen(QColor(Colors.FG_4))
        painter.drawText(
            QRect(14, 14, w - 18, 12),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._label.upper(),
        )

        # 3. Value — 18 px mono, FG (with flash to white)
        f = self._flash
        vr = int(0xe7 + (0xff - 0xe7) * f)
        vg = int(0xec + (0xff - 0xec) * f)
        vb = int(0xf5 + (0xff - 0xf5) * f)
        val_font = QFont("JetBrains Mono")
        val_font.setStyleHint(QFont.StyleHint.Monospace)
        val_font.setPixelSize(18)
        val_font.setWeight(QFont.Weight(Typography.WEIGHT_REGULAR))
        painter.setFont(val_font)
        painter.setPen(QColor(vr, vg, vb))
        painter.drawText(
            QRect(14, 30, w - 18, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._value,
        )

        # 4. Error / unit — 9 px mono, FG_3
        if self._error:
            err_font = QFont("JetBrains Mono")
            err_font.setStyleHint(QFont.StyleHint.Monospace)
            err_font.setPixelSize(9)
            painter.setFont(err_font)
            painter.setPen(QColor(Colors.FG_3))
            painter.drawText(
                QRect(14, 54, w - 18, 13),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                self._error,
            )

        painter.end()
