"""Photon application entry point."""

import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from photon.ui.main_window import MainWindow
from photon.ui.theme import Colors, apply_theme

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the Photon desktop application."""
    # ── Crash logging — must be set up before anything else ───────────────
    log_path = Path.home() / "photon_crash.log"
    logging.basicConfig(
        filename=str(log_path),
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    def handle_exception(
        exc_type: type,
        exc_value: BaseException,
        exc_tb: object,
    ) -> None:
        logging.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = handle_exception

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
