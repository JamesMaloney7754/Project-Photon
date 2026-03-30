# CLAUDE.md — Architecture Decisions and Conventions

## Project Overview

Photon is a desktop application for astrophotography science analysis.  It enables
amateur and professional astronomers to load calibrated FITS images, plate-solve them
against the Astrometry.net cloud service, cross-match sources against SIMBAD / Gaia DR3 /
VSX catalogs, perform aperture photometry, build light curves, and extract exoplanet
transit parameters — all within a single PySide6 GUI.

---

## Architecture Principles

1. **Core/UI separation is absolute.**  `photon/core/` and `photon/utils/` have zero Qt
   imports.  All science logic lives there.  Test it headlessly with plain `pytest` — no
   display required.  `photon/workers/` is permitted Qt imports because workers *are* Qt
   infrastructure (`QRunnable`, `QObject`, `Signal`), but they must never contain science
   logic — delegate all computation to `photon/core/` functions.

2. **Never block the main thread.**  All I/O and computation (FITS loading, plate solving,
   photometry, catalog queries) must be dispatched via `QThreadPool` using the worker
   pattern in `photon/workers/base_worker.py`.  The UI emits a signal to start work and
   receives results via signals.  If you find yourself calling a blocking function from a
   slot connected to a button, stop and use a worker instead.

3. **PhotonSession is the single source of truth.**  All loaded state — frames, WCS,
   catalog matches, photometry results — lives on a `PhotonSession` instance owned by
   `MainWindow`.  Modules receive what they need as arguments; they do not hold state
   themselves and must not store references to the session.

4. **Plate solving is behind an interface.**  `PlateSolver` is an abstract base class in
   `photon/core/plate_solver.py`.  Concrete implementations: `AstrometryNetSolver`
   (cloud, via astroquery).  Future: local `astrometry-net` binary via subprocess.
   Never call astrometry APIs directly from UI code.

5. **Catalog queries use astroquery exclusively.**  SIMBAD via `astroquery.simbad`,
   Gaia DR3 via `astroquery.gaia`, variable star catalog via `astroquery.vizier`
   (VizieR catalog `B/vsx/vsx`).  Each service is wrapped in its own function in
   `photon/core/catalog.py`.  Dispatch all catalog calls through workers.

6. **Stretch and display are separate from science.**  `photon/utils/stretch.py` handles
   `astropy.visualization` interval and stretch transforms for display only.
   Science computations (photometry, astrometry) always use raw calibrated counts.
   Never pass a stretched array to any function in `photon/core/`.

---

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `photon/__init__.py` | Package version declaration. |
| `photon/__main__.py` | Application entry point; constructs `QApplication` and `MainWindow`. |
| `photon/core/session.py` | `PhotonSession` and `FitsFrame` dataclasses — the application state model. |
| `photon/core/fits_loader.py` | Synchronous FITS file loading and validation; returns `FitsFrame`. |
| `photon/core/plate_solver.py` | Abstract `PlateSolver` interface and `AstrometryNetSolver` implementation. |
| `photon/core/catalog.py` | SIMBAD, Gaia DR3, and VSX catalog query functions. |
| `photon/core/photometry.py` | Aperture photometry using `photutils`. |
| `photon/core/transit.py` | Transit parameter extraction from detrended light curves. |
| `photon/ui/main_window.py` | `QMainWindow` subclass; owns `PhotonSession`; orchestrates workers and panels. |
| `photon/ui/fits_canvas.py` | Matplotlib-in-Qt widget for interactive FITS image display. |
| `photon/ui/light_curve_panel.py` | Placeholder `QWidget` for photometric light curve display. |
| `photon/ui/transit_panel.py` | Placeholder `QWidget` for transit model fit display. |
| `photon/workers/base_worker.py` | `BaseWorker(QRunnable)` with `WorkerSignals`; subclass for every async task. |
| `photon/workers/fits_worker.py` | Off-thread worker that calls `fits_loader.load_fits`. |
| `photon/utils/stretch.py` | `astropy.visualization` stretch/interval helpers for display normalisation. |
| `tests/conftest.py` | pytest fixtures: synthetic FITS, WCS FITS, cached remote sample. |
| `tests/test_fits_loader.py` | Full test coverage for `fits_loader` happy paths and error cases. |
| `tests/test_session.py` | Placeholder for `PhotonSession` tests. |
| `tests/test_photometry.py` | Placeholder for `photometry` tests. |

---

## Coding Conventions

- **Type-hint all public function signatures.**  Use `from __future__ import annotations`
  at the top of every module so forward references work without quotes.
- **Docstrings on all public classes and functions** using NumPy/Napoleon style.
- **No bare `except:` clauses** — always catch specific exceptions (e.g. `except OSError`).
  Use `except Exception` only as a last resort in worker `run()` methods.
- **Log using the stdlib `logging` module.**  The UI shows status in the status bar via
  `MainWindow._set_status()`, never via `print()`.  Use `logger = logging.getLogger(__name__)`
  at module level.
- **All physical constants via `astropy.constants`; all units via `astropy.units`.**
  Never hardcode unit conversion factors (e.g. write `1 * u.arcsec` not `4.8e-6`).
- **Qt signals use `snake_case` names** (e.g. `pixel_clicked`, not `pixelClicked`).
  Worker result signals carry typed payloads (`Signal(object)` for complex types).
- **Imports:** standard library first, then third-party, then local `photon.*`.  Separate
  groups with a blank line.  Use `ruff --select I` to enforce import order.
- **Line length:** 100 characters (enforced by `ruff`).

---

## Testing Conventions

- **Tests for `photon/core/` and `photon/utils/` must not require a display** (no Qt).
  Run with plain `pytest` in any headless CI environment.
- **Tests for `photon/ui/` use `pytest-qt`** and the `qtbot` fixture provided by
  `pytest-qt`.  Mark them with `@pytest.mark.qt` or rely on `pytest-qt` auto-detection.
- **Use `astropy.utils.data.download_file` with `cache=True`** for sample FITS data in
  session-scoped fixtures.  Do not bundle binary FITS files in the repository.
- **Keep fixtures in `tests/conftest.py`.**  Fixtures shared between test files must
  live there, not in individual test modules.
- **Test file naming:** `test_<module_name>.py` mirroring the source structure.

---

## Future Work Placeholders (do not implement yet)

- **One-click AAVSO submission** via AAVSO WebObs API (`https://www.aavso.org/webobs`).
- **Exoplanet Transit Database (ETD) submission** — upload times and depths to ETD.
- **Local `astrometry-net` plate solver backend** — shell out to the `solve-field` binary
  via `subprocess` in a new `LocalAstrometryNetSolver` that implements `PlateSolver`.
- **Session save/load** — JSON serialisation of `PhotonSession` (excluding raw pixel data;
  store file paths instead and reload on open).
