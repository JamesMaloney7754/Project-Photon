"""Tests for photon.core.fits_loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from photon.core.fits_loader import (
    get_observation_times,
    load_fits_sequence,
    summarize_sequence,
)


# ---------------------------------------------------------------------------
# 1. test_load_single_fits
# ---------------------------------------------------------------------------

def test_load_single_fits(sample_fits_path: Path) -> None:
    """Load one file; stack shape is (1, H, W), dtype float64, one header."""
    stack, headers = load_fits_sequence([sample_fits_path])

    assert stack.ndim == 3, "stack must be 3-D"
    assert stack.shape[0] == 1, "first axis must equal number of input files"
    assert stack.dtype == np.float64, "dtype must be float64"
    assert len(headers) == 1, "one header per frame"


# ---------------------------------------------------------------------------
# 2. test_load_sequence_consistent_dims
# ---------------------------------------------------------------------------

def test_load_sequence_consistent_dims(sample_fits_sequence: tuple) -> None:
    """3-frame sequence produces a (3, H, W) stack."""
    stack, headers = sample_fits_sequence

    assert stack.shape[0] == 3, "first axis must equal 3"
    assert stack.ndim == 3, "stack must be 3-D"
    assert len(headers) == 3, "one header per frame"
    # All spatial dims identical (sequence was built from the same file)
    assert stack.shape[1] > 0 and stack.shape[2] > 0


# ---------------------------------------------------------------------------
# 3. test_load_empty_sequence_raises
# ---------------------------------------------------------------------------

def test_load_empty_sequence_raises() -> None:
    """Empty path list must raise ValueError."""
    with pytest.raises(ValueError):
        load_fits_sequence([])


# ---------------------------------------------------------------------------
# 4. test_load_missing_file_raises
# ---------------------------------------------------------------------------

def test_load_missing_file_raises(tmp_path: Path) -> None:
    """Nonexistent path must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_fits_sequence([tmp_path / "no_such_file.fits"])


# ---------------------------------------------------------------------------
# 5. test_summarize_sequence_keys
# ---------------------------------------------------------------------------

def test_summarize_sequence_keys(sample_fits_path: Path) -> None:
    """summarize_sequence dict must contain n_frames, dimensions, date_range."""
    stack, headers = load_fits_sequence([sample_fits_path])
    summary = summarize_sequence([sample_fits_path], stack, headers)

    assert isinstance(summary, dict)
    for key in ("n_frames", "dimensions", "date_range"):
        assert key in summary, f"missing key: {key!r}"


# ---------------------------------------------------------------------------
# Additional coverage (synthetic, no network)
# ---------------------------------------------------------------------------

def test_load_sequence_dtype_float64(synthetic_fits_sequence: list[Path]) -> None:
    """Pixel data must be float64 regardless of source dtype."""
    stack, _ = load_fits_sequence(synthetic_fits_sequence)
    assert stack.dtype == np.float64


def test_load_sequence_frame_count(synthetic_fits_sequence: list[Path]) -> None:
    """Stack first axis equals number of input paths."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    assert stack.shape[0] == len(synthetic_fits_sequence)
    assert len(headers) == len(synthetic_fits_sequence)


def test_dimension_mismatch_raises(tmp_path: Path) -> None:
    """Frames with different shapes must raise ValueError."""
    p1, p2 = tmp_path / "a.fits", tmp_path / "b.fits"
    fits.PrimaryHDU(np.zeros((32, 32), dtype=np.float32)).writeto(p1)
    fits.PrimaryHDU(np.zeros((64, 64), dtype=np.float32)).writeto(p2)
    with pytest.raises(ValueError, match="dimension mismatch"):
        load_fits_sequence([p1, p2])


def test_not_a_fits_file_raises(tmp_path: Path) -> None:
    """Invalid FITS file must raise OSError."""
    bad = tmp_path / "bad.fits"
    bad.write_bytes(b"not a fits file")
    with pytest.raises(OSError):
        load_fits_sequence([bad])


def test_get_times_date_obs(synthetic_fits_sequence: list[Path]) -> None:
    """get_observation_times parses DATE-OBS keyword."""
    from astropy.time import Time

    _, headers = load_fits_sequence(synthetic_fits_sequence)
    times = get_observation_times(headers)
    assert isinstance(times, Time)
    assert len(times) == len(headers)


def test_get_times_no_keyword_raises(tmp_path: Path) -> None:
    """Missing time keywords must raise ValueError."""
    p = tmp_path / "notime.fits"
    fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32)).writeto(p)
    _, headers = load_fits_sequence([p])
    with pytest.raises(ValueError, match="time keyword"):
        get_observation_times(headers)


def test_summarize_n_frames(synthetic_fits_sequence: list[Path]) -> None:
    """n_frames key must equal number of loaded frames."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert summary["n_frames"] == len(synthetic_fits_sequence)


def test_summarize_median_sky_finite(synthetic_fits_sequence: list[Path]) -> None:
    """median_sky must be a finite float."""
    stack, headers = load_fits_sequence(synthetic_fits_sequence)
    summary = summarize_sequence(synthetic_fits_sequence, stack, headers)
    assert isinstance(summary["median_sky"], float)
    assert np.isfinite(summary["median_sky"])
