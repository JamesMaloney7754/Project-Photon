"""pytest fixtures for the Photon test suite."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from photon.core.fits_loader import load_fits_sequence


# ---------------------------------------------------------------------------
# Remote sample FITS (session-scoped, cached to disk)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_fits_path() -> Path:
    """Download a real FITS file via astropy's cache and return its path.

    Uses ``astropy.utils.data.download_file`` with ``cache=True`` so the file
    is only fetched from the network once per machine.  The test is skipped
    automatically if the network is unavailable.

    Returns
    -------
    Path
        Local path to the cached FITS file.
    """
    from astropy.utils.data import download_file

    url = "https://fits.gsfc.nasa.gov/samples/FOSy19g0309t_c2f.fits"
    try:
        cached = download_file(url, cache=True, timeout=30)
    except Exception as exc:
        pytest.skip(f"Could not download sample FITS: {exc}")
    return Path(cached)


@pytest.fixture(scope="session")
def sample_fits_sequence(sample_fits_path: Path) -> tuple[np.ndarray, list]:
    """Load a 3-frame sequence by repeating *sample_fits_path* three times.

    Simulates a multi-frame sequence without requiring multiple distinct files.
    Skipped automatically if the network sample is unavailable.

    Returns
    -------
    tuple[np.ndarray, list]
        ``(image_stack, headers)`` as returned by
        :func:`photon.core.fits_loader.load_fits_sequence`.
    """
    return load_fits_sequence([sample_fits_path, sample_fits_path, sample_fits_path])


# ---------------------------------------------------------------------------
# Synthetic FITS fixtures (no network required)
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthetic_fits_path(tmp_path: Path) -> Path:
    """Write a minimal 64×64 synthetic FITS file and return its path.

    Includes ``OBJECT``, ``EXPTIME``, ``FILTER``, and ``DATE-OBS`` keywords.

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
def synthetic_fits_sequence(tmp_path: Path) -> list[Path]:
    """Write a sequence of 3 synthetic 64×64 FITS files and return their paths.

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
