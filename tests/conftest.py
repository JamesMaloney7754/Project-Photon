"""pytest fixtures for the Photon test suite."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Synthetic FITS fixtures (no network required)
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthetic_fits_path(tmp_path: Path) -> Path:
    """Write a minimal synthetic FITS file to a temp directory and return its path.

    The file contains a 64×64 float32 image with a simple gradient pattern,
    plus basic FITS keywords.  No WCS is included so tests can separately
    verify WCS-absent behaviour.

    Returns
    -------
    Path
        Path to the written ``.fits`` file.
    """
    from astropy.io import fits

    data = np.arange(64 * 64, dtype=np.float32).reshape(64, 64)
    hdu = fits.PrimaryHDU(data)
    hdu.header["OBJECT"] = "TEST_TARGET"
    hdu.header["EXPTIME"] = 120.0
    hdu.header["INSTRUME"] = "SyntheticCam"
    hdu.header["DATE-OBS"] = "2024-06-15T22:30:00.0"
    hdu.header["FILTER"] = "V"

    fits_path = tmp_path / "synthetic.fits"
    hdu.writeto(fits_path)
    return fits_path


@pytest.fixture()
def synthetic_fits_with_wcs(tmp_path: Path) -> Path:
    """Write a minimal FITS file with a simple TAN WCS to a temp directory.

    Returns
    -------
    Path
        Path to the written ``.fits`` file.
    """
    from astropy.io import fits

    rng = np.random.default_rng(42)
    data = rng.uniform(100, 1000, (128, 128)).astype(np.float32)
    hdu = fits.PrimaryHDU(data)
    hdu.header["NAXIS"] = 2
    hdu.header["NAXIS1"] = 128
    hdu.header["NAXIS2"] = 128
    hdu.header["CTYPE1"] = "RA---TAN"
    hdu.header["CTYPE2"] = "DEC--TAN"
    hdu.header["CRPIX1"] = 64.0
    hdu.header["CRPIX2"] = 64.0
    hdu.header["CRVAL1"] = 83.8221  # Orion Nebula RA
    hdu.header["CRVAL2"] = -5.3911  # Orion Nebula Dec
    hdu.header["CD1_1"] = -0.000277778
    hdu.header["CD1_2"] = 0.0
    hdu.header["CD2_1"] = 0.0
    hdu.header["CD2_2"] = 0.000277778
    hdu.header["DATE-OBS"] = "2024-06-15T23:00:00.0"

    fits_path = tmp_path / "synthetic_wcs.fits"
    hdu.writeto(fits_path)
    return fits_path


@pytest.fixture()
def synthetic_fits_sequence(tmp_path: Path) -> list[Path]:
    """Write a sequence of 3 synthetic FITS files with DATE-OBS headers.

    All frames are 64×64 with varying sky backgrounds.

    Returns
    -------
    list[Path]
        Ordered list of paths to the written ``.fits`` files.
    """
    from astropy.io import fits

    paths = []
    rng = np.random.default_rng(99)
    for i in range(3):
        data = rng.uniform(200 + i * 50, 800 + i * 50, (64, 64)).astype(np.float32)
        hdu = fits.PrimaryHDU(data)
        hdu.header["OBJECT"] = "TEST_TARGET"
        hdu.header["EXPTIME"] = 60.0
        hdu.header["FILTER"] = "R"
        hdu.header["DATE-OBS"] = f"2024-06-15T2{i}:00:00.0"
        p = tmp_path / f"frame_{i:03d}.fits"
        hdu.writeto(p)
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Real FITS sample via astropy remote data (cached)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_fits_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Download a small real FITS image using astropy's data cache.

    Uses ``astropy.utils.data.download_file`` with ``cache=True`` so the file
    is only downloaded once per machine.  The test is automatically skipped if
    the network is unavailable.

    Returns
    -------
    Path
        Local path to the cached FITS file.
    """
    pytest.importorskip("astropy")
    try:
        from astropy.utils.data import download_file

        url = "https://fits.gsfc.nasa.gov/samples/WFPC2u5780205r_c0fx.fits"
        cached = download_file(url, cache=True, timeout=30)
        return Path(cached)
    except Exception as exc:
        pytest.skip(f"Could not download sample FITS: {exc}")
