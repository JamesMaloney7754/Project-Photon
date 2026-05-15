"""SettingsManager — typed singleton wrapper around QSettings.

Provides application-wide access to all user preferences with typed defaults.
Behaves as a singleton: always call :func:`get_settings_manager` to obtain
the shared instance.

Note: this module imports ``QSettings`` from PySide6.  It lives in
``photon/core/`` as an application-service module rather than a science module;
it contains no display or rendering logic.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    # General
    "general/theme": "deep_field",
    "general/confirm_on_quit": True,
    "general/recent_directories": [],

    # Plate solving
    "platesolve/backend": "astap",
    "platesolve/astap_binary_path": "",
    "platesolve/astap_search_radius": 30,
    "platesolve/astap_downsample": 0,
    "platesolve/local_binary_path": "",
    "platesolve/index_dir": "",
    "platesolve/astrometry_api_key": "",
    "platesolve/scale_units": "arcsecperpix",
    "platesolve/scale_low": 0.1,
    "platesolve/scale_high": 10.0,
    "platesolve/timeout_seconds": 120,

    # Photometry
    "photometry/aperture_radius_px": 8.0,
    "photometry/annulus_inner_px": 12.0,
    "photometry/annulus_outer_px": 20.0,
    "photometry/detection_fwhm": 3.0,
    "photometry/detection_threshold_sigma": 5.0,
    "photometry/max_comparison_stars": 10,
    "photometry/min_comparison_snr": 50.0,

    # Catalog
    "catalog/search_radius_arcmin": 15.0,
    "catalog/use_simbad": True,
    "catalog/use_gaia": True,
    "catalog/use_vsx": True,

    # Export
    "export/default_format": "csv",
    "export/include_headers": True,
}

_MAX_RECENT = 8


class SettingsManager:
    """Typed wrapper around ``QSettings`` for all Photon preferences.

    Do not instantiate directly; use :func:`get_settings_manager`.

    Parameters
    ----------
    use_ini : bool
        When ``True``, uses an in-memory INI backend (useful for testing).
        Defaults to ``False`` (native OS backend).
    """

    def __init__(self, *, use_ini: bool = False) -> None:
        try:
            from PySide6.QtCore import QSettings
            if use_ini:
                self._settings = QSettings(
                    QSettings.Format.IniFormat,
                    QSettings.Scope.UserScope,
                    "PhotonAstro",
                    "Photon",
                )
            else:
                self._settings = QSettings("PhotonAstro", "Photon")
            self._qt_available = True
        except Exception as exc:
            logger.warning("QSettings unavailable (%s); using in-memory store.", exc)
            self._settings = None
            self._qt_available = False
            self._mem: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Core access
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        """Return the value for *key*, falling back to :data:`DEFAULTS`.

        Parameters
        ----------
        key : str
            Dot-free key in ``"section/name"`` form.

        Returns
        -------
        Any
            Stored value if present, otherwise the default from
            :data:`DEFAULTS`.
        """
        default = DEFAULTS.get(key)
        if not self._qt_available:
            return self._mem.get(key, default)
        raw = self._settings.value(key, default)
        # Coerce type to match default
        if isinstance(default, bool):
            if isinstance(raw, str):
                return raw.lower() not in ("false", "0", "no")
            return bool(raw)
        if isinstance(default, float) and not isinstance(raw, float):
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default
        if isinstance(default, int) and not isinstance(raw, int):
            try:
                return int(raw)
            except (TypeError, ValueError):
                return default
        if isinstance(default, list) and not isinstance(raw, list):
            return default
        return raw

    def set(self, key: str, value: Any) -> None:
        """Persist *value* under *key* immediately.

        Parameters
        ----------
        key : str
            Settings key in ``"section/name"`` form.
        value : Any
            Value to store.
        """
        if not self._qt_available:
            self._mem[key] = value
            return
        self._settings.setValue(key, value)
        self._settings.sync()

    def reset_to_defaults(self) -> None:
        """Clear all stored values and revert every key to its default."""
        if not self._qt_available:
            self._mem.clear()
            return
        self._settings.clear()
        self._settings.sync()
        logger.info("Settings reset to defaults.")

    # ------------------------------------------------------------------
    # Recent directories
    # ------------------------------------------------------------------

    def get_recent_directories(self) -> list[Path]:
        """Return recently opened directories as a list of :class:`Path`.

        Returns
        -------
        list[Path]
            Up to 8 paths, most-recent first.  Non-existent paths are excluded.
        """
        raw: list = self.get("general/recent_directories")
        if not isinstance(raw, list):
            return []
        return [Path(p) for p in raw if Path(p).exists()]

    def add_recent_directory(self, path: Path) -> None:
        """Prepend *path* to the recent-directories list.

        Deduplicates and trims to 8 entries.

        Parameters
        ----------
        path : Path
            Directory path to prepend.
        """
        raw: list = self.get("general/recent_directories")
        if not isinstance(raw, list):
            raw = []
        path_str = str(path)
        entries = [p for p in raw if p != path_str]
        entries.insert(0, path_str)
        self.set("general/recent_directories", entries[:_MAX_RECENT])


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_instance: SettingsManager | None = None


def get_settings_manager() -> SettingsManager:
    """Return the application-wide :class:`SettingsManager` singleton.

    Returns
    -------
    SettingsManager
        The shared settings instance, created on first call.
    """
    global _instance
    if _instance is None:
        _instance = SettingsManager()
    return _instance
