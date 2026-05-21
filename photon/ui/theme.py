"""Cockpit design system — single source of truth for all UI tokens.

Every color, font size, and spacing value used anywhere in ``photon/ui/`` must
reference a constant from this module.  No hardcoded hex values are permitted
outside of this file.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


class Colors:
    """Color palette for the Cockpit theme (deep navy + red accent)."""

    # ── Backgrounds ────────────────────────────────────────────────────────
    BACKGROUND    = "#080a13"   # body fill
    BG_PANEL      = "#11131f"   # panel surfaces
    BG_PANEL_2    = "#161826"   # hover / raised surfaces
    BG_TITLEBAR   = "#0a0c16"   # top bar, foot bar

    # ── Borders ────────────────────────────────────────────────────────────
    BORDER        = "#1e2238"
    BORDER_2      = "#272b44"

    # ── Foreground / text ──────────────────────────────────────────────────
    FG            = "#e7ecf5"   # primary text
    FG_2          = "#a5b4cb"   # secondary text
    FG_3          = "#7d8ba8"   # muted labels
    FG_4          = "#525a78"   # disabled / very muted

    # ── Accents ────────────────────────────────────────────────────────────
    ACCENT        = "#dc2626"   # red  — actions, active states, borders
    ACCENT_DIM    = "#991b1b"   # darker red  — pressed states
    AMBER         = "#F59E0B"   # gold — data values, measurements, target dot

    # ── Semantic ───────────────────────────────────────────────────────────
    SUCCESS       = "#10b981"
    DANGER        = "#ef4444"
    WARNING       = "#F59E0B"

    # ── Canvas ─────────────────────────────────────────────────────────────
    CANVAS_BG     = "#04060d"

    # ── Legacy aliases — keep existing callers working ─────────────────────
    VIOLET          = "#dc2626"
    VIOLET_BRIGHT   = "#ef4444"
    VIOLET_GLOW     = "rgba(220, 38, 38, 40)"
    VIOLET_DIM      = "rgba(220, 38, 38, 20)"
    BLUE            = "#b91c1c"
    BLUE_GLOW       = "rgba(185, 28, 28, 30)"
    GOLD            = "#F59E0B"
    GOLD_DIM        = "rgba(245, 158, 11, 20)"
    TEXT_PRIMARY    = "#e7ecf5"
    TEXT_SECONDARY  = "#7d8ba8"
    TEXT_DISABLED   = "#525a78"
    TEXT_GOLD       = "#F59E0B"
    TEXT_ACCENT     = "#f87171"
    SURFACE         = "#11131f"
    SURFACE_ALT     = "#161826"
    SURFACE_RAISED  = "#161826"
    GLASS_SURFACE   = "#11131f"
    GLASS_BG        = "rgba(255, 255, 255, 12)"
    GLASS_BORDER_LT = "rgba(255, 255, 255, 30)"
    GLASS_BORDER_DK = "rgba(255, 255, 255, 6)"
    BASE_CENTER     = "#080a13"
    BASE_EDGE       = "#060810"
    BASE            = "#080a13"
    BORDER_FOCUS    = "#dc2626"
    BORDER_SUBTLE   = "#1e2238"
    ACCENT_PRIMARY   = "#dc2626"
    ACCENT_SECONDARY = "#b91c1c"
    ACCENT_SUCCESS   = "#10b981"
    ACCENT_WARNING   = "#F59E0B"
    ACCENT_DANGER    = "#ef4444"
    SUCCESS_GLOW     = "rgba(16, 185, 129, 30)"


class Typography:
    """Typography scale for the Cockpit theme."""

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
    """Return the complete Qt stylesheet for the Cockpit theme."""
    C = Colors
    T = Typography
    return f"""

/* ── Base ─────────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {C.BACKGROUND};
    color: {C.FG};
    font-family: Inter, "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: {T.SIZE_BASE}px;
    border: none;
}}

/* ── Glass / cockpit pane ─────────────────────────────────────────── */
QWidget#glass_panel, QWidget#cockpit_pane {{
    background-color: {C.BG_PANEL};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
}}

/* ── Splitter ─────────────────────────────────────────────────────── */
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
    background-color: {C.ACCENT};
}}

/* ── List Widget ──────────────────────────────────────────────────── */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 2px 0;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: {C.FG};
    border-left: 2px solid transparent;
}}
QListWidget::item:hover {{
    background-color: rgba(255, 255, 255, 6);
}}
QListWidget::item:selected {{
    background-color: rgba(220, 38, 38, 15);
    border-left: 2px solid {C.ACCENT};
}}
QListWidget::item:focus {{
    outline: none;
}}

/* ── Labels ───────────────────────────────────────────────────────── */
QLabel {{
    color: {C.FG};
    background-color: transparent;
}}

