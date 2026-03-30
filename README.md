# Photon — Astrophotography Science Analysis

[![CI](https://github.com/JamesMaloney7754/Project-Photon/actions/workflows/ci.yml/badge.svg)](https://github.com/JamesMaloney7754/Project-Photon/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/JamesMaloney7754/Project-Photon?label=download)](https://github.com/JamesMaloney7754/Project-Photon/releases/latest)

A desktop application for amateur and professional astronomers that brings a
complete astrophotography science pipeline into a single GUI: load calibrated
FITS sequences, plate-solve against Astrometry.net, cross-match sources with
SIMBAD / Gaia DR3 / VSX, perform differential aperture photometry, build light
curves, and extract exoplanet transit parameters — no Python knowledge required
for end users.

---

## Download & Run (Windows)

1. Go to the [Releases page](../../releases)
2. Download the latest `Photon-vX.X.X-windows.zip`
3. Extract the zip to any folder (e.g. Desktop or Documents)
4. Open the extracted `Photon` folder
5. Double-click **`Photon.exe`**
6. **First launch only — Windows SmartScreen warning:** if Windows shows
   "Windows protected your PC", click **More info** → **Run anyway**.
   This is expected for apps without a paid code signing certificate and is
   safe to dismiss.

---

## For Developers (running from source)

### Prerequisites

- Python 3.11 or later
- pip

### Install and run

```bash
# Clone the repository
git clone https://github.com/JamesMaloney7754/Project-Photon.git
cd Project-Photon

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Launch the application
photon
```

### Run the test suite

```bash
pytest
```

### Build the Windows distributable locally

```batch
scripts\build_windows.bat
```

The script generates `dist\Photon-local-build.zip` containing the
self-contained `Photon\` folder.

---

## Triggering a Release

Push a version tag and GitHub Actions builds and uploads the zip automatically:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The [release workflow](.github/workflows/release.yml) runs on
`windows-latest`, builds with PyInstaller, and attaches
`Photon-v0.2.0-windows.zip` to a new GitHub Release.

Tags containing `-beta` or `-alpha` (e.g. `v0.2.0-beta`) are automatically
marked as pre-releases.
