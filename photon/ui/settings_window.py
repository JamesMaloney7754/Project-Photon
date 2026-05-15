"""Settings window — modal dialog for all Photon preferences."""

from __future__ import annotations

import logging
import subprocess

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from photon.core.settings_manager import get_settings_manager
from photon.ui.theme import Colors, Typography

logger = logging.getLogger(__name__)

_CAT_NAMES = ["General", "Plate Solving", "Photometry", "Catalogs", "API Keys", "Export"]
_CAT_COLORS = ["#3b82f6", "#7c3aed", "#f59e0b", "#10b981", "#f59e0b", "#6b7fa3"]


class _CategoryList(QWidget):
    """Painted list of category items with a violet left-bar on selected."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(160)
        self._selected = 0
        self._items = _CAT_NAMES
        self._dots  = _CAT_COLORS
        self._callback: object = None
        self.setStyleSheet("background-color: transparent;")

    def set_callback(self, fn: object) -> None:
        self._callback = fn  # type: ignore[assignment]

    def set_selected(self, index: int) -> None:
        self._selected = index
        self.update()

    def sizeHint(self) -> object:  # type: ignore[override]
        from PySide6.QtCore import QSize
        return QSize(160, 40 * len(self._items))

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        item_h = 40
        for i, (name, dot_color) in enumerate(zip(self._items, self._dots)):
            y = i * item_h
            if i == self._selected:
                painter.fillRect(0, y, self.width(), item_h, QColor(124, 58, 237, 25))
                painter.fillRect(0, y, 2, item_h, QColor(Colors.VIOLET))
            # Dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(dot_color))
            painter.drawEllipse(14, y + item_h // 2 - 3, 6, 6)
            # Label
            from PySide6.QtGui import QFont
            font = QFont("Inter")
            font.setPixelSize(Typography.SIZE_MD)
            font.setWeight(QFont.Weight(
                Typography.WEIGHT_SEMIBOLD if i == self._selected
                else Typography.WEIGHT_REGULAR
            ))
            painter.setFont(font)
            painter.setPen(
                QColor(Colors.TEXT_PRIMARY) if i == self._selected
                else QColor(Colors.TEXT_SECONDARY)
            )
            painter.drawText(28, y, self.width() - 28, item_h, 0, name)
        painter.end()

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        from PySide6.QtCore import Qt as _Qt
        y = event.pos().y()  # type: ignore[attr-defined]
        idx = y // 40
        if 0 <= idx < len(self._items):
            self._selected = idx
            self.update()
            if self._callback is not None:
                self._callback(idx)


def _row(label: str, widget: QWidget, suffix: str = "") -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;"
        f"background-color: transparent;"
    )
    lbl.setFixedWidth(120)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    if suffix:
        slbl = QLabel(suffix)
        slbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;"
            f"background-color: transparent;"
        )
        row.addWidget(slbl)
    return row


def _make_spinbox(lo: float, hi: float, val: float, step: float = 0.5, suffix: str = "") -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(lo, hi)
    sb.setSingleStep(step)
    sb.setValue(val)
    if suffix:
        sb.setSuffix(suffix)
    sb.setStyleSheet(
        f"color: {Colors.TEXT_GOLD}; background-color: {Colors.SURFACE_ALT};"
        f"font-family: {Typography.FONT_MONO}; border-radius: 4px;"
    )
    return sb


class SettingsWindow(QDialog):
    """Modal settings dialog with a category navigator and stacked pages.

    Parameters
    ----------
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Photon Settings")
        self.setFixedSize(720, 520)
        self.setModal(True)
        self.setStyleSheet(
            f"QDialog {{ background-color: {Colors.SURFACE}; }}"
            f"QWidget {{ background-color: transparent; }}"
            f"QGroupBox {{ color: {Colors.TEXT_SECONDARY};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: 6px;"
            f"  margin-top: 8px; padding: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; }}"
        )

        self._sm = get_settings_manager()
        self._build_ui()
        self._load_from_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left navigator ──────────────────────────────────────────────────────────────────
        left_bg = QWidget()
        left_bg.setFixedWidth(160)
        left_bg.setStyleSheet(
            f"background-color: {Colors.SURFACE_ALT};"
            f"border-right: 1px solid {Colors.BORDER};"
        )
        left_layout = QVBoxLayout(left_bg)
        left_layout.setContentsMargins(0, 12, 0, 0)
        left_layout.setSpacing(0)

        title_lbl = QLabel("Settings")
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Typography.SIZE_MD}px;"
            f"font-weight: {Typography.WEIGHT_BOLD}; padding: 0 14px 12px 14px;"
            f"background-color: transparent;"
        )
        left_layout.addWidget(title_lbl)

        self._cat_list = _CategoryList()
        self._cat_list.set_callback(self._on_category_changed)
        left_layout.addWidget(self._cat_list)
        left_layout.addStretch()
        root.addWidget(left_bg)

        # ── Right: stacked pages ──────────────────────────────────────────────────────
        right_wrapper = QWidget()
        right_layout = QVBoxLayout(right_wrapper)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {Colors.SURFACE};")
        self._stack.addWidget(self._build_page_general())
        self._stack.addWidget(self._build_page_platesolve())
        self._stack.addWidget(self._build_page_photometry())
        self._stack.addWidget(self._build_page_catalogs())
        self._stack.addWidget(self._build_page_apikeys())
        self._stack.addWidget(self._build_page_export())
        right_layout.addWidget(self._stack, 1)

        # ── Bottom button row ───────────────────────────────────────────────────────────
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background-color: {Colors.SURFACE_ALT};"
            f"border-top: 1px solid {Colors.BORDER};"
        )
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(12, 8, 12, 8)

        restore_btn = QPushButton("Restore Defaults")
        restore_btn.setFlat(True)
        restore_btn.clicked.connect(self._restore_defaults)
        btn_layout.addWidget(restore_btn)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFlat(True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(save_btn)

        right_layout.addWidget(btn_bar)
        root.addWidget(right_wrapper, 1)

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------

    def _scroll_wrap(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {Colors.SURFACE}; border: none; }}"
        )
        return scroll

    def _page_container(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        w.setStyleSheet(f"background-color: {Colors.SURFACE};")
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)
        hdr = QLabel(title)
        hdr.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Typography.SIZE_LG}px;"
            f"font-weight: {Typography.WEIGHT_SEMIBOLD}; background-color: transparent;"
        )
        v.addWidget(hdr)
        return w, v

    def _build_page_general(self) -> QScrollArea:
        w, v = self._page_container("General")
        self._confirm_quit_cb = QCheckBox("Confirm before quitting")
        self._confirm_quit_cb.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; background-color: transparent;"
        )
        v.addWidget(self._confirm_quit_cb)

        v.addWidget(QLabel("Recent Directories:"))
        self._recent_list = QListWidget()
        self._recent_list.setFixedHeight(120)
        self._recent_list.setStyleSheet(
            f"background-color: {Colors.SURFACE_ALT}; border: 1px solid {Colors.BORDER};"
            f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;"
        )
        v.addWidget(self._recent_list)

        clear_btn = QPushButton("Clear Recent")
        clear_btn.setFlat(True)
        clear_btn.clicked.connect(self._clear_recent)
        v.addWidget(clear_btn, 0, Qt.AlignmentFlag.AlignLeft)
        v.addStretch()
        return self._scroll_wrap(w)

    def _build_page_platesolve(self) -> QScrollArea:
        w, v = self._page_container("Plate Solving")

        # ── Backend selection (ASTAP first) ───────────────────────────────────────
        self._radio_astap  = QRadioButton("ASTAP (recommended for Windows)")
        self._radio_local  = QRadioButton("Local astrometry.net (ANSVR)")
        self._radio_cloud  = QRadioButton("Astrometry.net Cloud")
        for rb in (self._radio_astap, self._radio_local, self._radio_cloud):
            rb.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background-color: transparent;")
        v.addWidget(self._radio_astap)
        v.addWidget(self._radio_local)
        v.addWidget(self._radio_cloud)

        # ── ASTAP group ───────────────────────────────────────────────────────────────────
        self._astap_group = QGroupBox("ASTAP Solver")
        ag = QVBoxLayout(self._astap_group)

        self._astap_binary_le = QLineEdit()
        self._astap_binary_le.setPlaceholderText(r"C:\Program Files\astap\astap.exe")
        astap_browse = QPushButton("Browse…")
        astap_browse.setFlat(True)
        astap_browse.clicked.connect(
            lambda: self._browse_file(self._astap_binary_le)
        )
        ar1 = QHBoxLayout()
        ar1.addWidget(QLabel("astap.exe path:"))
        ar1.addWidget(self._astap_binary_le, 1)
        ar1.addWidget(astap_browse)
        ag.addLayout(ar1)

        self._astap_radius_sb = QDoubleSpinBox()
        self._astap_radius_sb.setRange(1.0, 180.0)
        self._astap_radius_sb.setSingleStep(5.0)
        self._astap_radius_sb.setValue(30.0)
        self._astap_radius_sb.setSuffix(" °")
        self._astap_radius_sb.setStyleSheet(
            f"color: {Colors.TEXT_GOLD}; background-color: {Colors.SURFACE_ALT};"
            f"font-family: {Typography.FONT_MONO}; border-radius: 4px;"
        )
        ag.addLayout(_row("Search radius:", self._astap_radius_sb))

        self._astap_downsample_sb = QSpinBox()
        self._astap_downsample_sb.setRange(0, 4)
        self._astap_downsample_sb.setValue(0)
        self._astap_downsample_sb.setToolTip(
            "0 = automatic, higher = faster but less accurate"
        )
        self._astap_downsample_sb.setStyleSheet(
            f"color: {Colors.TEXT_GOLD}; background-color: {Colors.SURFACE_ALT};"
        )
        ag.addLayout(_row("Downsample:", self._astap_downsample_sb))

        astap_test_row = QHBoxLayout()
        self._astap_test_btn = QPushButton("Test ASTAP")
        self._astap_test_btn.setFlat(True)
        self._astap_test_btn.clicked.connect(self._test_astap_solver)
        astap_test_row.addWidget(self._astap_test_btn)
        self._astap_autodetect_btn = QPushButton("Auto-detect")
        self._astap_autodetect_btn.setFlat(True)
        self._astap_autodetect_btn.clicked.connect(self._autodetect_astap)
        astap_test_row.addWidget(self._astap_autodetect_btn)
        self._astap_test_lbl = QLabel()
        self._astap_test_lbl.setStyleSheet("background-color: transparent;")
        self._astap_test_lbl.setVisible(False)
        astap_test_row.addWidget(self._astap_test_lbl)
        astap_test_row.addStretch()
        ag.addLayout(astap_test_row)
        v.addWidget(self._astap_group)

        # ── Local (ANSVR) group ───────────────────────────────────────────────────
        self._local_group = QGroupBox("Local astrometry.net (ANSVR)")
        lg = QVBoxLayout(self._local_group)
        self._local_binary_le = QLineEdit()
        self._local_binary_le.setPlaceholderText("/usr/local/bin/solve-field")
        binary_browse = QPushButton("Browse…")
        binary_browse.setFlat(True)
        binary_browse.clicked.connect(
            lambda: self._browse_file(self._local_binary_le)
        )
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("solve-field path:"))
        r1.addWidget(self._local_binary_le, 1)
        r1.addWidget(binary_browse)
        lg.addLayout(r1)

        self._index_dir_le = QLineEdit()
        self._index_dir_le.setPlaceholderText("/usr/share/astrometry")
        index_browse = QPushButton("Browse…")
        index_browse.setFlat(True)
        index_browse.clicked.connect(
            lambda: self._browse_dir(self._index_dir_le)
        )
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Index files dir:"))
        r2.addWidget(self._index_dir_le, 1)
        r2.addWidget(index_browse)
        lg.addLayout(r2)

        test_row = QHBoxLayout()
        self._test_btn = QPushButton("Test Installation")
        self._test_btn.setFlat(True)
        self._test_btn.clicked.connect(self._test_local_solver)
        test_row.addWidget(self._test_btn)
        self._test_result_lbl = QLabel()
        self._test_result_lbl.setStyleSheet("background-color: transparent;")
        self._test_result_lbl.setVisible(False)
        test_row.addWidget(self._test_result_lbl)
        test_row.addStretch()
        lg.addLayout(test_row)
        v.addWidget(self._local_group)

        # ── Cloud group ─────────────────────────────────────────────────────────────────
        self._cloud_group = QGroupBox("Astrometry.net Cloud")
        cg = QVBoxLayout(self._cloud_group)
        self._api_key_le = QLineEdit()
        self._api_key_le.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_le.setPlaceholderText("nova.astrometry.net API key")
        show_btn = QPushButton("Show")
        show_btn.setFlat(True)
        show_btn.setFixedWidth(44)
        show_btn.clicked.connect(self._toggle_api_key_visibility)
        ak_row = QHBoxLayout()
        ak_row.addWidget(QLabel("API Key:"))
        ak_row.addWidget(self._api_key_le, 1)
        ak_row.addWidget(show_btn)
        cg.addLayout(ak_row)

        link_lbl = QLabel(
            '<a href="https://nova.astrometry.net" style="color:#7c3aed;">'
            "Get a free key at nova.astrometry.net</a>"
        )
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setStyleSheet(
            f"font-size: {Typography.SIZE_SM}px; background-color: transparent;"
        )
        cg.addWidget(link_lbl)
        v.addWidget(self._cloud_group)

        # ── Scale / timeout (visible for local + cloud only) ──────────────────────
        self._scale_timeout_group = QGroupBox("Search parameters")
        stg = QVBoxLayout(self._scale_timeout_group)
        self._scale_low_sb  = _make_spinbox(0.01, 100.0, 0.1,  0.1, " arcsec/px")
        self._scale_high_sb = _make_spinbox(0.01, 100.0, 10.0, 0.5, " arcsec/px")
        self._timeout_sb = QSpinBox()
        self._timeout_sb.setRange(10, 600)
        self._timeout_sb.setSuffix(" s")
        self._timeout_sb.setStyleSheet(
            f"color: {Colors.TEXT_GOLD}; background-color: {Colors.SURFACE_ALT};"
        )
        stg.addLayout(_row("Min scale:", self._scale_low_sb))
        stg.addLayout(_row("Max scale:", self._scale_high_sb))
        stg.addLayout(_row("Timeout:",   self._timeout_sb))
        v.addWidget(self._scale_timeout_group)
        v.addStretch()

        self._radio_astap.toggled.connect(self._update_solver_visibility)
        self._radio_local.toggled.connect(self._update_solver_visibility)
        self._radio_cloud.toggled.connect(self._update_solver_visibility)
        return self._scroll_wrap(w)

    def _build_page_photometry(self) -> QScrollArea:
        w, v = self._page_container("Photometry")

        self._ap_r_sb  = _make_spinbox(1.0, 50.0, 8.0,  0.5, " px")
        self._an_in_sb = _make_spinbox(1.0, 50.0, 12.0, 0.5, " px")
        self._an_out_sb = _make_spinbox(1.0, 50.0, 20.0, 0.5, " px")
        self._fwhm_sb  = _make_spinbox(1.0, 20.0, 3.0,  0.5, " px")
        self._thresh_sb = _make_spinbox(1.0, 20.0, 5.0, 0.5, " σ")
        self._max_comp_sb = QSpinBox()
        self._max_comp_sb.setRange(3, 50)
        self._max_comp_sb.setValue(10)
        self._max_comp_sb.setStyleSheet(
            f"color: {Colors.TEXT_GOLD}; background-color: {Colors.SURFACE_ALT};"
        )
        self._min_snr_sb = _make_spinbox(1.0, 500.0, 50.0, 5.0, " SNR")

        for label, sb in [
            ("Aperture radius", self._ap_r_sb),
            ("Annulus inner",   self._an_in_sb),
            ("Annulus outer",   self._an_out_sb),
            ("Detection FWHM",  self._fwhm_sb),
            ("Det. threshold",  self._thresh_sb),
            ("Max comp. stars", self._max_comp_sb),
            ("Min comp. SNR",   self._min_snr_sb),
        ]:
            v.addLayout(_row(label, sb))

        # Aperture preview
        from photon.ui.photometry_panel import AperturePreviewWidget
        self._ap_preview = AperturePreviewWidget()
        v.addWidget(self._ap_preview, 0, Qt.AlignmentFlag.AlignHCenter)
        for sb in (self._ap_r_sb, self._an_in_sb, self._an_out_sb):
            sb.valueChanged.connect(self._update_aperture_preview)

        v.addStretch()
        return self._scroll_wrap(w)

    def _build_page_catalogs(self) -> QScrollArea:
        w, v = self._page_container("Catalogs")
        self._simbad_cb = QCheckBox("Query SIMBAD")
        self._gaia_cb   = QCheckBox("Query Gaia DR3")
        self._vsx_cb    = QCheckBox("Query VSX (variable stars)")
        for cb in (self._simbad_cb, self._gaia_cb, self._vsx_cb):
            cb.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; background-color: transparent;"
            )
            v.addWidget(cb)

        self._search_radius_sb = _make_spinbox(1.0, 60.0, 15.0, 1.0, " arcmin")
        v.addLayout(_row("Search radius:", self._search_radius_sb))

        info_lbl = QLabel("Catalogs are queried after a successful plate solution.")
        info_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;"
            f"font-style: italic; background-color: transparent;"
        )
        info_lbl.setWordWrap(True)
        v.addWidget(info_lbl)
        v.addStretch()
        return self._scroll_wrap(w)

    def _build_page_apikeys(self) -> QScrollArea:
        w, v = self._page_container("API Keys")

        # Astrometry.net — shares value with plate solving page
        self._api_key_le2 = QLineEdit()
        self._api_key_le2.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_le2.setPlaceholderText("nova.astrometry.net API key")
        v.addLayout(_row("Astrometry.net:", self._api_key_le2))

        # Sync with main api_key field
        self._api_key_le2.textChanged.connect(
            lambda t: self._api_key_le.setText(t)
        )

        for name in ("AAVSO WebObs", "Exoplanet Transit DB"):
            disabled_le = QLineEdit()
            disabled_le.setEnabled(False)
            disabled_le.setPlaceholderText("Coming in a future release")
            v.addLayout(_row(name + ":", disabled_le))

        v.addStretch()
        return self._scroll_wrap(w)

    def _build_page_export(self) -> QScrollArea:
        w, v = self._page_container("Export")

        self._export_csv_radio  = QRadioButton("CSV")
        self._export_fits_radio = QRadioButton("FITS")
        for rb in (self._export_csv_radio, self._export_fits_radio):
            rb.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; background-color: transparent;"
            )
        fmt_row = QHBoxLayout()
        fmt_lbl = QLabel("Default format:")
        fmt_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; background-color: transparent;"
        )
        fmt_row.addWidget(fmt_lbl)
        fmt_row.addWidget(self._export_csv_radio)
        fmt_row.addWidget(self._export_fits_radio)
        fmt_row.addStretch()
        v.addLayout(fmt_row)

        self._include_headers_cb = QCheckBox("Include column headers in CSV")
        self._include_headers_cb.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; background-color: transparent;"
        )
        v.addWidget(self._include_headers_cb)
        v.addStretch()
        return self._scroll_wrap(w)

    # ------------------------------------------------------------------
    # Settings I/O
    # ------------------------------------------------------------------

    def _load_from_settings(self) -> None:
        sm = self._sm

        # General
        self._confirm_quit_cb.setChecked(sm.get("general/confirm_on_quit"))
        self._recent_list.clear()
        for p in sm.get_recent_directories():
            self._recent_list.addItem(str(p))

        # Plate solving
        backend = sm.get("platesolve/backend")
        self._radio_astap.setChecked(backend == "astap")
        self._radio_local.setChecked(backend == "local")
        self._radio_cloud.setChecked(backend == "astrometry_net")
        self._astap_binary_le.setText(sm.get("platesolve/astap_binary_path"))
        self._astap_radius_sb.setValue(float(sm.get("platesolve/astap_search_radius")))
        self._astap_downsample_sb.setValue(int(sm.get("platesolve/astap_downsample")))
        self._local_binary_le.setText(sm.get("platesolve/local_binary_path"))
        self._index_dir_le.setText(sm.get("platesolve/index_dir"))
        self._api_key_le.setText(sm.get("platesolve/astrometry_api_key"))
        self._api_key_le2.setText(sm.get("platesolve/astrometry_api_key"))
        self._scale_low_sb.setValue(sm.get("platesolve/scale_low"))
        self._scale_high_sb.setValue(sm.get("platesolve/scale_high"))
        self._timeout_sb.setValue(sm.get("platesolve/timeout_seconds"))
        self._update_solver_visibility()

        # Photometry
        self._ap_r_sb.setValue(sm.get("photometry/aperture_radius_px"))
        self._an_in_sb.setValue(sm.get("photometry/annulus_inner_px"))
        self._an_out_sb.setValue(sm.get("photometry/annulus_outer_px"))
        self._fwhm_sb.setValue(sm.get("photometry/detection_fwhm"))
        self._thresh_sb.setValue(sm.get("photometry/detection_threshold_sigma"))
        self._max_comp_sb.setValue(sm.get("photometry/max_comparison_stars"))
        self._min_snr_sb.setValue(sm.get("photometry/min_comparison_snr"))
        self._update_aperture_preview()

        # Catalogs
        self._simbad_cb.setChecked(sm.get("catalog/use_simbad"))
        self._gaia_cb.setChecked(sm.get("catalog/use_gaia"))
        self._vsx_cb.setChecked(sm.get("catalog/use_vsx"))
        self._search_radius_sb.setValue(sm.get("catalog/search_radius_arcmin"))

        # Export
        fmt = sm.get("export/default_format")
        self._export_csv_radio.setChecked(fmt == "csv")
        self._export_fits_radio.setChecked(fmt != "csv")
        self._include_headers_cb.setChecked(sm.get("export/include_headers"))

    def _save_settings(self) -> None:
        sm = self._sm

        sm.set("general/confirm_on_quit", self._confirm_quit_cb.isChecked())
        if self._radio_astap.isChecked():
            backend = "astap"
        elif self._radio_local.isChecked():
            backend = "local"
        else:
            backend = "astrometry_net"
        sm.set("platesolve/backend", backend)
        sm.set("platesolve/astap_binary_path", self._astap_binary_le.text())
        sm.set("platesolve/astap_search_radius", self._astap_radius_sb.value())
        sm.set("platesolve/astap_downsample", self._astap_downsample_sb.value())
        sm.set("platesolve/local_binary_path", self._local_binary_le.text())
        sm.set("platesolve/index_dir", self._index_dir_le.text())
        sm.set("platesolve/astrometry_api_key", self._api_key_le.text())
        sm.set("platesolve/scale_low", self._scale_low_sb.value())
        sm.set("platesolve/scale_high", self._scale_high_sb.value())
        sm.set("platesolve/timeout_seconds", self._timeout_sb.value())

        sm.set("photometry/aperture_radius_px", self._ap_r_sb.value())
        sm.set("photometry/annulus_inner_px", self._an_in_sb.value())
        sm.set("photometry/annulus_outer_px", self._an_out_sb.value())
        sm.set("photometry/detection_fwhm", self._fwhm_sb.value())
        sm.set("photometry/detection_threshold_sigma", self._thresh_sb.value())
        sm.set("photometry/max_comparison_stars", self._max_comp_sb.value())
        sm.set("photometry/min_comparison_snr", self._min_snr_sb.value())

        sm.set("catalog/use_simbad", self._simbad_cb.isChecked())
        sm.set("catalog/use_gaia",   self._gaia_cb.isChecked())
        sm.set("catalog/use_vsx",    self._vsx_cb.isChecked())
        sm.set("catalog/search_radius_arcmin", self._search_radius_sb.value())

        sm.set("export/default_format", "csv" if self._export_csv_radio.isChecked() else "fits")
        sm.set("export/include_headers", self._include_headers_cb.isChecked())

        logger.info("Settings saved.")

    def _save_and_close(self) -> None:
        self._save_settings()
        self.accept()

    def _restore_defaults(self) -> None:
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "Reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._sm.reset_to_defaults()
            self._load_from_settings()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_category_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    def _update_solver_visibility(self) -> None:
        astap  = self._radio_astap.isChecked()
        local  = self._radio_local.isChecked()
        cloud  = self._radio_cloud.isChecked()
        self._astap_group.setVisible(astap)
        self._local_group.setVisible(local)
        self._cloud_group.setVisible(cloud)
        # Scale/timeout only relevant for local (ANSVR) and cloud backends
        self._scale_timeout_group.setVisible(local or cloud)

    def _update_aperture_preview(self) -> None:
        self._ap_preview.set_params(
            self._ap_r_sb.value(),
            self._an_in_sb.value(),
            self._an_out_sb.value(),
        )

    def _browse_file(self, line_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Binary", "")
        if path:
            line_edit.setText(path)

    def _browse_dir(self, line_edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Directory", "")
        if path:
            line_edit.setText(path)

    def _toggle_api_key_visibility(self) -> None:
        if self._api_key_le.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_le.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._api_key_le.setEchoMode(QLineEdit.EchoMode.Password)

    def _clear_recent(self) -> None:
        self._sm.set("general/recent_directories", [])
        self._recent_list.clear()

    def _test_astap_solver(self) -> None:
        import sys
        import shutil
        from photon.core.plate_solver import ASTAPSolver
        binary = self._astap_binary_le.text().strip() or "astap"
        # Check existence without running the binary (ASTAP opens GUI if invoked bare)
        found, _ = ASTAPSolver.detect_installation(binary)
        if not found:
            self._astap_test_lbl.setText("✗ Not found")
            self._astap_test_lbl.setStyleSheet(
                f"color: {Colors.DANGER}; background-color: transparent;"
            )
            self._astap_test_lbl.setVisible(True)
            return
        # Binary exists — try running it with CREATE_NO_WINDOW to get version
        resolved = shutil.which(binary) or binary
        try:
            kwargs: dict = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            result = subprocess.run(
                [resolved, "-version"],
                capture_output=True, text=True, timeout=3, **kwargs
            )
            version = (result.stdout or result.stderr or "").strip().splitlines()[0] if (result.stdout or result.stderr) else ""
            label = f"✓ {version}" if version else "✓ Found"
            self._astap_test_lbl.setText(label)
            self._astap_test_lbl.setStyleSheet(
                f"color: {Colors.SUCCESS}; background-color: transparent;"
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            self._astap_test_lbl.setText("✓ Found (could not query version)")
            self._astap_test_lbl.setStyleSheet(
                f"color: {Colors.SUCCESS}; background-color: transparent;"
            )
        self._astap_test_lbl.setVisible(True)

    def _autodetect_astap(self) -> None:
        """Search common install locations for ASTAP and populate the path field."""
        import shutil
        from photon.core.plate_solver import ASTAPSolver
        _candidates = [
            r"C:\Program Files\astap\astap.exe",
            r"C:\Program Files (x86)\astap\astap.exe",
            "/usr/bin/astap",
            "/usr/local/bin/astap",
            "/opt/homebrew/bin/astap",
        ]
        # Check PATH first
        via_which = shutil.which("astap")
        if via_which:
            self._astap_binary_le.setText(via_which)
            self._astap_test_lbl.setText("✓ Auto-detected")
            self._astap_test_lbl.setStyleSheet(
                f"color: {Colors.SUCCESS}; background-color: transparent;"
            )
            self._astap_test_lbl.setVisible(True)
            return
        for candidate in _candidates:
            found, _ = ASTAPSolver.detect_installation(candidate)
            if found:
                self._astap_binary_le.setText(candidate)
                self._astap_test_lbl.setText("✓ Auto-detected")
                self._astap_test_lbl.setStyleSheet(
                    f"color: {Colors.SUCCESS}; background-color: transparent;"
                )
                self._astap_test_lbl.setVisible(True)
                return
        self._astap_test_lbl.setText("✗ Not found")
        self._astap_test_lbl.setStyleSheet(
            f"color: {Colors.DANGER}; background-color: transparent;"
        )
        self._astap_test_lbl.setVisible(True)

    def _test_local_solver(self) -> None:
        binary = self._local_binary_le.text().strip() or "solve-field"
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                self._test_result_lbl.setText("✓ Found")
                self._test_result_lbl.setStyleSheet(
                    f"color: {Colors.SUCCESS}; background-color: transparent;"
                )
            else:
                self._test_result_lbl.setText("✗ Error")
                self._test_result_lbl.setStyleSheet(
                    f"color: {Colors.DANGER}; background-color: transparent;"
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._test_result_lbl.setText("✗ Not found")
            self._test_result_lbl.setStyleSheet(
                f"color: {Colors.DANGER}; background-color: transparent;"
            )
        self._test_result_lbl.setVisible(True)
