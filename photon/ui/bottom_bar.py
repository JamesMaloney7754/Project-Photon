"""Bottom bar widget — status messages, progress, and frame scrubber."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSlider,
    QWidget,
)

from photon.ui.theme import Colors, Typography


class BottomBarWidget(QWidget):
    """Thin bar at the bottom of the main window.

    Contains (left-to-right): a status message label, a spacer, an optional
    progress bar, and a frame scrubber slider with current/total frame labels.

    Signals
    -------
    frame_scrubbed : Signal(int)
        Emitted when the user moves the scrubber; carries the new frame index.
    """

    frame_scrubbed: Signal = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(
            f"background-color: {Colors.BASE};"
            f"border-top: 1px solid {Colors.BORDER};"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Status label
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_XS}px;"
        )
        layout.addWidget(self._status_lbl)

        layout.addStretch(1)

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setFixedWidth(160)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        layout.addWidget(self._progress, 0, Qt.AlignmentFlag.AlignVCenter)

        # Current frame label
        self._frame_lbl = QLabel("0")
        self._frame_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_XS}px;"
        )
        self._frame_lbl.setFixedWidth(30)
        self._frame_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._frame_lbl)

        # Scrubber slider
        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setFixedWidth(240)
        self._scrubber.setRange(0, 0)
        self._scrubber.setValue(0)
        self._scrubber.valueChanged.connect(self._on_scrubber_changed)
        layout.addWidget(self._scrubber, 0, Qt.AlignmentFlag.AlignVCenter)

        # Total frames label
        self._total_lbl = QLabel("/ 0")
        self._total_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_XS}px;"
        )
        self._total_lbl.setFixedWidth(36)
        layout.addWidget(self._total_lbl)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(self, message: str) -> None:
        """Update the status message.

        Parameters
        ----------
        message : str
            Text to display in the left-aligned status label.
        """
        self._status_lbl.setText(message)

    def show_progress(self, visible: bool) -> None:
        """Show or hide the progress bar.

        Parameters
        ----------
        visible : bool
            ``True`` to show, ``False`` to hide.
        """
        self._progress.setVisible(visible)

    def set_progress(self, value: int, maximum: int) -> None:
        """Set the progress bar value and maximum.

        Pass ``maximum=0`` for an indeterminate (busy) indicator.

        Parameters
        ----------
        value : int
            Current progress value.
        maximum : int
            Maximum value.  ``0`` means indeterminate.
        """
        self._progress.setMaximum(maximum)
        self._progress.setValue(value)

    def configure_scrubber(self, n_frames: int) -> None:
        """Set the scrubber range for *n_frames* frames.

        Parameters
        ----------
        n_frames : int
            Total number of frames in the current sequence.
        """
        maximum = max(0, n_frames - 1)
        self._scrubber.blockSignals(True)
        self._scrubber.setRange(0, maximum)
        self._scrubber.setValue(0)
        self._scrubber.blockSignals(False)
        self._total_lbl.setText(f"/ {n_frames}")
        self._frame_lbl.setText("0")

    def set_frame(self, index: int) -> None:
        """Move the scrubber to *index* without emitting :attr:`frame_scrubbed`.

        Parameters
        ----------
        index : int
            Frame index to display.
        """
        self._scrubber.blockSignals(True)
        self._scrubber.setValue(index)
        self._scrubber.blockSignals(False)
        self._frame_lbl.setText(str(index))

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_scrubber_changed(self, value: int) -> None:
        self._frame_lbl.setText(str(value))
        self.frame_scrubbed.emit(value)
