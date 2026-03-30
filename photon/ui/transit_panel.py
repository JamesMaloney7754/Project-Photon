"""Transit model fit display panel — placeholder widget.

The full implementation will show:
- Phase-folded light curve overlaid with the best-fit Mandel-Agol model
- A parameter table: t0, period, Rp/Rs, duration, impact parameter, chi²
- Residuals sub-panel
- Export controls for ETD submission
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TransitPanel(QWidget):
    """Placeholder panel for displaying transit model fits.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("Transit Panel — not yet implemented.")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
