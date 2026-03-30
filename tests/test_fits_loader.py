"""Tests for photon.core.fits_loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from photon.core.fits_loader import FitsLoadError, debayer, load_fits
from photon.core.session import FitsFrame


# ---------------------------------------------------------------------------
# load_fits — happy path
# ---------------------------------------------------------------------------

def test_load_fits_returns_fits_frame(synthetic_fits_path: Path) -> None:
    """load_fits should return a FitsFrame for a valid FITS file."""
    frame = load_fits(synthetic_fits_path)
    assert isinstance(frame, FitsFrame)


def test_load_fits_data_is_float32(synthetic_fits_path: Path) -> None:
    """Pixel data must always be float32 regardless of the source dtype."""
    frame = load_fits(synthetic_fits_path)
    assert frame.data.dtype == np.float32


def test_load_fits_data_shape(synthetic_fits_path: Path) -> None:
    """Loaded data shape must match the written array shape (64×64)."""
    frame = load_fits(synthetic_fits_path)
    assert frame.data.shape == (64, 64)


def test_load_fits_header_populated(synthetic_fits_path: Path) -> None:
    """Header dict must contain the keywords written during fixture creation."""
    frame = load_fits(synthetic_fits_path)
    assert "OBJECT" in frame.header
    assert frame.header["OBJECT"] == "TEST_TARGET"


def test_load_fits_path_is_absolute(synthetic_fits_path: Path) -> None:
    """FitsFrame.path must be an absolute path."""
    frame = load_fits(synthetic_fits_path)
    assert frame.path.is_absolute()


def test_load_fits_no_wcs_returns_none(synthetic_fits_path: Path) -> None:
    """WCS should be None when the file has no WCS keywords."""
    frame = load_fits(synthetic_fits_path)
    assert frame.wcs is None


# ---------------------------------------------------------------------------
# load_fits — WCS present
# ---------------------------------------------------------------------------

def test_load_fits_wcs_parsed(synthetic_fits_with_wcs: Path) -> None:
    """WCS should be populated when valid WCS keywords are in the header."""
    frame = load_fits(synthetic_fits_with_wcs)
    assert frame.wcs is not None
    assert frame.wcs.has_celestial


def test_load_fits_wcs_round_trip(synthetic_fits_with_wcs: Path) -> None:
    """Pixel-to-sky-to-pixel round-trip should be accurate to sub-pixel level."""
    frame = load_fits(synthetic_fits_with_wcs)
    wcs = frame.wcs
    assert wcs is not None

    x_in, y_in = 64.0, 64.0
    sky = wcs.pixel_to_world(x_in, y_in)
    x_out, y_out = wcs.world_to_pixel(sky)
    assert abs(x_out - x_in) < 0.5
    assert abs(y_out - y_in) < 0.5


# ---------------------------------------------------------------------------
# load_fits — error cases
# ---------------------------------------------------------------------------

def test_load_fits_missing_file_raises(tmp_path: Path) -> None:
    """load_fits must raise FitsLoadError for a nonexistent path."""
    with pytest.raises(FitsLoadError, match="File not found"):
        load_fits(tmp_path / "does_not_exist.fits")


def test_load_fits_not_a_fits_file_raises(tmp_path: Path) -> None:
    """load_fits must raise FitsLoadError when the file is not valid FITS."""
    bad_file = tmp_path / "bad.fits"
    bad_file.write_bytes(b"this is not a fits file at all")
    with pytest.raises(FitsLoadError):
        load_fits(bad_file)


# ---------------------------------------------------------------------------
# debayer
# ---------------------------------------------------------------------------

def test_debayer_output_shape() -> None:
    """debayer should return an (H, W, 3) array from a 2-D input."""
    raw = np.random.default_rng(0).uniform(0, 65535, (64, 64)).astype(np.float32)
    rgb = debayer(raw, pattern="RGGB")
    assert rgb.shape == (64, 64, 3)


def test_debayer_output_dtype_float32() -> None:
    """debayer output must be float32."""
    raw = np.zeros((32, 32), dtype=np.uint16)
    rgb = debayer(raw, "RGGB")
    assert rgb.dtype == np.float32


def test_debayer_raises_on_3d_input() -> None:
    """debayer must raise ValueError for non-2D input."""
    with pytest.raises(ValueError, match="2-D"):
        debayer(np.zeros((10, 10, 3), dtype=np.float32))


def test_debayer_raises_on_unknown_pattern() -> None:
    """debayer must raise ValueError for an unrecognised Bayer pattern."""
    with pytest.raises(ValueError, match="Unknown Bayer pattern"):
        debayer(np.zeros((32, 32), dtype=np.float32), pattern="XYZW")


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_debayer_all_patterns(pattern: str) -> None:
    """debayer should succeed for all four supported Bayer patterns."""
    raw = np.random.default_rng(1).uniform(0, 1000, (64, 64)).astype(np.float32)
    rgb = debayer(raw, pattern=pattern)
    assert rgb.shape == (64, 64, 3)
