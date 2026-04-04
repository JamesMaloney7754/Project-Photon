"""Light curve display panel — interactive matplotlib plot of differential flux."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from photon.ui.glass_panel import GlassPanel
from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)


class LightCurvePanel(GlassPanel):
    """Interactive light curve plot embedded in a glass panel.

    Displays differential magnitudes vs. time.  Left-clicking a point
    flags/unflags that frame.

    Signals
    -------
    frame_flagged : Signal(int, bool)
        Emitted when the user flags or unflags a point.  Carries
        ``(frame_index, is_flagged)``.
    """

    frame_flagged: Signal = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._light_curve: Any = None  # astropy Table
        self._hover_annotation: Any = None
        self._sc_good: Any = None
        self._sc_flag: Any = None
        self._median_line: Any = None
        self._fade_anim: Any = None   # FuncAnimation kept alive until complete

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # ── Header row ────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_lbl = QLabel("Light Curve")
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Typography.SIZE_MD}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"background-color: transparent;"
        )
        hdr.addWidget(title_lbl)
        hdr.addStretch()

        self._rms_lbl = QLabel("RMS: —")
        self._rms_lbl.setStyleSheet(
            f"color: {Colors.TEXT_GOLD};"
            f"font-family: {Typography.FONT_MONO};"
            f"font-size: {Typography.SIZE_SM}px;"
            f"background-color: transparent;"
        )
        hdr.addWidget(self._rms_lbl)

        self._export_btn = QPushButton("Export CSV")
        self._export_btn.setFlat(True)
        self._export_btn.setFixedHeight(26)
        self._export_btn.clicked.connect(self._on_export)
        hdr.addWidget(self._export_btn)

        root.addLayout(hdr)

        # ── Matplotlib canvas ─────────────────────────────────────────────
        bg = Colors.CANVAS_BG
        self._fig = Figure(facecolor=bg, tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._setup_axes()
        self._mpl_canvas = FigureCanvas(self._fig)
        self._mpl_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._mpl_canvas.mpl_connect("button_press_event", self._on_click)
        self._mpl_canvas.mpl_connect("motion_notify_event", self._on_hover)
        root.addWidget(self._mpl_canvas, 1)

        # ── Toolbar row ───────────────────────────────────────────────────
        tb = QHBoxLayout()
        self._reset_zoom_btn = QPushButton("Reset Zoom")
        self._reset_zoom_btn.setFlat(True)
        self._reset_zoom_btn.setFixedHeight(24)
        self._reset_zoom_btn.clicked.connect(self._reset_zoom)
        tb.addWidget(self._reset_zoom_btn)

        self._unflag_all_btn = QPushButton("Unflag all")
        self._unflag_all_btn.setFlat(True)
        self._unflag_all_btn.setFixedHeight(24)
        self._unflag_all_btn.clicked.connect(self._unflag_all)
        tb.addWidget(self._unflag_all_btn)

        self._show_flagged_cb = QCheckBox("Show flagged")
        self._show_flagged_cb.setChecked(True)
        self._show_flagged_cb.stateChanged.connect(self._replot)
        self._show_flagged_cb.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background-color: transparent;")
        tb.addWidget(self._show_flagged_cb)
        tb.addStretch()

        root.addLayout(tb)

        # Connect scroll wheel for zoom
        self._mpl_canvas.mpl_connect("scroll_event", self._on_scroll)

    # ------------------------------------------------------------------
    # Axes setup
    # ------------------------------------------------------------------

    def _setup_axes(self) -> None:
        ax = self._ax
        ax.set_facecolor("#080c10")
        ax.tick_params(
            colors=Colors.TEXT_SECONDARY,
            labelsize=Typography.SIZE_XS,
            which="both",
        )
        for spine in ax.spines.values():
            spine.set_edgecolor(Colors.BORDER)
        ax.set_xlabel("Frame Index", color=Colors.TEXT_SECONDARY, fontsize=Typography.SIZE_XS)
        ax.set_ylabel("Differential Magnitude", color=Colors.TEXT_SECONDARY,
                      fontsize=Typography.SIZE_XS)
        ax.yaxis.set_inverted(True)
        ax.grid(True, color="white", alpha=0.05, linewidth=0.5, linestyle="--")
        ax.set_title("", color=Colors.TEXT_SECONDARY)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_light_curve(self, light_curve: Any) -> None:
        """Render a new light curve with a 200 ms fade-in animation.

        Parameters
        ----------
        light_curve : astropy.table.Table
            Table with columns ``time``, ``mag``, ``mag_err``, ``flagged``,
            ``frame_index``.
        """
        from matplotlib.animation import FuncAnimation

        self._light_curve = light_curve

        # Stop any previous fade animation so it doesn't fight the new one.
        if self._fade_anim is not None:
            try:
                self._fade_anim.event_source.stop()
            except Exception:
                pass
            self._fade_anim = None

        self._replot()

        # Start scatter artists at alpha=0 then animate to final alpha.
        sc_good = self._sc_good
        sc_flag = self._sc_flag
        if sc_good is not None:
            sc_good.set_alpha(0.0)
        if sc_flag is not None:
            sc_flag.set_alpha(0.0)

        def _step(frame_num: int) -> None:
            progress = (frame_num + 1) / 10
            if sc_good is not None:
                sc_good.set_alpha(progress * 0.85)
            if sc_flag is not None:
                sc_flag.set_alpha(progress * 0.5)

        self._fade_anim = FuncAnimation(
            self._fig,
            _step,
            frames=10,
            interval=20,   # 20 ms × 10 frames = 200 ms total
            blit=False,
            repeat=False,
        )

        # Update RMS label
        flags = np.asarray(light_curve["flagged"], dtype=bool)
        mags = np.asarray(light_curve["mag"], dtype=float)
        good = ~flags
        if good.sum() > 1:
            rms = float(np.std(mags[good]))
            self._rms_lbl.setText(f"RMS: {rms:.4f} mag")
        else:
            self._rms_lbl.setText("RMS: —")

    def export_csv(self, path: Path) -> None:
        """Write the current light curve to a CSV file.

        Parameters
        ----------
        path : Path
            Destination CSV file path.
        """
        if self._light_curve is None:
            return
        self._light_curve.write(str(path), format="ascii.csv", overwrite=True)
        logger.info("Light curve exported to %s", path)

    # ------------------------------------------------------------------
    # Private plotting
    # ------------------------------------------------------------------

    def _replot(self) -> None:
        """Replot the light curve from the stored table."""
        if self._light_curve is None:
            return

        import numpy as np

        ax = self._ax
        ax.cla()
        self._setup_axes()

        lc = self._light_curve
        times   = np.asarray(lc["frame_index"], dtype=float)
        mags    = np.asarray(lc["mag"], dtype=float)
        flags   = np.asarray(lc["flagged"], dtype=bool)
        good    = ~flags

        # Unflagged points
        if good.any():
            self._sc_good = ax.scatter(
                times[good], mags[good],
                color="#7c3aed",   # Colors.VIOLET
                s=20, alpha=0.85, zorder=3, picker=5,
            )

        # Flagged points
        show_flagged = self._show_flagged_cb.isChecked()
        if show_flagged and flags.any():
            self._sc_flag = ax.scatter(
                times[flags], mags[flags],
                color="#ef4444",   # Colors.DANGER
                s=20, alpha=0.5, marker="x", zorder=2, picker=5,
            )

        # Median line
        if good.any():
            med = float(np.median(mags[good]))
            ax.axhline(med, color=Colors.TEXT_SECONDARY, linewidth=0.8,
                       alpha=0.5, linestyle="--")

        # Error bars
        if "mag_err" in lc.colnames and good.any():
            errs = np.asarray(lc["mag_err"], dtype=float)
            ax.errorbar(
                times[good], mags[good], yerr=errs[good],
                fmt="none", ecolor="#7c3aed", alpha=0.4, capsize=0,
            )

        self._mpl_canvas.draw_idle()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_click(self, event: Any) -> None:
        """Flag/unflag a point on left-click."""
        if event.button != 1 or self._light_curve is None:
            return
        if event.xdata is None or event.ydata is None:
            return

        import numpy as np
        lc = self._light_curve
        times = np.asarray(lc["frame_index"], dtype=float)
        mags  = np.asarray(lc["mag"], dtype=float)
        flags = np.asarray(lc["flagged"], dtype=bool)

        # Find nearest point in data coordinates
        try:
            ax = self._ax
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = max(xlim[1] - xlim[0], 1e-6)
            y_range = max(abs(ylim[1] - ylim[0]), 1e-6)
            dx = (times - event.xdata) / x_range
            dy = (mags  - event.ydata) / y_range
            dist = np.sqrt(dx**2 + dy**2)
            idx = int(np.argmin(dist))
            if dist[idx] > 0.05:
                return
        except Exception:
            return

        # Toggle flag
        new_flag = not bool(flags[idx])
        self._light_curve["flagged"][idx] = new_flag
        self._replot()
        frame_idx = int(lc["frame_index"][idx])
        self.frame_flagged.emit(frame_idx, new_flag)

    def _on_hover(self, event: Any) -> None:
        """Show an annotation tooltip on hover."""
        if event.xdata is None or self._light_curve is None:
            if self._hover_annotation is not None:
                self._hover_annotation.set_visible(False)
                self._mpl_canvas.draw_idle()
            return

        import numpy as np
        lc = self._light_curve
        times = np.asarray(lc["frame_index"], dtype=float)
        mags  = np.asarray(lc["mag"], dtype=float)

        ax = self._ax
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_range = max(xlim[1] - xlim[0], 1e-6)
        y_range = max(abs(ylim[1] - ylim[0]), 1e-6)
        dx = (times - event.xdata) / x_range
        dy = (mags  - event.ydata) / y_range
        dist = np.sqrt(dx**2 + dy**2)
        idx = int(np.argmin(dist))

        if dist[idx] > 0.04:
            if self._hover_annotation is not None:
                self._hover_annotation.set_visible(False)
                self._mpl_canvas.draw_idle()
            return

        mag_val  = float(mags[idx])
        frame_no = int(lc["frame_index"][idx])
        snr_val  = ""

        ann_text = f"Frame {frame_no}\nMag: {mag_val:.4f}"
        if self._hover_annotation is None:
            self._hover_annotation = ax.annotate(
                ann_text,
                xy=(times[idx], mags[idx]),
                xytext=(12, -20),
                textcoords="offset points",
                fontsize=Typography.SIZE_XS,
                color=Colors.TEXT_PRIMARY,
                bbox=dict(boxstyle="round,pad=0.4", fc=Colors.SURFACE_RAISED,
                          ec=Colors.VIOLET, alpha=0.9),
            )
        else:
            self._hover_annotation.set_text(ann_text)
            self._hover_annotation.xy = (times[idx], mags[idx])
            self._hover_annotation.set_visible(True)

        self._mpl_canvas.draw_idle()

    def _on_scroll(self, event: Any) -> None:
        """Zoom X axis on scroll wheel."""
        if event.xdata is None:
            return
        ax = self._ax
        xlim = ax.get_xlim()
        xrange = xlim[1] - xlim[0]
        factor = 0.9 if event.button == "up" else 1.1
        cx = event.xdata
        ax.set_xlim(cx - (cx - xlim[0]) * factor, cx + (xlim[1] - cx) * factor)
        self._mpl_canvas.draw_idle()

    def _reset_zoom(self) -> None:
        self._ax.autoscale()
        self._mpl_canvas.draw_idle()

    def _unflag_all(self) -> None:
        if self._light_curve is None:
            return
        import numpy as np
        n = len(self._light_curve)
        self._light_curve["flagged"] = np.zeros(n, dtype=bool)
        self._replot()

    def _on_export(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Light Curve", "", "CSV Files (*.csv)"
        )
        if path:
            self.export_csv(Path(path))
