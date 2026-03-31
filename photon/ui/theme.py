"""Deep Field design system — single source of truth for all UI tokens.

Every color, font size, and spacing value used anywhere in ``photon/ui/`` must
reference a constant from this module.  No hardcoded hex values are permitted
outside of this file.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


class Colors:
    """Color palette for the Deep Field theme."""

    # Backgrounds — deep space gradient system
    BASE_CENTER     = "#0a0f1a"   # Deep navy — radial gradient center
    BASE_EDGE       = "#060810"   # Near black — radial gradient edge

    # Panel surfaces — glass effect
    GLASS_BG        = "rgba(255, 255, 255, 12)"
    GLASS_BORDER_LT = "rgba(255, 255, 255, 30)"
    GLASS_BORDER_DK = "rgba(255, 255, 255, 6)"
    GLASS_SURFACE   = "#111827"

    SURFACE         = "#111827"
    SURFACE_ALT     = "#1a2235"
    SURFACE_RAISED  = "#1f2d45"
    BORDER          = "#1e2d45"
    BORDER_SUBTLE   = "#152032"

    # Accents — violet (actions / navigation)
    VIOLET          = "#7c3aed"
    VIOLET_BRIGHT   = "#8b5cf6"
    VIOLET_GLOW     = "rgba(124, 58, 237, 40)"
    VIOLET_DIM      = "rgba(124, 58, 237, 20)"

    BLUE            = "#3b82f6"
    BLUE_GLOW       = "rgba(59, 130, 246, 30)"

    # Science data accent — gold/amber for measurements and values
    GOLD            = "#f59e0b"
    GOLD_DIM        = "rgba(245, 158, 11, 20)"

    SUCCESS         = "#10b981"
    SUCCESS_GLOW    = "rgba(16, 185, 129, 30)"
    WARNING         = "#f59e0b"
    DANGER          = "#ef4444"

    # Text
    TEXT_PRIMARY    = "#f0f4ff"   # Slightly blue-tinted white
    TEXT_SECONDARY  = "#6b7fa3"   # Muted blue-grey
    TEXT_DISABLED   = "#2d3f5c"
    TEXT_GOLD       = "#fbbf24"   # Science values
    TEXT_ACCENT     = "#a78bfa"   # Light violet highlights

    # Canvas
    CANVAS_BG       = "#04060d"

    # Legacy aliases — keep old callers working
    ACCENT_PRIMARY   = VIOLET
    ACCENT_SECONDARY = BLUE
    ACCENT_SUCCESS   = SUCCESS
    ACCENT_WARNING   = WARNING
    ACCENT_DANGER    = DANGER
    BASE             = BASE_CENTER
    BORDER_FOCUS     = "#388bfd"


class Typography:
    """Typography scale for the Deep Field theme."""

    FONT_UI      = "Inter, 'Segoe UI Variable', 'Segoe UI', sans-serif"
    FONT_MONO    = "'JetBrains Mono', 'Cascadia Code', Consolas, monospace"
    FONT_DISPLAY = "Inter, 'Segoe UI Variable Display', 'Segoe UI', sans-serif"

    WEIGHT_LIGHT    = 300
    WEIGHT_REGULAR  = 400
    WEIGHT_MEDIUM   = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD     = 700

    SIZE_XS   = 9
    SIZE_SM   = 10
    SIZE_BASE = 11
    SIZE_MD   = 12
    SIZE_LG   = 14
    SIZE_XL   = 17
    SIZE_2XL  = 22


def build_stylesheet() -> str:
    """Return the complete Qt stylesheet for the Deep Field theme.

    Returns
    -------
    str
        A Qt-compatible CSS stylesheet string.
    """
    C = Colors
    T = Typography
    return f"""

