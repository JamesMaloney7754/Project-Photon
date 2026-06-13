"""MetricsPane — solution & measurements dashboard pane."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QWidget

from photon.ui.big_stat_widget import BigStatWidget
from photon.ui.cockpit_pane import CockpitPane
from photon.ui.theme import Colors


class MetricsPane(CockpitPane):
    """Top-right dashboard pane: 6 BigStatWidget cells in a 3×2 grid.

    Grid layout
    -----------
    Row 0: RA Center | Dec Center | Pixel Scale
    Row 1: Target Flux (ADU) | Diff Magnitude | RMS Scatter

    Signals
    -------
    solve_requested : Signal()
        Emitted when the user clicks "Solve Field".
    """

    solve_requested: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(title="Solution & Measurements", parent=parent)

        # ── Solve Field button in header ──────────────────────────────────
        self._solve_btn = QPushButton("Solve Field")
        self._solve_btn.setFixedHeight(24)
        self._solve_btn.setStyleSheet(
            f"font-size: 10px; padding: 2px 10px; border-radius: 4px;"
        )
        self._solve_btn.clicked.connect(self.solve_requested)
        self.header_right_layout().addWidget(self._solve_btn)

        # ── Content: 3×2 grid of BigStatWidgets ──────────────────────────
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(content)
        grid.setContentsMargins(16, 12, 16, 16)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        self._ra_stat    = BigStatWidget(label="RA Center",      value="—")
        self._dec_stat   = BigStatWidget(label="Dec Center",     value="—")
        self._scale_stat = BigStatWidget(label="Pixel Scale",    value="—")
        self._flux_stat  = BigStatWidget(label="Target Flux",    value="—", error="ADU")
        self._mag_stat   = BigStatWidget(label="Diff Magnitude", value="—")
        self._rms_stat   = BigStatWidget(label="RMS Scatter",    value="—")

        # Amber accent for science values
        for w in (self._ra_stat, self._dec_stat, self._scale_stat,
                  self._flux_stat, self._mag_stat, self._rms_stat):
            w.set_accent(Colors.AMBER)

        grid.addWidget(self._ra_stat,    0, 0)
        grid.addWidget(self._dec_stat,   0, 1)
        grid.addWidget(self._scale_stat, 0, 2)
        grid.addWidget(self._flux_stat,  1, 0)
        grid.addWidget(self._mag_stat,   1, 1)
        grid.addWidget(self._rms_stat,   1, 2)

        self.set_content_widget(content)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_wcs(
        self,
        ra_str: str,
        dec_str: str,
        scale_str: str,
        rotation_str: str = "",
    ) -> None:
        """Update the astrometric solution cells.

        Parameters
        ----------
        ra_str : str
            Formatted RA string (e.g. ``"12h 34m 56.7s"``).
        dec_str : str
            Formatted Dec string (e.g. ``"+45° 30' 12.3"``).
        scale_str : str
            Pixel scale string (e.g. ``"1.23 ″/px"``).
        rotation_str : str
            Optional rotation / position angle string used as subtitle.
        """
        self._ra_stat.set_value(ra_str)
        self._dec_stat.set_value(dec_str)
        self._scale_stat.set_value(scale_str)
        if rotation_str:
            self.set_subtitle(rotation_str)

    def update_photometry(
        self,
        flux_str: str,
        mag_str: str,
        rms_str: str,
    ) -> None:
        """Update the photometry result cells.

        Parameters
        ----------
        flux_str : str
            Target flux string (e.g. ``"42 350"``).
        mag_str : str
            Differential magnitude string (e.g. ``"0.023"``).
        rms_str : str
            RMS scatter string (e.g. ``"0.008"``).
        """
        self._flux_stat.set_value(flux_str)
        self._mag_stat.set_value(mag_str)
        self._rms_stat.set_value(rms_str)

    def set_solving_state(self, is_solving: bool) -> None:
        """Toggle the Solve Field button while a solve is running.

        Parameters
        ----------
        is_solving : bool
            ``True`` while plate solving; ``False`` when idle.
        """
        self._solve_btn.setEnabled(not is_solving)
        self._solve_btn.setText("Solving…" if is_solving else "Solve Field")

    def set_solve_error(self, message: str) -> None:
        """Display a solve error in the RA Center cell and re-enable the button.

        Parameters
        ----------
        message : str
            Short error description shown in the RA stat cell.
        """
        self._ra_stat.set_value("Error")
        self._ra_stat.set_error(message[:40])
        self._solve_btn.setEnabled(True)
        self._solve_btn.setText("Solve Field")
        self.set_subtitle("Solve failed")
