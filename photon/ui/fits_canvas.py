"""FITS image display canvas with drag-and-drop and empty-state rendering."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QPoint, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from photon.ui.theme import Colors, Typography
from photon.utils.stretch import stretch_image

logger = logging.getLogger(__name__)

# ── Empty-state widget ────────────────────────────────────────────────────────


class _EmptyStateWidget(QWidget):
    """Paints a drop-zone placeholder when no image is loaded."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {Colors.CANVAS_BG};")

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # ── Dashed rounded rect (drop zone) ──────────────────────────
        margin_x = int(w * 0.20)
        margin_y = int(h * 0.20)
        rect = QRect(margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

        pen = QPen(QColor(Colors.BORDER), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)

        # Centre of the drop zone
        cx = w // 2
        cy = h // 2 - 20

        # ── Telescope icon (QPainter line art) ────────────────────────
        icon_pen = QPen(QColor(Colors.TEXT_DISABLED), 2, Qt.SolidLine)
        icon_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(icon_pen)
        painter.setBrush(Qt.NoBrush)

        # Aperture circle
        r_ap = 14
        painter.drawEllipse(QPoint(cx, cy - 30), r_ap, r_ap)
        # Optical tube (rectangle below aperture)
        tube_w, tube_h = 14, 28
        painter.drawRect(cx - tube_w // 2, cy - 16, tube_w, tube_h)
        # Focuser knob (small rectangle on the right)
        painter.drawRect(cx + tube_w // 2, cy - 4, 6, 6)
        # Tripod legs
        painter.drawLine(cx - 7, cy + 12, cx - 24, cy + 40)
        painter.drawLine(cx + 7, cy + 12, cx + 24, cy + 40)
        painter.drawLine(cx,     cy + 12, cx,       cy + 40)
        # Tripod spreader ring
        painter.drawLine(cx - 18, cy + 30, cx + 18, cy + 30)

        # ── Primary text ─────────────────────────────────────────────
        font1 = QFont("Inter")
        font1.setPixelSize(Typography.SIZE_MD)
        painter.setFont(font1)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        text_y = cy + 58
        painter.drawText(
            QRect(0, text_y, w, Typography.SIZE_MD + 6),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "Drop FITS files here",
        )

        # ── Sub-text ─────────────────────────────────────────────────
        font2 = QFont("Inter")
        font2.setPixelSize(Typography.SIZE_XS)
        painter.setFont(font2)
        painter.setPen(QColor(Colors.TEXT_DISABLED))
        painter.drawText(
            QRect(0, text_y + Typography.SIZE_MD + 8, w, Typography.SIZE_XS + 4),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "or press Ctrl+O to open",
        )

        painter.end()


# ── Main canvas widget ────────────────────────────────────────────────────────


class FitsCanvas(QWidget):
    """Embeds a Matplotlib figure for interactive FITS image display.

    When no image is loaded, an empty-state drop-zone is shown.  When files
    are dragged and dropped onto the widget, :attr:`files_dropped` is emitted.

    Signals
    -------
    files_dropped : Signal(list)
        Emitted with a sorted list of ``pathlib.Path`` objects when the user
        drops files or folders onto the canvas.  Folders are recursively
        globbed for ``*.fits`` / ``*.fit`` files.
    """

    files_dropped: Signal = Signal(list)
    star_clicked:  Signal = Signal(float, float)   # (x_px, y_px) in image coordinates

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._drag_active: bool = False
        self._interaction_mode: str = "none"   # "none" | "select_target" | "select_comparison"

        # Star overlay artists (matplotlib)
        self._star_overlay_artists: list[Any] = []
        self._target_xy: tuple[float, float] | None = None
        self._comparison_xys: list[tuple[float, float]] = []
        self._aperture_radius: float = 8.0
        self._annulus_inner:   float = 12.0
        self._annulus_outer:   float = 20.0

        # ── Matplotlib figure ─────────────────────────────────────────────
        bg = Colors.CANVAS_BG
        self._figure = Figure(facecolor=bg, tight_layout=True)
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor(bg)
        self._mpl_canvas = FigureCanvas(self._figure)
        self._mpl_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        mpl_wrapper = QWidget()
        mpl_wrapper.setStyleSheet(f"background-color: {bg};")
        mpl_layout = QVBoxLayout(mpl_wrapper)
        mpl_layout.setContentsMargins(0, 0, 0, 0)
        mpl_layout.addWidget(self._mpl_canvas)

        # ── Stacked widget: page 0 = empty state, page 1 = matplotlib ─
        self._stack = QStackedWidget()
        self._stack.addWidget(_EmptyStateWidget())
        self._stack.addWidget(mpl_wrapper)
        self._stack.setCurrentIndex(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._image_obj: Any = None  # AxesImage once drawn
        self._stretch: str = "asinh"

        # Fade-in animation for the matplotlib wrapper (first display)
        self._mpl_effect = QGraphicsOpacityEffect(mpl_wrapper)
        self._mpl_effect.setOpacity(1.0)
        mpl_wrapper.setGraphicsEffect(self._mpl_effect)
        self._mpl_anim = QPropertyAnimation(self._mpl_effect, b"opacity", self)
        self._mpl_anim.setDuration(400)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_frame(self, data: np.ndarray, header: Any = None) -> None:
        """Stretch and render *data*.

        Parameters
        ----------
        data : np.ndarray
            2-D science frame in raw calibrated ADU.
        header : astropy.io.fits.Header | dict | None
            FITS header for title decoration.
        """
        was_empty = self._image_obj is None

        try:
            display_data = stretch_image(data, stretch=self._stretch)
        except Exception as exc:
            logger.warning("stretch_image failed (%s); using linear fallback.", exc)
            display_data = stretch_image(data, stretch="linear")

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

        # Title from header
        title = ""
        if header is not None:
            obj  = header.get("OBJECT", "")
            filt = header.get("FILTER", "")
            parts = [p for p in (obj, filt) if p]
            title = "  |  ".join(parts)
        self._ax.set_title(title, color=Colors.TEXT_SECONDARY,
                           fontsize=Typography.SIZE_XS, pad=4)

        self._stack.setCurrentIndex(1)
        self._mpl_canvas.draw_idle()

        # Fade in on first display
        if was_empty:
            # Connect click handler
            self._mpl_canvas.mpl_connect("button_press_event", self._on_canvas_click)
            self._mpl_effect.setOpacity(0.0)
            self._mpl_anim.stop()
            self._mpl_anim.setStartValue(0.0)
            self._mpl_anim.setEndValue(1.0)
            self._mpl_anim.start()

    def clear(self) -> None:
        """Reset to the empty state."""
        self._ax.cla()
        self._ax.set_facecolor(Colors.CANVAS_BG)
        self._image_obj = None
        self._star_overlay_artists.clear()
        self._target_xy = None
        self._comparison_xys.clear()
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Star overlay
    # ------------------------------------------------------------------

    def display_stars(self, stars: Any) -> None:
        """Draw star detection overlay markers on the current image.

        Parameters
        ----------
        stars : astropy.table.Table
            Source table from :func:`photon.core.star_detector.detect_stars`.
        """
        self._clear_star_artists()
        if stars is None or len(stars) == 0:
            self._mpl_canvas.draw_idle()
            return

        import numpy as np
        xs = np.asarray(stars["xcentroid"], dtype=float)
        ys = np.asarray(stars["ycentroid"], dtype=float)

        # All detected stars: small open circles
        sc = self._ax.scatter(
            xs, ys,
            s=40, facecolors="none", edgecolors="#6b7fa3",
            linewidths=0.8, alpha=0.7, zorder=4,
        )
        self._star_overlay_artists.append(sc)

        self._redraw_selection_overlay()
        self._mpl_canvas.draw_idle()

    def _redraw_selection_overlay(self) -> None:
        """Redraw target and comparison overlays on top of the star field."""
        # Remove previous selection artists
        for art in list(self._star_overlay_artists):
            if getattr(art, "_photon_selection", False):
                try:
                    art.remove()
                except Exception:
                    pass
                self._star_overlay_artists.remove(art)

        # Target star: filled violet circle + aperture/annulus rings
        if self._target_xy is not None:
            tx, ty = self._target_xy
            import matplotlib.patches as mpatches

            tsc = self._ax.scatter(
                [tx], [ty],
                s=50, color="#7c3aed", zorder=6, alpha=0.9,
            )
            tsc._photon_selection = True  # type: ignore[attr-defined]
            self._star_overlay_artists.append(tsc)

            for radius, color, ls in [
                (self._aperture_radius, "#7c3aed", "-"),
                (self._annulus_inner,   "#f59e0b", "--"),
                (self._annulus_outer,   "#f59e0b", "--"),
            ]:
                circ = mpatches.Circle(
                    (tx, ty), radius,
                    fill=False, edgecolor=color, linewidth=1.0,
                    linestyle=ls, alpha=0.8, zorder=5,
                )
                circ._photon_selection = True  # type: ignore[attr-defined]
                self._ax.add_patch(circ)
                self._star_overlay_artists.append(circ)

        # Comparison stars: open gold circles with C1, C2… labels
        for c_idx, (cx, cy) in enumerate(self._comparison_xys):
            import matplotlib.patches as mpatches
            csc = self._ax.scatter(
                [cx], [cy],
                s=40, facecolors="none", edgecolors="#f59e0b",
                linewidths=1.2, zorder=6, alpha=0.9,
            )
            csc._photon_selection = True  # type: ignore[attr-defined]
            self._star_overlay_artists.append(csc)

            txt = self._ax.text(
                cx + 6, cy + 6, f"C{c_idx + 1}",
                color="#f59e0b", fontsize=6, zorder=7, alpha=0.9,
            )
            txt._photon_selection = True  # type: ignore[attr-defined]
            self._star_overlay_artists.append(txt)

    def clear_star_overlay(self) -> None:
        """Remove all star overlay markers from the plot."""
        self._clear_star_artists()
        self._mpl_canvas.draw_idle()

    def _clear_star_artists(self) -> None:
        for art in self._star_overlay_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._star_overlay_artists.clear()

    def set_target(
        self,
        xy: tuple[float, float] | None,
        comparison_xys: list[tuple[float, float]] | None = None,
    ) -> None:
        """Update target and comparison positions and redraw overlay.

        Parameters
        ----------
        xy : tuple or None
            Target pixel position, or ``None`` to clear.
        comparison_xys : list of tuple or None
            Comparison star positions.
        """
        self._target_xy = xy
        if comparison_xys is not None:
            self._comparison_xys = list(comparison_xys)
        self._redraw_selection_overlay()
        self._mpl_canvas.draw_idle()

    def set_aperture_params(
        self,
        radius: float,
        inner: float,
        outer: float,
    ) -> None:
        """Update aperture/annulus radii and redraw the target overlay rings.

        Parameters
        ----------
        radius, inner, outer : float
            Aperture radius and annulus inner/outer radii in pixels.
        """
        self._aperture_radius = radius
        self._annulus_inner   = inner
        self._annulus_outer   = outer
        self._redraw_selection_overlay()
        self._mpl_canvas.draw_idle()

    # ------------------------------------------------------------------
    # Interaction mode
    # ------------------------------------------------------------------

    def set_interaction_mode(self, mode: str) -> None:
        """Set the mouse interaction mode.

        Parameters
        ----------
        mode : str
            One of ``"none"``, ``"select_target"``, ``"select_comparison"``.
        """
        self._interaction_mode = mode
        if mode in ("select_target", "select_comparison"):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()

    def _on_canvas_click(self, event: Any) -> None:
        """Handle matplotlib button_press_event and emit :attr:`star_clicked`."""
        if event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return
        if self._interaction_mode == "none":
            return
        self.star_clicked.emit(float(event.xdata), float(event.ydata))

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: Any) -> None:
        """Collect dropped paths, glob directories, emit :attr:`files_dropped`."""
        paths: list[Path] = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                # Recursive glob for FITS files inside the directory
                paths.extend(p.rglob("*.fits"))
                paths.extend(p.rglob("*.fit"))
            elif p.suffix.lower() in (".fits", ".fit"):
                paths.append(p)

        # Deduplicate and sort
        paths = sorted(set(paths))
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
