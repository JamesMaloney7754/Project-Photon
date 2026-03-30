"""PhotonSession — single source of truth for all loaded state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class PhotonSession:
    """Container for all state belonging to a single Photon working session.

    ``MainWindow`` owns exactly one ``PhotonSession`` at a time.  Science modules
    receive the pieces they need as arguments and never hold a reference to the
    session itself.

    Parameters
    ----------
    fits_paths : list[Path]
        Ordered list of FITS file paths that have been loaded.
    image_stack : np.ndarray | None
        Raw image data with shape ``(N_frames, height, width)``, dtype float64.
        ``None`` until at least one frame is loaded.
    headers : list
        Per-frame ``astropy.io.fits.Header`` objects, one per frame in the same
        order as ``fits_paths``.
    wcs : object | None
        ``astropy.wcs.WCS`` object from the plate solution, or ``None`` if the
        sequence has not been plate-solved.
    catalog_matches : object | None
        ``astropy.table.Table`` of catalog cross-matches, or ``None`` if no
        cross-match has been performed.
    photometry_results : dict
        Mapping of ``source_id`` (str) → 1-D numpy array of flux measurements
        across all frames.
    light_curve : object | None
        ``astropy.table.Table`` of the target light curve (time, flux, flux_err
        columns), or ``None`` if photometry has not been run.
    """

    fits_paths: list[Path] = field(default_factory=list)
    image_stack: Optional[np.ndarray] = None
    headers: list = field(default_factory=list)
    wcs: Optional[object] = None
    catalog_matches: Optional[object] = None
    photometry_results: dict = field(default_factory=dict)
    light_curve: Optional[object] = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset the session to an empty state."""
        self.fits_paths.clear()
        self.image_stack = None
        self.headers.clear()
        self.wcs = None
        self.catalog_matches = None
        self.photometry_results.clear()
        self.light_curve = None

    @property
    def frame_count(self) -> int:
        """Number of frames currently loaded."""
        return len(self.fits_paths)

    @property
    def is_loaded(self) -> bool:
        """``True`` if at least one frame is in the session."""
        return self.image_stack is not None and len(self.fits_paths) > 0

    @property
    def is_plate_solved(self) -> bool:
        """``True`` if the session has a WCS solution."""
        return self.wcs is not None
