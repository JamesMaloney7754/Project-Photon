"""Tests for photon.core.session — PhotonSession state model."""

from __future__ import annotations

import numpy as np
import pytest

from photon.core.session import PhotonSession


def test_initial_state_is_empty() -> None:
    """A freshly constructed PhotonSession has no loaded data."""
    s = PhotonSession()
    assert s.frame_count == 0
    assert s.is_loaded is False
    assert s.is_plate_solved is False
    assert s.image_stack is None
    assert s.detected_stars is None
    assert s.target_xy is None
    assert s.comparison_xys == []
    assert s.photometry_result is None
    assert s.frame_flags is None


def test_is_loaded_after_stack_and_paths(tmp_path) -> None:
    """is_loaded returns True when both image_stack and fits_paths are set."""
    from pathlib import Path

    s = PhotonSession()
    s.image_stack = np.zeros((2, 10, 10))
    s.fits_paths = [Path(tmp_path / "a.fits"), Path(tmp_path / "b.fits")]
    assert s.is_loaded is True
    assert s.frame_count == 2


def test_is_loaded_requires_both_stack_and_paths() -> None:
    """is_loaded is False if only one of stack / paths is set."""
    from pathlib import Path

    s = PhotonSession()
    s.image_stack = np.zeros((1, 10, 10))
    # No paths set
    assert s.is_loaded is False

    s2 = PhotonSession()
    s2.fits_paths = [Path("/fake/a.fits")]
    # No stack set
    assert s2.is_loaded is False


def test_clear_resets_all_fields(tmp_path) -> None:
    """clear() resets every field back to the empty state."""
    from pathlib import Path

    s = PhotonSession()
    s.image_stack = np.zeros((3, 20, 20))
    s.fits_paths = [Path(tmp_path / f"{i}.fits") for i in range(3)]
    s.headers = [{}, {}, {}]
    s.detected_stars = object()  # dummy non-None value
    s.target_xy = (10.0, 20.0)
    s.target_star_row = 5
    s.comparison_xys = [(30.0, 40.0)]
    s.comparison_star_rows = [7]
    s.photometry_result = {"scatter": 0.003}
    s.frame_flags = np.zeros(3, dtype=bool)
    s.light_curve = object()

    s.clear()

    assert s.frame_count == 0
    assert s.is_loaded is False
    assert s.headers == []
    assert s.detected_stars is None
    assert s.target_xy is None
    assert s.target_star_row is None
    assert s.comparison_xys == []
    assert s.comparison_star_rows == []
    assert s.photometry_result is None
    assert s.frame_flags is None
    assert s.light_curve is None


def test_is_plate_solved() -> None:
    """is_plate_solved returns True only when wcs is set."""
    s = PhotonSession()
    assert s.is_plate_solved is False
    s.wcs = object()  # any non-None value simulates a WCS
    assert s.is_plate_solved is True
