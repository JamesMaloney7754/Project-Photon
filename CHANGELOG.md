# Changelog

All notable changes to Photon will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - Initial Release

### Added
- FITS image sequence loader (`load_fits_sequence`, `get_observation_times`,
  `summarize_sequence`)
- Basic Qt window with FITS display canvas (Matplotlib-in-Qt)
- Observatory Glass UI design system (`photon/ui/theme.py`)
- Drag-and-drop FITS file and folder loading with recursive directory glob
- Pipeline stepper navigation widget (Load → Solve → Photometry → Transit)
- Session sidebar with two-line file list and sequence metadata grid
- Context-sensitive inspector panel with one page per pipeline step
- Frame scrubber and keyboard navigation shortcuts (← → Space 1–4 Ctrl+O Ctrl+Q)
- Empty-state drop-zone canvas with telescope icon
- Abstract `PlateSolver` interface and `AstrometryNetSolver` stub
- Catalog query stubs (SIMBAD, Gaia DR3, VSX via VizieR)
- Aperture photometry stubs (`photutils`-based)
- Transit detection and fitting stubs
- Windows PyInstaller build pipeline (`photon.spec`)
- GitHub Actions release workflow (tag → zip → GitHub Release)
- CI workflow (pytest on every push / PR to main)
