import sys

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from photon.ui.main_window import MainWindow
from photon.ui.theme import Colors, apply_theme


def main() -> None:
    """Launch the Photon desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Photon")
    app.setOrganizationName("Photon Astrophotography")

    apply_theme(app)

    # Placeholder icon: 32×32 filled with the accent color
    icon = QIcon()
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(Colors.ACCENT_PRIMARY))
    icon.addPixmap(pixmap)
    app.setWindowIcon(icon)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
