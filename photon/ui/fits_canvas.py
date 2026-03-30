"""Matplotlib-in-Qt FITS display widget.

Embeds a Matplotlib figure in a Qt widget for interactive FITS image display.
Applies stretch transforms via ``photon.utils.stretch.stretch_image``.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from photon.utils.stretch import stretch_image

logger = logging.getLogger(__name__)


class FitsCanvas(QWidget):
    """Widget that displays a 2-D FITS image using Matplotlib.

    Embeds a ``FigureCanvasQTAgg`` and exposes a :meth:`display_data` method
    to update the displayed image without recreating the figure.

    Signals
    -------
    pixel_clicked : Signal(float, float)
        Emitted when the user clicks on the image, carrying ``(x, y)`` pixel
        coordinates (0-indexed, column-major convention).
    """

    pixel_clicked: Signal = Signal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stretch: str = "asinh"
        self._percentile_low: float = 1.0
        self._percentile_high: float = 99.5

        self._figure = Figure(tight_layout=True)
        self._ax = self._figure.add_subplot(111)
        self._ax.set_visible(False)

        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._canvas.mpl_connect("button_press_event", self._on_click)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._image_obj: Any = None  # matplotlib AxesImage, once drawn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_data(
        self,
        data: np.ndarray,
        *,
        stretch: str | None = None,
        percentile_low: float | None = None,
        percentile_high: float | None = None,
    ) -> None:
        """Render *data* on the canvas.

        Parameters
        ----------
        data : np.ndarray
            2-D science frame in raw calibrated ADU.
        stretch : str | None
            Override the current stretch algorithm.  See
            :func:`photon.utils.stretch.stretch_image` for valid names.
        percentile_low : float | None
            Override the lower percentile bound for the display interval.
        percentile_high : float | None
            Override the upper percentile bound for the display interval.
        """
        if stretch is not None:
            self._stretch = stretch
        if percentile_low is not None:
            self._percentile_low = percentile_low
        if percentile_high is not None:
            self._percentile_high = percentile_high

        try:
            display_data = stretch_image(
                data,
                stretch=self._stretch,
                percentile_low=self._percentile_low,
                percentile_high=self._percentile_high,
            )
        except Exception as exc:
            logger.warning("Stretch failed (%s); falling back to linear.", exc)
            display_data = stretch_image(data, stretch="linear")

        self._ax.set_visible(True)
        if self._image_obj is None:
            self._image_obj = self._ax.imshow(
                display_data,
                cmap="gray",
                origin="lower",
                interpolation="nearest",
                aspect="equal",
            )
        else:
            self._image_obj.set_data(display_data)
            self._image_obj.set_clim(float(display_data.min()), float(display_data.max()))

        self._ax.set_xlabel("X (px)")
        self._ax.set_ylabel("Y (px)")
        self._canvas.draw_idle()

    def clear(self) -> None:
        """Clear the displayed image."""
        self._ax.cla()
        self._ax.set_visible(False)
        self._image_obj = None
        self._canvas.draw_idle()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_click(self, event: Any) -> None:
        """Forward Matplotlib click events as Qt signals."""
        if event.inaxes is self._ax and event.xdata is not None:
            self.pixel_clicked.emit(float(event.xdata), float(event.ydata))
