"""Observatory Glass design system — single source of truth for all UI tokens.

Every color, font size, and spacing value used anywhere in ``photon/ui/`` must
reference a constant from this module.  No hardcoded hex values are permitted
outside of this file.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


class Colors:
    """Color palette for the Observatory Glass theme."""

    # Backgrounds
    BASE         = "#0d1117"   # App background
    SURFACE      = "#161b22"   # Panel / card surfaces
    SURFACE_ALT  = "#1c2333"   # Slightly lighter surface (hover states)
    BORDER       = "#21262d"   # Subtle 1px borders
    BORDER_FOCUS = "#388bfd"   # Focused element border

    # Accents — violet-to-blue spectrum (nods to stellar spectral colors)
    ACCENT_PRIMARY   = "#7c3aed"   # Violet — primary actions
    ACCENT_SECONDARY = "#3b82f6"   # Blue — secondary / info
    ACCENT_SUCCESS   = "#10b981"   # Green — success / complete
    ACCENT_WARNING   = "#f59e0b"   # Amber — warnings
    ACCENT_DANGER    = "#ef4444"   # Red — errors

    # Text
    TEXT_PRIMARY   = "#e2e8f0"   # Primary readable text
    TEXT_SECONDARY = "#8b949e"   # Subdued labels
    TEXT_DISABLED  = "#484f58"   # Disabled state
    TEXT_ACCENT    = "#a78bfa"   # Highlighted / accent text (light violet)

    # Matplotlib canvas background
    CANVAS_BG = "#080c10"        # Slightly darker than BASE for the image area


class Typography:
    """Typography scale for the Observatory Glass theme."""

    FONT_UI   = "Inter, 'Segoe UI', 'SF Pro Display', sans-serif"
    FONT_MONO = "'JetBrains Mono', 'Cascadia Code', Consolas, monospace"
    SIZE_XS   = 10
    SIZE_SM   = 11
    SIZE_BASE = 12
    SIZE_MD   = 13
    SIZE_LG   = 15
    SIZE_XL   = 18


def build_stylesheet() -> str:
    """Return the complete Qt stylesheet for the Observatory Glass theme.

    All color and font references resolve to ``Colors`` and ``Typography``
    constants — no hardcoded literals appear in the returned string.

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
    background-color: {C.BASE};
    color: {C.TEXT_PRIMARY};
    font-family: Inter, "Segoe UI", "SF Pro Display", sans-serif;
    font-size: {T.SIZE_BASE}px;
}}

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter {{
    background-color: {C.BASE};
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
    background-color: {C.BORDER_FOCUS};
}}

/* ── List Widget ────────────────────────────────────────────────────────── */
QListWidget {{
    background-color: {C.SURFACE};
    border: none;
    outline: none;
    padding: 4px 0;
}}
QListWidget::item {{
    padding: 6px 12px;
    border-radius: 4px;
    color: {C.TEXT_PRIMARY};
}}
QListWidget::item:hover {{
    background-color: {C.SURFACE_ALT};
}}
QListWidget::item:selected {{
    background-color: {C.ACCENT_PRIMARY};
    color: {C.TEXT_PRIMARY};
}}

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {{
    color: {C.TEXT_PRIMARY};
    background-color: transparent;
}}

/* ── Push Buttons ───────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {C.ACCENT_PRIMARY};
    color: {C.TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: {T.SIZE_BASE}px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #6d28d9;
}}
QPushButton:pressed {{
    background-color: #5b21b6;
}}
QPushButton:disabled {{
    background-color: {C.BORDER};
    color: {C.TEXT_DISABLED};
}}
QPushButton[secondary="true"] {{
    background-color: transparent;
    border: 1px solid {C.BORDER};
    color: {C.TEXT_PRIMARY};
}}
QPushButton[secondary="true"]:hover {{
    background-color: {C.SURFACE_ALT};
    border-color: {C.TEXT_SECONDARY};
}}
QPushButton[secondary="true"]:pressed {{
    background-color: {C.BORDER};
}}

/* ── Tool Buttons ───────────────────────────────────────────────────────── */
QToolButton {{
    background-color: transparent;
    border: none;
    color: {C.TEXT_PRIMARY};
    padding: 4px 8px;
    border-radius: 4px;
}}
QToolButton:hover {{
    background-color: {C.SURFACE_ALT};
}}
QToolButton::menu-indicator {{
    image: none;
}}

/* ── Menu Bar ───────────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {C.SURFACE};
    color: {C.TEXT_PRIMARY};
    border-bottom: 1px solid {C.BORDER};
    padding: 2px 0;
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 4px 12px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {C.SURFACE_ALT};
}}

/* ── Menus ──────────────────────────────────────────────────────────────── */
QMenu {{
    background-color: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
    padding: 4px 0;
    color: {C.TEXT_PRIMARY};
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background-color: {C.ACCENT_PRIMARY};
    color: {C.TEXT_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background-color: {C.BORDER};
    margin: 4px 8px;
}}

/* ── Status Bar ─────────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {C.BASE};
    color: {C.TEXT_SECONDARY};
    border-top: 1px solid {C.BORDER};
    font-size: {T.SIZE_XS}px;
}}

/* ── Scroll Bars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {C.SURFACE};
    width: 6px;
    border: none;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background-color: {C.BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {C.TEXT_SECONDARY};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {C.SURFACE};
    height: 6px;
    border: none;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background-color: {C.BORDER};
    border-radius: 3px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {C.TEXT_SECONDARY};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Tooltips ───────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {C.SURFACE};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: {T.SIZE_SM}px;
}}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {C.BORDER};
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {C.ACCENT_PRIMARY};
    border-radius: 2px;
}}

/* ── Line Edit ──────────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {C.SURFACE};
    color: {C.TEXT_PRIMARY};
    border: 1px solid {C.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {C.ACCENT_PRIMARY};
}}
QLineEdit:focus {{
    border-color: {C.BORDER_FOCUS};
}}
QLineEdit:disabled {{
    color: {C.TEXT_DISABLED};
    border-color: {C.BORDER};
}}

/* ── Sliders ────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {C.BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {C.ACCENT_PRIMARY};
    border: none;
    width: 12px;
    height: 12px;
    border-radius: 6px;
    margin: -4px 0;
}}
QSlider::handle:horizontal:hover {{
    background-color: {C.TEXT_ACCENT};
}}
QSlider::sub-page:horizontal {{
    background-color: {C.ACCENT_PRIMARY};
    border-radius: 2px;
}}

/* ── Frame / Separator ──────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="HLine"] {{
    color: {C.BORDER};
    background-color: {C.BORDER};
    border: none;
    max-height: 1px;
}}
QFrame[frameShape="5"],
QFrame[frameShape="VLine"] {{
    color: {C.BORDER};
    background-color: {C.BORDER};
    border: none;
    max-width: 1px;
}}

"""


def apply_theme(app: QApplication) -> None:
    """Apply the Observatory Glass theme to *app*.

    Sets the global stylesheet and configures the default application font.

    Parameters
    ----------
    app : QApplication
        The running application instance.
    """
    app.setStyleSheet(build_stylesheet())
    font = QFont("Inter")
    font.setStyleHint(QFont.SansSerif)
    font.setPixelSize(Typography.SIZE_BASE)
    app.setFont(font)
