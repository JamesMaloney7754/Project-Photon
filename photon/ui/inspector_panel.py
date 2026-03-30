"""Inspector panel — context-sensitive right panel for the active pipeline step."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)


def _section_header(text: str) -> QLabel:
    """Return a styled section-header QLabel."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECONDARY};"
        f"font-size: {Typography.SIZE_XS}px;"
        f"font-weight: bold;"
        f"letter-spacing: 1px;"
        f"padding-bottom: 6px;"
    )
    return lbl


def _key_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;"
    )
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return lbl


def _value_label(placeholder: str = "—") -> QLabel:
    lbl = QLabel(placeholder)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_PRIMARY};"
        f"font-family: {Typography.FONT_MONO};"
        f"font-size: {Typography.SIZE_SM}px;"
    )
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def _separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet(
        f"background-color: {Colors.BORDER}; max-height: 1px; margin: 8px 0;"
    )
    return sep


def _page_wrapper(inner: QWidget) -> QScrollArea:
    """Wrap *inner* in a scrollable area with consistent padding."""
    scroll = QScrollArea()
    scroll.setWidget(inner)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setStyleSheet(
        f"QScrollArea {{ background-color: {Colors.SURFACE}; border: none; }}"
    )
    return scroll


class InspectorPanel(QWidget):
    """Context-sensitive inspector panel with one page per pipeline step.

    Use :meth:`set_step` to switch pages.  Each ``update_*`` method populates
    the corresponding page with live data.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setStyleSheet(f"background-color: {Colors.SURFACE};")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_page0())
        self._stack.addWidget(self._build_page1())
        self._stack.addWidget(self._build_page2())
        self._stack.addWidget(self._build_page3())

        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------

    def _build_page0(self) -> QScrollArea:
        """File info page."""
        w = QWidget()
        w.setStyleSheet(f"background-color: {Colors.SURFACE};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        layout.addWidget(_section_header("F I L E  I N F O"))
        layout.addWidget(_separator())

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self._p0_filename  = _value_label()
        self._p0_filesize  = _value_label()
        self._p0_telescop  = _value_label()
        self._p0_instrume  = _value_label()
        self._p0_exptime   = _value_label()
        self._p0_gain      = _value_label()
        self._p0_object    = _value_label()

        rows = [
            ("File",       self._p0_filename),
            ("Size",       self._p0_filesize),
            ("Telescope",  self._p0_telescop),
            ("Instrument", self._p0_instrume),
            ("Exposure",   self._p0_exptime),
            ("Gain",       self._p0_gain),
            ("Object",     self._p0_object),
        ]
        for row, (key, val) in enumerate(rows):
            grid.addWidget(_key_label(key), row, 0)
            grid.addWidget(val, row, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return _page_wrapper(w)

    def _build_page1(self) -> QScrollArea:
        """Plate solution page."""
        w = QWidget()
        w.setStyleSheet(f"background-color: {Colors.SURFACE};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        layout.addWidget(_section_header("P L A T E  S O L V E"))
        layout.addWidget(_separator())

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self._p1_ra       = _value_label()
        self._p1_dec      = _value_label()
        self._p1_scale    = _value_label()
        self._p1_rotation = _value_label()
        self._p1_matches  = _value_label()

        rows = [
            ("RA center",   self._p1_ra),
            ("Dec center",  self._p1_dec),
            ("Pixel scale", self._p1_scale),
            ("Rotation",    self._p1_rotation),
            ("Cat. matches", self._p1_matches),
        ]
        for row, (key, val) in enumerate(rows):
            grid.addWidget(_key_label(key), row, 0)
            grid.addWidget(val, row, 1)

        layout.addLayout(grid)
        layout.addWidget(_separator())

        self._solve_btn = QPushButton("Solve Field")
        self._solve_btn.setObjectName("solve_btn")
        layout.addWidget(self._solve_btn)
        layout.addStretch()
        return _page_wrapper(w)

    def _build_page2(self) -> QScrollArea:
        """Photometry page."""
        w = QWidget()
        w.setStyleSheet(f"background-color: {Colors.SURFACE};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        layout.addWidget(_section_header("P H O T O M E T R Y"))
        layout.addWidget(_separator())

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self._p2_target    = _value_label()
        self._p2_comp_n    = _value_label()
        self._p2_aperture  = _value_label()
        self._p2_ann_inner = _value_label()
        self._p2_ann_outer = _value_label()

        rows = [
            ("Target",        self._p2_target),
            ("Comp. stars",   self._p2_comp_n),
            ("Aperture",      self._p2_aperture),
            ("Ann. inner",    self._p2_ann_inner),
            ("Ann. outer",    self._p2_ann_outer),
        ]
        for row, (key, val) in enumerate(rows):
            grid.addWidget(_key_label(key), row, 0)
            grid.addWidget(val, row, 1)

        layout.addLayout(grid)
        layout.addWidget(_separator())

        run_btn = QPushButton("Run Photometry")
        layout.addWidget(run_btn)
        layout.addStretch()
        return _page_wrapper(w)

    def _build_page3(self) -> QScrollArea:
        """Transit parameters page."""
        w = QWidget()
        w.setStyleSheet(f"background-color: {Colors.SURFACE};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        layout.addWidget(_section_header("T R A N S I T"))
        layout.addWidget(_separator())

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self._p3_t0       = _value_label()
        self._p3_duration = _value_label()
        self._p3_depth    = _value_label()
        self._p3_rprs     = _value_label()

        rows = [
            ("Mid-transit (BJD)", self._p3_t0),
            ("Duration",          self._p3_duration),
            ("Depth",             self._p3_depth),
            ("Rp/Rs",             self._p3_rprs),
        ]
        for row, (key, val) in enumerate(rows):
            grid.addWidget(_key_label(key), row, 0)
            grid.addWidget(val, row, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return _page_wrapper(w)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_step(self, index: int) -> None:
        """Switch to the page corresponding to pipeline *index*.

        Parameters
        ----------
        index : int
            Step index ``[0, 3]``.
        """
        self._stack.setCurrentIndex(max(0, min(index, 3)))

    def set_current_frame_path(self, path: object) -> None:
        """Populate the filename and file-size fields on page 0.

        Parameters
        ----------
        path : pathlib.Path
            Path to the FITS file for the currently selected frame.
        """
        from pathlib import Path

        if not isinstance(path, Path):
            return
        self._p0_filename.setText(path.name)
        try:
            size_bytes = path.stat().st_size
            if size_bytes >= 1_048_576:
                self._p0_filesize.setText(f"{size_bytes / 1_048_576:.1f} MB")
            else:
                self._p0_filesize.setText(f"{size_bytes / 1024:.1f} KB")
        except OSError:
            self._p0_filesize.setText("—")

    def update_file_info(self, header: Any) -> None:
        """Populate page 0 from *header*.

        Parameters
        ----------
        header : astropy.io.fits.Header | dict | None
            FITS header for the selected frame.
        """
        if header is None:
            for lbl in (
                self._p0_telescop, self._p0_instrume,
                self._p0_exptime, self._p0_gain, self._p0_object,
            ):
                lbl.setText("—")
                lbl.setStyleSheet(
                    f"color: {Colors.TEXT_DISABLED};"
                    f"font-family: {Typography.FONT_MONO};"
                    f"font-size: {Typography.SIZE_SM}px;"
                )
            return

        def _get(key: str) -> str:
            try:
                val = header.get(key)
                return str(val) if val is not None else "—"
            except Exception:
                return "—"

        def _set(lbl: QLabel, val: str) -> None:
            lbl.setText(val)
            if val == "—":
                lbl.setStyleSheet(
                    f"color: {Colors.TEXT_DISABLED};"
                    f"font-family: {Typography.FONT_MONO};"
                    f"font-size: {Typography.SIZE_SM}px;"
                )
            else:
                lbl.setStyleSheet(
                    f"color: {Colors.TEXT_PRIMARY};"
                    f"font-family: {Typography.FONT_MONO};"
                    f"font-size: {Typography.SIZE_SM}px;"
                )

        exptime = _get("EXPTIME")
        if exptime != "—":
            try:
                exptime = f"{float(exptime):.1f} s"
            except ValueError:
                pass

        _set(self._p0_telescop, _get("TELESCOP"))
        _set(self._p0_instrume, _get("INSTRUME"))
        _set(self._p0_exptime,  exptime)
        _set(self._p0_gain,     _get("GAIN"))
        _set(self._p0_object,   _get("OBJECT"))

    def update_wcs_info(self, wcs: Any) -> None:
        """Populate page 1 from a ``WCS`` object.

        Parameters
        ----------
        wcs : astropy.wcs.WCS | None
            Plate solution WCS, or ``None`` to reset to ``—``.
        """
        if wcs is None:
            for lbl in (self._p1_ra, self._p1_dec, self._p1_scale,
                        self._p1_rotation, self._p1_matches):
                lbl.setText("—")
            return

        try:
            # Use naxis attributes to get image centre
            nx = int(getattr(wcs, "pixel_shape", [None, None])[1] or 256)
            ny = int(getattr(wcs, "pixel_shape", [None, None])[0] or 256)
            sky = wcs.pixel_to_world(nx / 2, ny / 2)
            ra_str  = sky.ra.to_string(unit="hourangle", sep=":", precision=2, pad=True)
            dec_str = sky.dec.to_string(sep=":", precision=1, alwayssign=True)
            self._p1_ra.setText(ra_str)
            self._p1_dec.setText(dec_str)
        except Exception:
            self._p1_ra.setText("—")
            self._p1_dec.setText("—")

        try:
            from astropy.wcs.utils import proj_plane_pixel_scales
            import astropy.units as u
            scales = proj_plane_pixel_scales(wcs) * u.deg
            arcsec = scales[0].to(u.arcsec).value
            self._p1_scale.setText(f"{arcsec:.3f} \"/px")
        except Exception:
            self._p1_scale.setText("—")

        self._p1_rotation.setText("—")
        self._p1_matches.setText("—")

    def update_photometry_info(self, results: dict) -> None:
        """Populate page 2 from photometry configuration *results*.

        Parameters
        ----------
        results : dict
            Keys: ``target``, ``n_comp``, ``aperture``, ``ann_inner``,
            ``ann_outer``.
        """
        self._p2_target.setText(str(results.get("target", "—")))
        self._p2_comp_n.setText(str(results.get("n_comp", "—")))
        ap = results.get("aperture")
        self._p2_aperture.setText(f"{ap} px" if ap is not None else "—")
        ai = results.get("ann_inner")
        self._p2_ann_inner.setText(f"{ai} px" if ai is not None else "—")
        ao = results.get("ann_outer")
        self._p2_ann_outer.setText(f"{ao} px" if ao is not None else "—")

    def update_transit_info(self, params: dict) -> None:
        """Populate page 3 from transit fit *params*.

        Parameters
        ----------
        params : dict
            Keys: ``t0``, ``duration_hours``, ``depth``, ``rp_over_rs``.
        """
        def _fmt(val: Any, fmt: str = "", suffix: str = "") -> str:
            if val is None:
                return "—"
            try:
                return f"{val:{fmt}}{suffix}"
            except (ValueError, TypeError):
                return str(val)

        self._p3_t0.setText(_fmt(params.get("t0"), ".6f", " BJD"))
        self._p3_duration.setText(_fmt(params.get("duration_hours"), ".2f", " h"))
        depth = params.get("depth")
        if depth is not None:
            try:
                self._p3_depth.setText(f"{float(depth) * 100:.3f} %")
            except (TypeError, ValueError):
                self._p3_depth.setText("—")
        else:
            self._p3_depth.setText("—")
        self._p3_rprs.setText(_fmt(params.get("rp_over_rs"), ".4f"))
