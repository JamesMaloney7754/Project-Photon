import sys
from PySide6.QtWidgets import QApplication
from photon.ui.main_window import MainWindow


def main() -> None:
    """Launch the Photon desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Photon")
    app.setOrganizationName("Photon Astrophotography")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
