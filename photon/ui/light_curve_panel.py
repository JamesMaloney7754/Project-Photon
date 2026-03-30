"""Light curve display panel — placeholder widget.

The full implementation will embed a Matplotlib canvas showing differential
flux vs. time for the target and comparison stars, with controls for:
- Choosing the target and comparison ensemble
- Detrending options (polynomial, Gaussian process)
- Period folding
- Export to CSV / AAVSO submission format
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class LightCurvePanel(QWidget):
    """Placeholder panel for displaying photometric light curves.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Light Curve Panel — not yet implemented.")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
