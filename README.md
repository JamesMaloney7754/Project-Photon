# Photon — Astrophotography Science Analysis

Photon is a desktop application for amateur and professional astronomers that
brings a complete astrophotography science pipeline into a single PySide6 GUI:
load sequences of calibrated FITS images, plate-solve them against the
Astrometry.net cloud API, cross-match sources against SIMBAD, Gaia DR3, and
the AAVSO Variable Star Index, perform differential aperture photometry, build
multi-frame light curves, and extract exoplanet transit parameters — all
without leaving the application.

## Prerequisites

- Python 3.11 or later
- pip

## Quickstart

```bash
pip install -e ".[dev]"
photon
pytest
```
