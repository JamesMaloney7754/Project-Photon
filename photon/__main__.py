"""Entry point for ``python -m photon`` and the ``photon`` console script."""

from __future__ import annotations

import logging
import sys


def main() -> None:
    """Launch the Photon desktop application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    from PySide6.QtWidgets import QApplication
    from photon.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Photon")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("photon-astro")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
