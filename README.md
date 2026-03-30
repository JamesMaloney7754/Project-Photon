# Photon — Astrophotography Science Analysis

Photon is a desktop application that enables astronomers to load calibrated FITS images,
plate-solve them via the Astrometry.net cloud API, cross-match sources against SIMBAD,
Gaia DR3, and the AAVSO Variable Star Index (VSX), perform aperture photometry, and
extract exoplanet transit parameters — all within a clean PySide6 GUI that keeps science
logic strictly separated from the user interface.

## Quickstart

```bash
# 1. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install Photon and its dependencies
pip install -e ".[dev]"

# 3. Run the application
photon

# 4. Run the test suite
pytest
```
