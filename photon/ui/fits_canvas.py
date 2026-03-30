"""Matplotlib-in-Qt FITS display widget."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from photon.utils.stretch import stretch_image

logger = logging.getLogger(__name__)

_BG = "#1a1a1a"


class FitsCanvas(QWidget):
    """Embeds a Matplotlib figure for interactive FITS image display.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._figure = Figure(facecolor=_BG, tight_layout=True)
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor(_BG)
        self._ax.set_visible(False)

        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._image_obj: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_frame(
        self,
        data: np.ndarray,
        header: Any = None,
    ) -> None:
        """Stretch and render *data* on the canvas.

        Parameters
        ----------
        data : np.ndarray
            2-D science frame in raw calibrated ADU.
        header : astropy.io.fits.Header | dict | None
            FITS header used to populate the axes title (``OBJECT`` and
            ``FILTER`` keywords).  Pass ``None`` to suppress the title.
        """
        try:
            display_data = stretch_image(data)
        except Exception as exc:
            logger.warning("stretch_image failed (%s); using linear fallback.", exc)
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

        self._ax.set_xticks([])
        self._ax.set_yticks([])

        if header is not None:
            obj = header.get("OBJECT", "")
            filt = header.get("FILTER", "")
            parts = [p for p in (obj, filt) if p]
            title = "  |  ".join(parts) if parts else ""
            self._ax.set_title(title, color="white", fontsize=9, pad=4)
        else:
            self._ax.set_title("")

        self._canvas.draw_idle()

    def clear(self) -> None:
        """Clear the axes and remove the displayed image."""
        self._ax.cla()
        self._ax.set_facecolor(_BG)
        self._ax.set_visible(False)
        self._image_obj = None
        self._canvas.draw_idle()
