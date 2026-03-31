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
| `photon/ui/background_widget.py` | `BackgroundWidget` — radial gradient deep space background; central widget of MainWindow. |
| `photon/ui/glass_panel.py` | `GlassPanel` — base class for floating glass-effect panels (sidebar, inspector). |
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

---

## UI Design System — Deep Field

All visual decisions are encoded in `photon/ui/theme.py`.  This section documents
the rules that all UI contributors must follow.

### Astronomical Inspiration

The Deep Field visual language draws from observatory instrument panels and deep
space imagery: a near-black background with subtle violet nebula bloom (the
`BackgroundWidget` radial gradient), glass panels that float over the starfield,
and gold accent text for science values — reminiscent of instrument readouts.

### Two-Accent System

| Accent | Color | Semantic use |
|--------|-------|-------------|
| **Violet** (`Colors.VIOLET` `#7c3aed`) | Actions, navigation, active states, selection |
| **Gold** (`Colors.GOLD` / `Colors.TEXT_GOLD`) | Science data values, measurements, coordinates |

Use violet for anything the user *does*; use gold for anything the app *shows*.

### Color Tokens

| Token | Value | Use |
|-------|-------|-----|
| `Colors.BASE_CENTER` | `#0a0f1a` | Radial gradient centre of background |
| `Colors.BASE_EDGE` | `#060810` | Radial gradient edge of background |
| `Colors.GLASS_SURFACE` | `#111827` | Solid fill for glass panels |
| `Colors.SURFACE` | `#111827` | General panel surface |
| `Colors.SURFACE_ALT` | `#1a2235` | Hover states, secondary surfaces |
| `Colors.SURFACE_RAISED` | `#1f2d45` | Elevated surfaces (menus, tooltips) |
| `Colors.BORDER` | `#1e2d45` | All 1 px dividers and outlines |
| `Colors.BORDER_SUBTLE` | `#152032` | Very faint separators between data rows |
| `Colors.VIOLET` | `#7c3aed` | Primary actions, active stepper, selection |
| `Colors.VIOLET_BRIGHT` | `#8b5cf6` | Hover state for violet elements |
| `Colors.VIOLET_GLOW` | `rgba(124,58,237,40)` | Glow ring / aura effects |
| `Colors.GOLD` | `#f59e0b` | Science data accent background tints |
| `Colors.SUCCESS` | `#10b981` | Completed steps, loaded indicator |
| `Colors.TEXT_PRIMARY` | `#f0f4ff` | Body text (slightly blue-tinted white) |
| `Colors.TEXT_SECONDARY` | `#6b7fa3` | Labels, captions, metadata keys |
| `Colors.TEXT_DISABLED` | `#2d3f5c` | Disabled text, inactive elements |
| `Colors.TEXT_GOLD` | `#fbbf24` | Science values, coordinates, measurements |
| `Colors.CANVAS_BG` | `#04060d` | Matplotlib figure background |

**Rule: no hardcoded hex values anywhere in `photon/ui/` except `theme.py`.**
For QPainter code that requires `QColor(r, g, b, a)` integers, add a comment
referencing the Colors token (e.g. `# Colors.VIOLET`).

### Glass Panel Base Class

`GlassPanel` (`photon/ui/glass_panel.py`) is the base class for all floating
panels.  It paints:
1. A rounded rect (radius 12px) filled with `QColor(17, 24, 39, 220)`.
2. A `QLinearGradient` border stroke (bright top-left → dim bottom-right).
3. A subtle inner top-edge highlight (top 30% clip).

`SessionSidebar` and `InspectorPanel` both inherit `GlassPanel` instead of
`QWidget`.  Do not add `setStyleSheet` background colors to GlassPanel subclasses —
the paint override handles the background.

### BackgroundWidget

`BackgroundWidget` (`photon/ui/background_widget.py`) is set as the `QMainWindow`
central widget.  It paints two radial gradients: the main deep-navy-to-black base,
and a subtle violet bloom in the upper-right quadrant composited with
`CompositionMode_Screen`.  The `QSplitter` sits inside it with 8px margins so the
gradient is visible around the glass panels.

### Three-Zone Layout Architecture

```
┌─────────────────────────────────────────────────────┐
│  Top bar (56 px) — hexagon logo + pill stepper + ⚙  │
├──────────────┬──────────────────────┬───────────────┤
│  Session     │                      │  Inspector    │
│  Sidebar     │    FitsCanvas        │  Panel        │
│  (260 px)    │    (flexible)        │  (260 px)     │
│  GlassPanel  │    (no border)       │  GlassPanel   │
├──────────────┴──────────────────────┴───────────────┤
│  Bottom bar (44 px) — dot · status · scrubber       │
└─────────────────────────────────────────────────────┘
```

### Pipeline Stepper — Floating Pill

`PipelineStepperWidget` is a fixed 480×52px pill that floats in the top bar,
centered with `AlignCenter`.  It has:
- A `glow_radius` Property animated 6→10px looping with SineCurve (1200ms).
  This creates a breathing pulse on the active step circle.
