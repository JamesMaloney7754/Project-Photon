"""Transit panel — placeholder widget."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TransitPanel(QWidget):
    """Placeholder panel for displaying transit model fits.

    A full implementation will show a folded light curve overlay with the
    best-fit Mandel-Agol model and a parameter table.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Transit Panel — not yet implemented.")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
