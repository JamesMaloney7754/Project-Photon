"""Light curve panel — placeholder widget."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class LightCurvePanel(QWidget):
    """Placeholder panel for displaying photometric light curves.

    A full implementation will embed a Matplotlib canvas showing flux vs. time,
    with controls for detrending and period folding.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Light Curve Panel — not yet implemented.")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