- A `bg_opacity` Property animated on hover (180→210, 150ms).
- Drop shadow: concentric low-opacity ellipses below the pill.

Steps are marked complete via `set_step_complete(index)` — completed steps show
a painted QPainter checkmark, not a text "✓".

### Inspector Panel — DataRow Widgets

`InspectorPanel` uses `DataRow(QWidget)` for every key-value pair instead of
`QLabel`.  `DataRow` paints itself with a `flash` Property (float 0.0–1.0) that
interpolates the value color from `TEXT_GOLD` → white on each call to
`set_value()`, driven by a 300ms `QPropertyAnimation`.

The inspector title label fades out (150ms) and fades in (150ms) when
`set_step()` is called.

### Animation Inventory

| Widget | Property | Duration | Trigger |
|--------|----------|----------|---------|
| `PipelineStepperWidget` | `glow_radius` (int) | 1200ms loop | Always (breathing pulse) |
| `PipelineStepperWidget` | `bg_opacity` (int) | 150ms | enter/leaveEvent |
| `DataRow` | `flash` (float) | 300ms | `set_value()` call |
| `InspectorPanel._title_lbl` | `opacity` via QGraphicsOpacityEffect | 150ms out + 150ms in | `set_step()` |
| `FitsCanvas._mpl_wrapper` | `opacity` via QGraphicsOpacityEffect | 400ms | First `display_frame()` |
| `BottomBarWidget._progress` | `opacity` via QGraphicsOpacityEffect | 200ms | `show_progress()` |
| `_PulseDot` | `dot_alpha` (int) | 1500ms loop | Always (loaded/unloaded dot) |
| `MainWindow` panels | `opacity` via QGraphicsOpacityEffect | 300ms staggered | `showEvent` launch |

**Rules:**
- All animations use `QPropertyAnimation` — no manual `QTimer`-driven alpha
  interpolation except for continuous effects (`_scan_offset` shimmer,
  `_PulseDot` breathing).
- Remove `QGraphicsOpacityEffect` from launch-animated panels after they
  complete (via `QTimer.singleShot`) — opacity effects interfere with child
  widget painting if left attached.
- Custom animatable properties are defined with `Property(type, getter, setter)`
  as class variables (PySide6 style), not `@Property` decorator chains.

### Drag-and-Drop — Files and Folders

`FitsCanvas.dropEvent` accepts:
- Individual `*.fits` / `*.fit` files.
- Directories — recursively globbed with `Path.rglob("*.fits")`.
- Mixed drops combining both.

While a drag is active (`_drag_active = True`), `FitsCanvas.paintEvent` overlays
a violet tint (`rgba(124,58,237,40)`) and dashed violet border over the entire
canvas.

Results are deduplicated, sorted, and emitted as a `list[Path]` via
`files_dropped`.  `MainWindow` wires this signal to `_load_paths`, so the full
loading flow runs identically to a file-dialog open.

---

## Build & Release Pipeline

### How a release works

1. A developer pushes a version tag: `git tag v0.2.0 && git push origin v0.2.0`
2. `.github/workflows/release.yml` triggers on `windows-latest`.
3. The workflow installs deps, generates the icon, runs PyInstaller, and zips
   `dist\Photon\` into `Photon-v0.2.0-windows.zip`.
4. `softprops/action-gh-release` creates the GitHub Release and attaches the zip.
5. Tags containing `-beta` or `-alpha` are automatically marked as pre-releases.

### App icon

`assets/icon.ico` is **generated, not committed to git**.  Before building,
always run:

```bash
python scripts/generate_icon.py
```

This produces a multi-resolution ICO (16 → 256 px) with a violet hexagon and
the letter "P" on a dark navy background.  Requires `Pillow>=10.0`.

### Why one-directory mode (not one-file)

PyInstaller's `--onefile` mode extracts the entire bundle to a temp directory
on every launch.  With astropy + scipy + matplotlib that extraction takes 5–10 s.
`COLLECT` (one-directory) ships as a folder and starts immediately because
files are already on disk.

### Why UPX is disabled

UPX compression on binaries that embed numpy / scipy native extensions triggers
Windows Defender false-positive alerts.  `upx=False` is set in both `EXE` and
`COLLECT` blocks of `photon.spec`.

### Debugging a broken build

When `console=False` hides crash output, run the EXE from a terminal to see
import errors:

```bat
cd dist\Photon
Photon.exe
```

Any missing hidden import will print a `ModuleNotFoundError` there.  Add the
missing module to the `hiddenimports` list in `photon.spec` and rebuild.

### SmartScreen warning

End users see "Windows protected your PC" on first launch because the app is
unsigned.  The fix: click **More info** → **Run anyway**.  This is documented
in both the README and the GitHub Release body.

Future: obtain a code signing certificate (Sectigo or DigiCert) and sign
`Photon.exe` post-build to eliminate the warning entirely.
