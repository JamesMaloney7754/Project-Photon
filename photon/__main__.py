"""Photon application entry point."""

import logging
import sys

from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from photon.ui.main_window import MainWindow
from photon.ui.theme import Colors, apply_theme

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the Photon desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Photon")
    app.setOrganizationName("Photon Astrophotography")

    # Font detection
    families = QFontDatabase.families()
    if "Inter" in families:
        logger.info("Font selected: Inter (system)")
    elif "Segoe UI Variable" in families:
        logger.info("Font selected: Segoe UI Variable (system)")
    else:
        logger.info("Font selected: system UI fallback")

    # Fusion base style — most consistent cross-platform Qt base for custom QSS
    app.setStyle("Fusion")

    apply_theme(app)

    # Application icon (32×32, violet accent color)
    icon = QIcon()
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(Colors.VIOLET))
    icon.addPixmap(pixmap)
    app.setWindowIcon(icon)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
