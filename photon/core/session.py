"""PhotonSession — single source of truth for all loaded state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class FitsFrame:
    """A single loaded FITS frame with its metadata.

    Parameters
    ----------
    path : Path
        Absolute path to the source FITS file.
    data : np.ndarray
        2-D or 3-D pixel array (float32 after calibration).
    header : dict[str, Any]
        FITS header as a plain dict (FITS keyword → value).
    wcs : Any | None
        ``astropy.wcs.WCS`` object if plate-solved, else ``None``.
    """

    path: Path
    data: np.ndarray
    header: dict[str, Any] = field(default_factory=dict)
    wcs: Any | None = None


@dataclass
class PhotometryResult:
    """Aperture-photometry result for a single source in a single frame.

    Parameters
    ----------
    source_id : str
        Catalog identifier (e.g. SIMBAD main_id or Gaia DR3 source_id string).
    frame_index : int
        Index into ``PhotonSession.frames`` for the frame this was measured on.
    flux : float
        Net aperture flux in ADU.
    flux_err : float
        1-sigma flux uncertainty in ADU.
    bjd : float | None
        Barycentric Julian Date of mid-exposure, or ``None`` if not computed.
    """

    source_id: str
    frame_index: int
    flux: float
    flux_err: float
    bjd: float | None = None


@dataclass
class PhotonSession:
    """Container for all state belonging to a single Photon working session.

    ``MainWindow`` owns exactly one ``PhotonSession`` at a time.  Science modules
    receive the pieces they need as arguments and never hold a reference to the
    session itself.

    Parameters
    ----------
    frames : list[FitsFrame]
        Ordered list of loaded FITS frames.
    catalog_matches : dict[str, Any]
        Mapping of catalog name → query result table (``astropy.table.Table``).
    photometry : list[PhotometryResult]
        All photometry results across all frames and sources.
    target_name : str
        Human-readable target name set by the user.
    """

    frames: list[FitsFrame] = field(default_factory=list)
    catalog_matches: dict[str, Any] = field(default_factory=dict)
    photometry: list[PhotometryResult] = field(default_factory=list)
    target_name: str = ""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def add_frame(self, frame: FitsFrame) -> None:
        """Append *frame* to the session frame list.

        Parameters
        ----------
        frame : FitsFrame
            The frame to append.
        """
        self.frames.append(frame)

    def clear(self) -> None:
        """Reset the session to an empty state."""
        self.frames.clear()
        self.catalog_matches.clear()
        self.photometry.clear()
        self.target_name = ""

    @property
    def frame_count(self) -> int:
        """Number of frames currently loaded."""
        return len(self.frames)

    @property
    def is_plate_solved(self) -> bool:
        """``True`` if every loaded frame has a WCS solution."""
        return bool(self.frames) and all(f.wcs is not None for f in self.frames)
