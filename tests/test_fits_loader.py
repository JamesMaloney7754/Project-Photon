"""Tests for photon.core.fits_loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.time import Time

from photon.core.fits_loader import (
    get_observation_times,
    load_fits_sequence,
    summarize_sequence,
)


# ---------------------------------------------------------------------------
# load_fits_sequence — happy path
# ---------------------------------------------------------------------------

def test_load_single_frame_returns_stack(synthetic_fits_path: Path) -> None:
    """load_fits_sequence with one path returns a (1, H, W) stack."""
    stack, headers = load_fits_sequence([synthetic_fits_path])
    assert stack.ndim == 3
    assert stack.shape[0] == 1


def test_load_sequence_frame_count(synthetic_fits_sequence: list[Path]) -> None:
    """Stack first axis equals the number of input paths."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    assert stack.shape[0] == len(synthetic_fits_sequence)
    assert len(headers) == len(synthetic_fits_sequence)


def test_load_sequence_dtype_float64(synthetic_fits_sequence: list[Path]) -> None:
    """Pixel data must be float64 regardless of source dtype."""
    stack, _ = load_fits_sequence(synthetic_fits_sequence)
    assert stack.dtype == np.float64


def test_load_single_frame_shape(synthetic_fits_path: Path) -> None:
    """Spatial shape matches the fixture's 64×64 array."""
    stack, _ = load_fits_sequence([synthetic_fits_path])
    assert stack.shape[1:] == (64, 64)


def test_load_sequence_headers_preserved(synthetic_fits_sequence: list[Path]) -> None:
    """FITS headers must preserve original keywords."""
    _, headers = load_fits_sequence(synthetic_fits_sequence)
    for h in headers:
        assert "OBJECT" in h
        assert h["OBJECT"] == "TEST_TARGET"


def test_load_sequence_stack_values_finite(synthetic_fits_sequence: list[Path]) -> None:
    """All pixels in the loaded stack must be finite."""
    stack, _ = load_fits_sequence(synthetic_fits_sequence)
    assert np.all(np.isfinite(stack))


# ---------------------------------------------------------------------------
# load_fits_sequence — error cases
# ---------------------------------------------------------------------------

def test_empty_paths_raises_value_error() -> None:
    """load_fits_sequence must raise ValueError for an empty list."""
    with pytest.raises(ValueError, match="at least one"):
        load_fits_sequence([])


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    """load_fits_sequence must raise FileNotFoundError for a nonexistent path."""
    with pytest.raises(FileNotFoundError, match="not found"):
        load_fits_sequence([tmp_path / "ghost.fits"])


def test_dimension_mismatch_raises_value_error(tmp_path: Path) -> None:
    """load_fits_sequence must raise ValueError when frames differ in size."""
    path_a = tmp_path / "a.fits"
    path_b = tmp_path / "b.fits"
    fits.PrimaryHDU(np.zeros((32, 32), dtype=np.float32)).writeto(path_a)
    fits.PrimaryHDU(np.zeros((64, 64), dtype=np.float32)).writeto(path_b)
    with pytest.raises(ValueError, match="dimension mismatch"):
        load_fits_sequence([path_a, path_b])


def test_not_a_fits_file_raises(tmp_path: Path) -> None:
    """load_fits_sequence must raise OSError for an invalid FITS file."""
    bad = tmp_path / "bad.fits"
    bad.write_bytes(b"not a fits file")
    with pytest.raises(OSError):
        load_fits_sequence([bad])


# ---------------------------------------------------------------------------
# get_observation_times
# ---------------------------------------------------------------------------

def test_get_times_from_date_obs(synthetic_fits_sequence: list[Path]) -> None:
    """get_observation_times should parse DATE-OBS keywords."""
    _, headers = load_fits_sequence(synthetic_fits_sequence)
    times = get_observation_times(headers)
    assert isinstance(times, Time)
    assert len(times) == len(headers)


def test_get_times_from_jd(tmp_path: Path) -> None:
    """get_observation_times should fall back to JD keyword."""
    paths = []
    for i, jd in enumerate([2460000.0, 2460001.0]):
        p = tmp_path / f"jd_{i}.fits"
        hdu = fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32))
        hdu.header["JD"] = jd
        hdu.writeto(p)
        paths.append(p)
    _, headers = load_fits_sequence(paths)
    times = get_observation_times(headers)
    assert times.format == "jd"
    assert abs(float(times[1].jd) - 2460001.0) < 1e-6


def test_get_times_from_mjd(tmp_path: Path) -> None:
    """get_observation_times should fall back to MJD keyword."""
    paths = []
    for i in range(2):
        p = tmp_path / f"mjd_{i}.fits"
        hdu = fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32))
        hdu.header["MJD"] = 60000.0 + i
        hdu.writeto(p)
        paths.append(p)
    _, headers = load_fits_sequence(paths)
    times = get_observation_times(headers)
    assert times.format == "mjd"


def test_get_times_no_keyword_raises(tmp_path: Path) -> None:
    """get_observation_times must raise ValueError when no time keyword is present."""
    p = tmp_path / "notime.fits"
    fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32)).writeto(p)
    _, headers = load_fits_sequence([p])
    with pytest.raises(ValueError, match="time keyword"):
        get_observation_times(headers)


def test_get_times_empty_raises() -> None:
    """get_observation_times must raise ValueError for empty headers list."""
    with pytest.raises(ValueError, match="empty"):
        get_observation_times([])


# ---------------------------------------------------------------------------
# summarize_sequence
# ---------------------------------------------------------------------------

def test_summarize_returns_dict(synthetic_fits_sequence: list[Path]) -> None:
    """summarize_sequence should return a dict."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert isinstance(summary, dict)


def test_summarize_n_frames(synthetic_fits_sequence: list[Path]) -> None:
    """n_frames key must equal number of input frames."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert summary["n_frames"] == len(synthetic_fits_sequence)


def test_summarize_dimensions(synthetic_fits_path: Path) -> None:
    """dimensions key must reflect the image dimensions."""
    stack, headers = load_fits_sequence([synthetic_fits_path])
    summary = summarize_sequence([synthetic_fits_path], stack, headers)
    assert "64" in summary["dimensions"]


def test_summarize_filter_keyword(synthetic_fits_sequence: list[Path]) -> None:
    """filter key must reflect the FILTER header keyword."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert summary["filter"] == "R"


def test_summarize_median_sky_is_float(synthetic_fits_sequence: list[Path]) -> None:
    """median_sky must be a finite float."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert isinstance(summary["median_sky"], float)
    assert np.isfinite(summary["median_sky"])


def test_summarize_date_range_present(synthetic_fits_sequence: list[Path]) -> None:
    """date_range key must be a non-empty string when DATE-OBS headers exist."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert isinstance(summary["date_range"], str)
    assert summary["date_range"] != "unknown"
