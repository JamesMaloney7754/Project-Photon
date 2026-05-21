"""CockpitPane — reusable titled pane with header + content area."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from photon.ui.theme import Colors, Typography


class CockpitPane(QWidget):
    """A panel with a 38 px header and a content area below it.

    Header
    ------
    - Title: 9 px uppercase letter-spaced ACCENT text, left-aligned.
    - Subtitle: 9 px monospace FG_4 text, right-aligned.
    - Optional *right_widget*: placed on the right side of the header row.
    - Bottom border: 1 px BORDER line.

    Background: BG_PANEL with 1 px BORDER outline, 6 px corner radius.

    Parameters
    ----------
    title : str
        Pane title (rendered uppercase).
    subtitle : str
        Pane subtitle (muted monospace text on the right).
    parent : QWidget | None
        Optional parent widget.
    """

    _HEADER_H = 38
    _RADIUS   = 6

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title    = title
        self._subtitle = subtitle

        # ── Outer layout ─────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header strip ─────────────────────────────────────────────────
        self._header = _PaneHeaderWidget(self)
        self._header.setFixedHeight(self._HEADER_H)
        outer.addWidget(self._header)

        # ── Content placeholder ──────────────────────────────────────────
        self._content_wrapper = QWidget()
        self._content_wrapper.setStyleSheet("background-color: transparent;")
        self._content_layout = QVBoxLayout(self._content_wrapper)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        outer.addWidget(self._content_wrapper, 1)

        # Apply initial values
        self._header.set_title(title)
        self._header.set_subtitle(subtitle)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_title(self, text: str) -> None:
        """Update the pane title."""
        self._title = text
        self._header.set_title(text)

    def set_subtitle(self, text: str) -> None:
        """Update the pane subtitle."""
        self._subtitle = text
        self._header.set_subtitle(text)

    def set_content_widget(self, widget: QWidget) -> None:
        """Replace the content area with *widget*."""
        # Clear existing
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)  # type: ignore[arg-type]
        self._content_layout.addWidget(widget)

    def header_right_layout(self) -> QHBoxLayout:
        """Return the header's right sub-layout for custom controls."""
        return self._header.right_layout()

    # ------------------------------------------------------------------
    # Paint — background + border
    # ------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self._RADIUS
        rect = self.rect().adjusted(0, 0, -1, -1)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Colors.BG_PANEL))
        painter.drawRoundedRect(rect, r, r)

        painter.setPen(QPen(QColor(Colors.BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, r, r)

        painter.end()


# ── Internal header widget ─────────────────────────────────────────────────────


class _PaneHeaderWidget(QWidget):
    """Painted header strip — title left, subtitle right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title    = ""
        self._subtitle = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 10, 0)
        layout.setSpacing(6)

        # Spacer so right_layout can receive widgets
        layout.addStretch(1)

        self._right = QHBoxLayout()
        self._right.setSpacing(6)
        self._right.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._right)

    def set_title(self, text: str) -> None:
        self._title = text
        self.update()

    def set_subtitle(self, text: str) -> None:
        self._subtitle = text
        self.update()

    def right_layout(self) -> QHBoxLayout:
        return self._right

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # ── Title ─────────────────────────────────────────────────────────
        title_font = QFont("Inter")
        title_font.setPixelSize(9)
        title_font.setWeight(QFont.Weight(Typography.WEIGHT_BOLD))
        painter.setFont(title_font)
        painter.setPen(QColor(Colors.ACCENT))
        # Title left-aligned with 12px left padding
        painter.drawText(
            12, 0, w // 2, h,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._title.upper(),
        )

        # ── Subtitle ───────────────────────────────────────────────────────
        if self._subtitle:
            sub_font = QFont("JetBrains Mono")
            sub_font.setStyleHint(QFont.StyleHint.Monospace)
            sub_font.setPixelSize(9)
            painter.setFont(sub_font)
            painter.setPen(QColor(Colors.FG_4))
            # Right-aligned, leaves room for right_layout controls (80px)
            right_reserve = 80
            painter.drawText(
                w // 2, 0, w // 2 - right_reserve - 4, h,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._subtitle,
            )

        # ── Bottom border ──────────────────────────────────────────────────
        painter.setPen(QPen(QColor(Colors.BORDER), 1))
        painter.drawLine(0, h - 1, w, h - 1)

        painter.end()
