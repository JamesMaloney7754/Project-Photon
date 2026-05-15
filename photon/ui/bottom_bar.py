"""Bottom bar widget — status, pulsing indicator, frame scrubber, progress."""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSlider,
    QWidget,
)

from photon.ui.theme import Colors, Typography

# Dot diameter in pixels
_DOT_D = 6


class _PulseDot(QWidget):
    """A small circle that pulses between full and dim opacity.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def _get_dot_alpha(self) -> int:
        return self._alpha

    def _set_dot_alpha(self, value: int) -> None:
        self._alpha = value
        self.update()

    dot_alpha = Property(int, _get_dot_alpha, _set_dot_alpha)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_DOT_D + 4, _DOT_D + 4)
        self._alpha: int = 255
        self._loaded: bool = False
        self._warning: bool = False

        self._anim = QPropertyAnimation(self, b"dot_alpha", self)
        self._anim.setStartValue(255)
        self._anim.setEndValue(100)
        self._anim.setDuration(1500)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._anim.start()

    def set_loaded(self, loaded: bool) -> None:
        """Switch dot color between success-green (loaded) and grey (empty)."""
        self._loaded = loaded
        self.update()

    def set_warning(self, warning: bool) -> None:
        """Switch dot to amber warning color."""
        self._warning = warning
        self.update()

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._warning:
            color = QColor(245, 158, 11, self._alpha)  # Colors.GOLD amber
        elif self._loaded:
            color = QColor(16, 185, 129, self._alpha)  # Colors.SUCCESS
        else:
            color = QColor(45, 63, 92, self._alpha)    # Colors.TEXT_DISABLED
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(2, 2, _DOT_D, _DOT_D)
        painter.end()


class BottomBarWidget(QWidget):
    """Thin bar at the bottom of the main window.

    Contains (left-to-right): a pulsing status dot + message label,
    a center frame scrubber section, and a right-side progress bar.

    Signals
    -------
    frame_scrubbed : Signal(int)
        Emitted when the user moves the scrubber; carries the new frame index.
    """

    frame_scrubbed: Signal = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            "background-color: rgba(6, 8, 16, 200);"
            "border-top: 1px solid rgba(255, 255, 255, 15);"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        # ── Left: pulsing dot + status label ─────────────────────
        self._dot = _PulseDot(self)
        layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-size: {Typography.SIZE_SM}px;"
        )
        layout.addWidget(self._status_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch(1)

        # ── Center: frame scrubber ────────────────────────────
        self._scrubber_section = QWidget()
        self._scrubber_section.setStyleSheet("background-color: transparent;")
        sc_layout = QHBoxLayout(self._scrubber_section)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(6)

        frame_lbl = QLabel("F R A M E")
        frame_lbl.setStyleSheet(
            f"color: {Colors.TEXT_DISABLED};"
            f"font-size: {Typography.SIZE_XS}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"letter-spacing: 1px;"
        )
        sc_layout.addWidget(frame_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._frame_lbl = QLabel("0")
        self._frame_lbl.setStyleSheet(
            f"color: {Colors.TEXT_GOLD};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_MD}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
        )
        self._frame_lbl.setFixedWidth(28)
        self._frame_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        sc_layout.addWidget(self._frame_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setFixedWidth(200)
        self._scrubber.setRange(0, 0)
        self._scrubber.setValue(0)
        self._scrubber.valueChanged.connect(self._on_scrubber_changed)
        sc_layout.addWidget(self._scrubber, 0, Qt.AlignmentFlag.AlignVCenter)

        self._total_lbl = QLabel("/ 0")
        self._total_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_SM}px;"
        )
        self._total_lbl.setFixedWidth(32)
        sc_layout.addWidget(self._total_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._scrubber_section, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch(1)

        # ── Right: progress bar ───────────────────────────────
        self._progress = QProgressBar()
        self._progress.setFixedWidth(120)
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)

        self._progress_effect = QGraphicsOpacityEffect(self._progress)
        self._progress_effect.setOpacity(0.0)
        self._progress.setGraphicsEffect(self._progress_effect)

        self._progress_anim = QPropertyAnimation(
            self._progress_effect, b"opacity", self
        )
        self._progress_anim.setDuration(200)

        layout.addWidget(self._progress, 0, Qt.AlignmentFlag.AlignVCenter)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(self, message: str) -> None:
        """Update the status message.

        Parameters
        ----------
        message : str
            Text to display in the status label.
        """
        self._status_lbl.setText(message)

    def show_progress(self, visible: bool) -> None:
        """Fade the progress bar in or out.

        Parameters
        ----------
        visible : bool
            ``True`` to show (fade in), ``False`` to hide (fade out).
        """
        if visible:
            self._progress.setVisible(True)
        self._progress_anim.stop()
        self._progress_anim.setStartValue(self._progress_effect.opacity())
        self._progress_anim.setEndValue(1.0 if visible else 0.0)
        self._progress_anim.start()
        if not visible:
            self._progress_anim.finished.connect(
                lambda: self._progress.setVisible(False)
            )

    def set_progress(self, value: int, maximum: int) -> None:
        """Set the progress bar value and maximum.

        Parameters
        ----------
        value : int
            Current progress value.
        maximum : int
            Maximum value. ``0`` means indeterminate.
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
        self._dot.set_loaded(n_frames > 0)
        self._scrubber_section.setEnabled(n_frames > 0)

    def set_dot_warning(self, warning: bool) -> None:
        """Set the pulsing dot to amber warning color."""
        self._dot.set_warning(warning)

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