/* ── Base ──────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {C.BASE_CENTER};
    color: {C.TEXT_PRIMARY};
    font-family: Inter, "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: {T.SIZE_BASE}px;
    border: none;
}}

/* ── Glass panel ────────────────────────────────────────────────────────── */
QWidget#glass_panel {{
    background-color: {C.GLASS_SURFACE};
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 12px;
}}

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter {{
    background-color: transparent;
}}
QSplitter::handle {{
    background-color: {C.BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:hover {{
    background-color: {C.VIOLET};
}}

/* ── List Widget ────────────────────────────────────────────────────────── */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 4px 0;
}}
QListWidget::item {{
    padding: 8px 12px;
    border-radius: 6px;
    color: {C.TEXT_PRIMARY};
    border-left: 2px solid transparent;
}}
QListWidget::item:hover {{
    background-color: rgba(255, 255, 255, 10);
}}
QListWidget::item:selected {{
    background-color: {C.VIOLET_DIM};
    border-left: 2px solid {C.VIOLET};
}}
QListWidget::item:focus {{
    outline: none;
}}

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {{
    color: {C.TEXT_PRIMARY};
    background-color: transparent;
}}

/* ── Push Buttons ───────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {C.VIOLET};
    color: {C.TEXT_PRIMARY};
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: {T.SIZE_MD}px;
    font-weight: {T.WEIGHT_MEDIUM};
}}
QPushButton:hover {{
    background-color: {C.VIOLET_BRIGHT};
    border-top: 1px solid rgba(255, 255, 255, 50);
}}
QPushButton:pressed {{
    background-color: #6d28d9;
}}
QPushButton:disabled {{
    background-color: {C.SURFACE_RAISED};
    color: {C.TEXT_DISABLED};
}}
QPushButton[flat="true"] {{
    background-color: transparent;
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    color: {C.TEXT_PRIMARY};
}}
QPushButton[flat="true"]:hover {{
    background-color: rgba(255, 255, 255, 13);
    border-color: {C.VIOLET};
}}
QPushButton[flat="true"]:pressed {{
    background-color: rgba(124, 58, 237, 20);
}}

/* ── Tool Buttons ───────────────────────────────────────────────────────── */
QToolButton {{
    background-color: transparent;
    border: none;
    color: {C.TEXT_PRIMARY};
    padding: 4px 8px;
    border-radius: 6px;
}}
QToolButton:hover {{
    background-color: rgba(255, 255, 255, 10);
}}
QToolButton::menu-indicator {{
    image: none;
}}

/* ── Menus ──────────────────────────────────────────────────────────────── */
QMenu {{
    background-color: {C.SURFACE_RAISED};
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 10px;
    padding: 6px 0;
    color: {C.TEXT_PRIMARY};
}}
QMenu::item {{
    padding: 7px 24px 7px 14px;
    border-radius: 6px;
    margin: 1px 6px;
}}
QMenu::item:selected {{
    background-color: {C.VIOLET};
    color: {C.TEXT_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background-color: {C.BORDER};
    margin: 4px 10px;
}}

/* ── Scroll Bars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 4px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: rgba(255, 255, 255, 30);
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {C.VIOLET};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 4px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: rgba(255, 255, 255, 30);
    border-radius: 2px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {C.VIOLET};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Sliders ────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 3px;
    background-color: {C.BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {C.VIOLET};
    border: 2px solid {C.VIOLET_BRIGHT};
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -6px 0;
}}
QSlider::handle:horizontal:hover {{
    background-color: {C.VIOLET_BRIGHT};
    border: 2px solid white;
}}
QSlider::sub-page:horizontal {{
    background-color: {C.VIOLET};
    border-radius: 2px;
}}

/* ── Tooltips ───────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {C.SURFACE_RAISED};
    color: {C.TEXT_PRIMARY};
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {T.SIZE_SM}px;
}}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {C.BORDER};
    border: none;
    border-radius: 2px;
    height: 3px;
}}
QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C.VIOLET}, stop:1 {C.BLUE});
    border-radius: 2px;
}}

/* ── Line Edit ──────────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {C.SURFACE};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    selection-background-color: {C.VIOLET};
}}
QLineEdit:focus {{
    border-color: {C.VIOLET};
}}
QLineEdit:disabled {{
    color: {C.TEXT_DISABLED};
}}

/* ── Scroll Area ────────────────────────────────────────────────────────── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ── Frame / Separator ──────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="HLine"] {{
    color: {C.BORDER};
    background-color: {C.BORDER};
    border: none;
    max-height: 1px;
}}

"""


def apply_theme(app: QApplication) -> None:
    """Apply the Deep Field theme to *app*.

    Parameters
    ----------
    app : QApplication
        The running application instance.
    """
    app.setStyleSheet(build_stylesheet())
    font = QFont("Inter")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPixelSize(Typography.SIZE_BASE)
    app.setFont(font)