/* ── Push Buttons ─────────────────────────────────────────────────── */
QPushButton {{
    background-color: {C.ACCENT};
    color: {C.FG};
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: {T.SIZE_MD}px;
    font-weight: {T.WEIGHT_MEDIUM};
}}
QPushButton:hover {{
    background-color: {C.DANGER};
}}
QPushButton:pressed {{
    background-color: {C.ACCENT_DIM};
}}
QPushButton:disabled {{
    background-color: {C.BG_PANEL_2};
    color: {C.TEXT_DISABLED};
}}
QPushButton[flat="true"] {{
    background-color: transparent;
    border: 1px solid {C.BORDER_2};
    border-radius: 6px;
    color: {C.FG_2};
}}
QPushButton[flat="true"]:hover {{
    background-color: rgba(255, 255, 255, 6);
    border-color: {C.ACCENT};
    color: {C.FG};
}}
QPushButton[flat="true"]:pressed {{
    background-color: rgba(220, 38, 38, 15);
}}

/* ── Tool Buttons ─────────────────────────────────────────────────── */
QToolButton {{
    background-color: transparent;
    border: none;
    color: {C.FG};
    padding: 4px 8px;
    border-radius: 4px;
}}
QToolButton:hover {{
    background-color: rgba(255, 255, 255, 6);
}}
QToolButton::menu-indicator {{
    image: none;
}}

/* ── Menus ────────────────────────────────────────────────────────── */
QMenu {{
    background-color: {C.BG_PANEL};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 4px 0;
    color: {C.FG};
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background-color: {C.ACCENT};
    color: {C.FG};
}}
QMenu::separator {{
    height: 1px;
    background-color: {C.BORDER};
    margin: 3px 8px;
}}

/* ── Scroll Bars ──────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 4px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {C.BORDER_2};
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {C.ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 4px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {C.BORDER_2};
    border-radius: 2px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {C.ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Sliders ──────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 3px;
    background-color: {C.BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {C.ACCENT};
    border: 2px solid {C.ACCENT};
    width: 12px;
    height: 12px;
    border-radius: 6px;
    margin: -5px 0;
}}
QSlider::handle:horizontal:hover {{
    background-color: {C.DANGER};
}}
QSlider::sub-page:horizontal {{
    background-color: {C.ACCENT};
    border-radius: 2px;
}}

/* ── Tooltips ─────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {C.BG_PANEL};
    color: {C.FG};
    border: 1px solid {C.BORDER_2};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: {T.SIZE_SM}px;
}}

/* ── Progress Bar ─────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {C.BORDER};
    border: none;
    border-radius: 2px;
    height: 3px;
}}
QProgressBar::chunk {{
    background-color: {C.ACCENT};
    border-radius: 2px;
}}

/* ── Line Edit ────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {C.BG_PANEL};
    color: {C.FG};
    border: 1px solid {C.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {C.ACCENT};
}}
QLineEdit:focus {{
    border-color: {C.ACCENT};
}}
QLineEdit:disabled {{
    color: {C.TEXT_DISABLED};
}}

/* ── Spin Boxes ───────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {{
    background-color: {C.BG_PANEL};
    color: {C.FG};
    border: 1px solid {C.BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: {C.ACCENT};
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {C.ACCENT};
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 14px;
}}

/* ── Table Widget ─────────────────────────────────────────────────── */
QTableWidget {{
    background-color: transparent;
    gridline-color: transparent;
    border: none;
    outline: none;
    color: {C.FG};
    alternate-background-color: rgba(22, 24, 38, 60);
}}
QTableWidget::item {{
    padding: 3px 6px;
    border: none;
    border-bottom: 1px solid {C.BORDER};
}}
QTableWidget::item:selected {{
    background-color: rgba(220, 38, 38, 18);
    color: {C.FG};
}}
QHeaderView::section {{
    background-color: transparent;
    color: {C.FG_4};
    border: none;
    border-bottom: 1px solid {C.BORDER};
    padding: 3px 6px;
    font-size: {T.SIZE_XS}px;
    font-weight: {T.WEIGHT_SEMIBOLD};
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QHeaderView {{
    background-color: transparent;
    border: none;
}}

/* ── Scroll Area ──────────────────────────────────────────────────── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ── Frame / Separator ────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="HLine"] {{
    color: {C.BORDER};
    background-color: {C.BORDER};
    border: none;
    max-height: 1px;
}}

/* ── Plain Text Edit ──────────────────────────────────────────────── */
QPlainTextEdit {{
    background-color: {C.BG_PANEL};
    color: {C.FG_2};
    border: 1px solid {C.BORDER};
    border-radius: 4px;
    padding: 4px;
    font-size: {T.SIZE_XS}px;
}}

/* ── Dialog ───────────────────────────────────────────────────────── */
QDialog {{
    background-color: {C.BG_PANEL};
}}

/* ── Tab Widget ───────────────────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {C.BG_PANEL};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {C.FG_3};
    padding: 6px 14px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {C.ACCENT};
    border-bottom-color: {C.ACCENT};
}}

"""


def apply_theme(app: QApplication) -> None:
    """Apply the Cockpit theme to *app*.

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
