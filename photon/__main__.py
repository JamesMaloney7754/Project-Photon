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
    # ── Logging setup — file handler first so crashes are always captured ──
    _fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Keep matplotlib font-scoring messages out of the diagnostic log
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

    debug_log_path = Path.home() / "photon_debug.log"
    _file_handler = logging.FileHandler(str(debug_log_path))
    _file_handler.setFormatter(_fmt)
    root_logger.addHandler(_file_handler)

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

    # Attach Qt log handler now that the window (and its log_widget) exists
    from photon.ui.main_window import QtLogHandler
    _qt_fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    _qt_handler = QtLogHandler(window.log_widget)
    _qt_handler.setFormatter(_qt_fmt)
    root_logger.addHandler(_qt_handler)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
