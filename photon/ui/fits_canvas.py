"""FITS image display canvas with drag-and-drop, scan shimmer, and drag hover."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import (
    QPropertyAnimation,
    QRect,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
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

# ── Empty-state widget ────────────────────────────────────────────────────────────────────────


class _EmptyStateWidget(QWidget):
    """Paints a drop-zone placeholder with an animated scan shimmer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {Colors.CANVAS_BG};")

        self._scan_offset: float = 0.0
        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(50)
        self._scan_timer.timeout.connect(self._tick_scan)
        self._scan_timer.start()

    def _tick_scan(self) -> None:
        self._scan_offset = (self._scan_offset + 0.005) % 1.0
        self.update()

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # ── Dashed rounded drop-zone rect ───────────────────────────────
        margin_x = int(w * 0.20)
        margin_y = int(h * 0.20)
        rect = QRect(margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

        pen = QPen(QColor(Colors.BORDER), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)

        # ── Scan shimmer band ─────────────────────────────────────────
        diag = math.sqrt(w * w + h * h)
        band_w = diag * 0.30
        t = self._scan_offset
        # Band centre moves from (-band_w) to (diag + band_w) along diagonal
        band_centre = (t * (diag + band_w * 2)) - band_w
        # Gradient perpendicular to top-left→bottom-right diagonal
        gx0 = band_centre - band_w / 2
        gy0 = 0.0
        gx1 = band_centre + band_w / 2
        gy1 = float(h)
        shimmer = QLinearGradient(gx0, gy0, gx1, gy1)
        shimmer.setColorAt(0.0, QColor(0, 0, 0, 0))
        shimmer.setColorAt(0.5, QColor(124, 58, 237, 15))   # VIOLET faint
        shimmer.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shimmer)
        painter.setClipRect(rect)
        painter.drawRect(0, 0, w, h)
        painter.setClipping(False)

        # Centre of the drop zone
        cx = w // 2
        cy = h // 2 - 20

        # ── Telescope icon ───────────────────────────────────────────
        icon_pen = QPen(QColor(Colors.TEXT_DISABLED), 2, Qt.PenStyle.SolidLine)
        icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(icon_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Aperture circle
        r_ap = 14
        painter.drawEllipse(cx - r_ap, cy - 30 - r_ap, r_ap * 2, r_ap * 2)
        # Eyepiece (small circle on top)
        painter.drawEllipse(cx - 4, cy - 30 - r_ap * 2 - 6, 8, 8)
        # Optical tube (rectangle below aperture)
        tube_w, tube_h = 14, 28
        painter.drawRect(cx - tube_w // 2, cy - 16, tube_w, tube_h)
        # Focuser knob on the right
        painter.drawRect(cx + tube_w // 2, cy - 4, 8, 6)
        painter.drawEllipse(cx + tube_w // 2 + 6, cy - 3, 4, 4)
        # Tripod legs
        painter.drawLine(cx - 7,  cy + 12, cx - 24, cy + 40)
        painter.drawLine(cx + 7,  cy + 12, cx + 24, cy + 40)
        painter.drawLine(cx,      cy + 12, cx,       cy + 40)
        # Tripod spreader ring
        painter.drawLine(cx - 18, cy + 30, cx + 18, cy + 30)

        # ── Primary text ────────────────────────────────────────────
        font1 = QFont("Inter")
        font1.setPixelSize(Typography.SIZE_MD)
        font1.setWeight(QFont.Weight(Typography.WEIGHT_MEDIUM))
        painter.setFont(font1)
        painter.setPen(QColor(Colors.TEXT_SECONDARY))
        text_y = cy + 58
        painter.drawText(
            QRect(0, text_y, w, Typography.SIZE_MD + 6),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "Drop FITS files here",
        )

        # ── Sub-text ─────────────────────────────────────────────────
        font2 = QFont("Inter")
        font2.setPixelSize(Typography.SIZE_XS)
        painter.setFont(font2)
        painter.setPen(QColor(Colors.TEXT_DISABLED))
        painter.drawText(
            QRect(0, text_y + Typography.SIZE_MD + 8, w, Typography.SIZE_XS + 4),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "or press Ctrl+O to open",
        )

        painter.end()


# ── Main canvas widget ──────────────────────────────────────────────────────────────────


class FitsCanvas(QWidget):
    """Embeds a Matplotlib figure for interactive FITS image display.

    When no image is loaded, an animated empty-state drop-zone is shown.
    When files are dragged over the widget, a violet overlay appears.
    When files are dropped, :attr:`files_dropped` is emitted.

    Signals
    -------
    files_dropped : Signal(list)
        Emitted with a sorted list of ``pathlib.Path`` objects when the user
        drops files or folders onto the canvas.
    star_clicked : Signal(float, float)
        Emitted with ``(x_px, y_px)`` image coordinates when the user clicks
        the canvas in ``select_target`` or ``select_comparison`` mode.
    """

    files_dropped: Signal = Signal(list)
    star_clicked:  Signal = Signal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._drag_active: bool = False
        self._interaction_mode: str = "none"   # "none" | "select_target" | "select_comparison"

        # Star overlay artists (matplotlib)
        self._star_overlay_artists: list[Any] = []
        self._target_xy: tuple[float, float] | None = None
        self._comparison_xys: list[tuple[float, float]] = []
        self._aperture_radius: float = 8.0
        self._annulus_inner:   float = 12.0
        self._annulus_outer:   float = 20.0

        # ── Matplotlib figure ───────────────────────────────────────────
        bg = Colors.CANVAS_BG
        self._figure = Figure(facecolor=bg, dpi=72)
        self._figure.set_tight_layout(False)
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor(bg)
        self._mpl_canvas = FigureCanvas(self._figure)
        self._mpl_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # Connect click handler for star selection
        self._mpl_canvas.mpl_connect("button_press_event", self._on_canvas_click)

        mpl_wrapper = QWidget()
        mpl_wrapper.setStyleSheet(f"background-color: {bg};")
        mpl_layout = QVBoxLayout(mpl_wrapper)
        mpl_layout.setContentsMargins(0, 0, 0, 0)
        mpl_layout.addWidget(self._mpl_canvas)

        # Opacity effect for fade-in on new image
        self._mpl_effect = QGraphicsOpacityEffect(mpl_wrapper)
        self._mpl_effect.setOpacity(1.0)
        mpl_wrapper.setGraphicsEffect(self._mpl_effect)
        self._mpl_anim = QPropertyAnimation(self._mpl_effect, b"opacity", self)
        self._mpl_anim.setDuration(400)
        self._mpl_wrapper = mpl_wrapper

        # ── Stacked widget ─────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(_EmptyStateWidget())
        self._stack.addWidget(mpl_wrapper)
        self._stack.setCurrentIndex(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._image_obj: Any = None
        self._stretch: str = "asinh"
        self._current_image: Any = None  # last displayed data; None when empty

        # Resize debounce — defer canvas redraw 150 ms after the last resize event
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._do_resize)

        # Catalog overlay artists (matplotlib)
        self._catalog_overlay_artists: list[Any] = []
        self._catalog_overlay_visible: bool = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_frame(self, data: np.ndarray, header: Any = None) -> None:
        """Stretch and render *data* with a fade-in animation on first display.

        Parameters
        ----------
        data : np.ndarray
            2-D science frame in raw calibrated ADU.
        header : astropy.io.fits.Header | dict | None
            FITS header for title decoration.
        """
        try:
            display_data = stretch_image(data, stretch=self._stretch)
        except Exception as exc:
            logger.warning("stretch_image failed (%s); using linear fallback.", exc)
            display_data = stretch_image(data, stretch="linear")

        self._current_image = display_data
        was_empty = self._image_obj is None

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
            self._image_obj.set_clim(
                float(display_data.min()), float(display_data.max())
            )

        self._ax.set_xticks([])
        self._ax.set_yticks([])

        title = ""
        if header is not None:
            obj  = header.get("OBJECT", "")
            filt = header.get("FILTER", "")
            parts = [p for p in (obj, filt) if p]
            title = "  |  ".join(parts)
        self._ax.set_title(
            title, color=Colors.TEXT_SECONDARY,
            fontsize=Typography.SIZE_XS, pad=4
        )

        self._stack.setCurrentIndex(1)
        self._mpl_canvas.draw_idle()

        # Fade in on first display
        if was_empty:
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
        self._current_image = None
        self._clear_star_artists()
        self._clear_catalog_artists()
        self._target_xy = None
        self._comparison_xys.clear()
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Catalog overlay
    # ------------------------------------------------------------------

    def display_catalog_overlay(self, wcs: Any, catalog_results: dict) -> None:
        """Draw catalog objects on the current image using *wcs* for projection.

        Renders three layers:
        - **Gaia DR3**: tiny grey dots (size 5, alpha 0.4) for background stars.
        - **SIMBAD**: small cyan diamonds labelled with the object name for
          sources within 3 arcmin of the image centre.
        - **VSX variables**: orange star (``"*"``) markers.

        A legend is drawn in the upper-right corner of the axes.

        Parameters
        ----------
        wcs : astropy.wcs.WCS
            Plate solution for RA/Dec → pixel conversion.
        catalog_results : dict
            ``{"simbad": Table, "gaia": Table, "vsx": Table}`` as returned by
            :func:`~photon.core.catalog.query_all_catalogs`.
        """
        import numpy as np

        self._clear_catalog_artists()

        if wcs is None or self._image_obj is None:
            return

        # ── Helper: RA/Dec columns → pixel coords ──────────────────────────────
        def _to_pixels(ra_arr: Any, dec_arr: Any) -> tuple[np.ndarray, np.ndarray]:
            from astropy.coordinates import SkyCoord
            import astropy.units as au
            coords = SkyCoord(ra=ra_arr, dec=dec_arr, unit=(au.deg, au.deg))
            xs, ys = wcs.world_to_pixel(coords)
            return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)

        # ── Image bounds for visibility check ───────────────────────────────
        img = self._image_obj.get_array()
        h, w = img.shape[:2]

        def _in_bounds(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
            return (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)

        legend_handles = []
        legend_labels  = []

        # ── Gaia DR3 — tiny grey dots ────────────────────────────────────
        gaia = catalog_results.get("gaia")
        if gaia is not None and len(gaia) > 0 and "ra" in gaia.colnames:
            try:
                gxs, gys = _to_pixels(
                    np.asarray(gaia["ra"],  dtype=float),
                    np.asarray(gaia["dec"], dtype=float),
                )
                mask = _in_bounds(gxs, gys)
                if mask.any():
                    sc = self._ax.scatter(
                        gxs[mask], gys[mask],
                        s=5, color="#888888", alpha=0.4, zorder=8,
                        marker="o", linewidths=0,
                    )
                    sc._photon_catalog = True  # type: ignore[attr-defined]
                    self._catalog_overlay_artists.append(sc)
                    legend_handles.append(sc)
                    legend_labels.append("Gaia DR3")
            except Exception as exc:
                logger.debug("Gaia overlay failed: %s", exc)

        # ── VSX — orange star markers ─────────────────────────────────────
        vsx = catalog_results.get("vsx")
        if vsx is not None and len(vsx) > 0 and "ra" in vsx.colnames:
            try:
                vxs, vys = _to_pixels(
                    np.asarray(vsx["ra"],  dtype=float),
                    np.asarray(vsx["dec"], dtype=float),
                )
                mask = _in_bounds(vxs, vys)
                if mask.any():
                    sc = self._ax.scatter(
                        vxs[mask], vys[mask],
                        s=60, color="#f97316", alpha=0.85, zorder=10,  # orange
                        marker="*", linewidths=0,
                    )
                    sc._photon_catalog = True  # type: ignore[attr-defined]
                    self._catalog_overlay_artists.append(sc)
                    legend_handles.append(sc)
                    legend_labels.append("VSX variable")
            except Exception as exc:
                logger.debug("VSX overlay failed: %s", exc)

        # ── SIMBAD — cyan diamonds with names ───────────────────────────────
        simbad = catalog_results.get("simbad")
        if simbad is not None and len(simbad) > 0 and "ra" in simbad.colnames:
            try:
                from astropy.coordinates import SkyCoord
                import astropy.units as au

                # Determine image centre in RA/Dec
                sky_centre = wcs.pixel_to_world(w / 2, h / 2)
                c_ra  = float(sky_centre.ra.deg)
                c_dec = float(sky_centre.dec.deg)
                centre_coord = SkyCoord(c_ra, c_dec, unit=au.deg)

                # Parse SIMBAD RA/Dec strings (sexagesimal) to degrees
                ra_str  = list(simbad["ra"])
                dec_str = list(simbad["dec"])
                try:
                    sky = SkyCoord(ra_str, dec_str, unit=(au.hourangle, au.deg))
                    ra_deg  = np.asarray(sky.ra.deg,  dtype=float)
                    dec_deg = np.asarray(sky.dec.deg, dtype=float)
                except Exception:
                    # Fall back: try treating as degrees
                    ra_deg  = np.asarray([float(r) for r in ra_str],  dtype=float)
                    dec_deg = np.asarray([float(d) for d in dec_str], dtype=float)

                sxs, sys_ = _to_pixels(ra_deg, dec_deg)
                mask = _in_bounds(sxs, sys_)

                if mask.any():
                    sc = self._ax.scatter(
                        sxs[mask], sys_[mask],
                        s=50, color="#22d3ee", alpha=0.9, zorder=11,  # cyan
                        marker="D", linewidths=0,
                    )
                    sc._photon_catalog = True  # type: ignore[attr-defined]
                    self._catalog_overlay_artists.append(sc)
                    legend_handles.append(sc)
                    legend_labels.append("SIMBAD")

                # Labels for objects within 3 arcmin of image centre
                names = list(simbad["name"])
                all_coords = SkyCoord(ra_deg, dec_deg, unit=au.deg)
                seps = centre_coord.separation(all_coords).to(au.arcmin).value

                indices = np.where(mask)[0]
                for i in indices:
                    if seps[i] < 3.0:
                        name = str(names[i]).strip()
                        if name:
                            txt = self._ax.text(
                                sxs[i] + 5, sys_[i] + 5, name,
                                color="#22d3ee", fontsize=5,
                                alpha=0.85, zorder=12,
                            )
                            txt._photon_catalog = True  # type: ignore[attr-defined]
                            self._catalog_overlay_artists.append(txt)

            except Exception as exc:
                logger.debug("SIMBAD overlay failed: %s", exc)

        # ── Legend ──────────────────────────────────────────────────────────────────────
        if legend_handles:
            leg = self._ax.legend(
                legend_handles, legend_labels,
                loc="upper right",
                fontsize=5,
                framealpha=0.5,
                facecolor=Colors.SURFACE,
                edgecolor=Colors.BORDER,
                labelcolor=Colors.TEXT_SECONDARY,
                markerscale=1.2,
            )
            leg._photon_catalog = True  # type: ignore[attr-defined]
            self._catalog_overlay_artists.append(leg)

        # Apply current visibility
        for art in self._catalog_overlay_artists:
            art.set_visible(self._catalog_overlay_visible)

        self._mpl_canvas.draw_idle()

    def toggle_catalog_overlay(self, visible: bool) -> None:
        """Show or hide catalog overlay artists without re-querying.

        Parameters
        ----------
        visible : bool
            ``True`` to show, ``False`` to hide.
        """
        self._catalog_overlay_visible = visible
        for art in self._catalog_overlay_artists:
            art.set_visible(visible)
        if self._catalog_overlay_artists:
            self._mpl_canvas.draw_idle()

    def _clear_catalog_artists(self) -> None:
        for art in self._catalog_overlay_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._catalog_overlay_artists.clear()

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

        xs = np.asarray(stars["x_centroid"], dtype=float)
        ys = np.asarray(stars["y_centroid"], dtype=float)

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
            import matplotlib.patches as mpatches
            tx, ty = self._target_xy

            tsc = self._ax.scatter(
                [tx], [ty],
                s=50, color="#7c3aed", zorder=6, alpha=0.9,  # Colors.VIOLET
            )
            tsc._photon_selection = True  # type: ignore[attr-defined]
            self._star_overlay_artists.append(tsc)

            for radius, color, ls in [
                (self._aperture_radius, "#7c3aed", "-"),   # Colors.VIOLET
                (self._annulus_inner,   "#f59e0b", "--"),  # Colors.GOLD
                (self._annulus_outer,   "#f59e0b", "--"),  # Colors.GOLD
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
                s=40, facecolors="none", edgecolors="#f59e0b",  # Colors.GOLD
                linewidths=1.2, zorder=6, alpha=0.9,
            )
            csc._photon_selection = True  # type: ignore[attr-defined]
            self._star_overlay_artists.append(csc)

            txt = self._ax.text(
                cx + 6, cy + 6, f"C{c_idx + 1}",
                color="#f59e0b", fontsize=6, zorder=7, alpha=0.9,  # Colors.GOLD
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
    # Resize debounce
    # ------------------------------------------------------------------

    def resizeEvent(self, event: Any) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._resize_timer.start()  # restarts on each resize; fires once idle

    def _do_resize(self) -> None:
        if self._current_image is not None:
            self._figure.tight_layout()
            self._mpl_canvas.draw_idle()

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            self._drag_active = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: Any) -> None:
        self._drag_active = False
        self.update()

    def dropEvent(self, event: Any) -> None:
        """Collect dropped paths, glob directories, emit :attr:`files_dropped`."""
        self._drag_active = False
        self.update()

        paths: list[Path] = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                paths.extend(p.rglob("*.fits"))
                paths.extend(p.rglob("*.fit"))
            elif p.suffix.lower() in (".fits", ".fit"):
                paths.append(p)

        paths = sorted(set(paths))
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def paintEvent(self, event: Any) -> None:  # type: ignore[override]
        super().paintEvent(event)

        if not self._drag_active:
            return

        # Violet drag-hover overlay
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(124, 58, 237, 40))   # Colors.VIOLET @ ~16% opacity
        pen = QPen(QColor(Colors.VIOLET), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 8, 8)
        painter.end()
