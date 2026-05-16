# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Photon — one-directory build (fast startup).

One-directory mode is used instead of one-file because the science stack
(astropy, scipy, matplotlib) contains many large data files.  One-file mode
would extract all of them to a temp directory on every launch, adding 5-10 s
cold-start latency.  One-directory ships as a folder and starts immediately.

To build:
    python scripts/generate_icon.py   # creates assets/icon.ico
    pyinstaller photon.spec --clean --noconfirm
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


def safe_copy_metadata(pkg):
    """Return copy_metadata result, or [] if the package isn't installed."""
    try:
        return copy_metadata(pkg)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Data files — package resource files + .dist-info metadata directories
#
# copy_metadata() copies the .dist-info folder into the bundle so that
# importlib.metadata.version() / requires() calls succeed at runtime.
# photutils uses importlib.metadata on import to read its own version and
# optional-dependency lists; without the .dist-info folder the import raises
# PackageNotFoundError before any detection code can run.
# ---------------------------------------------------------------------------
datas = (
    collect_data_files('astropy') +
    collect_data_files('astroquery') +
    collect_data_files('matplotlib') +
    collect_data_files('photutils') +
    collect_data_files('lightkurve') +
    safe_copy_metadata('photutils') +
    safe_copy_metadata('astropy') +
    safe_copy_metadata('numpy') +
    safe_copy_metadata('scipy') +
    safe_copy_metadata('matplotlib') +
    safe_copy_metadata('astroquery') +
    safe_copy_metadata('lightkurve') +
    safe_copy_metadata('packaging') +
    safe_copy_metadata('importlib_metadata')
)

# ---------------------------------------------------------------------------
# Hidden imports — modules that PyInstaller's static analysis misses
# ---------------------------------------------------------------------------
hiddenimports = [
    # Astropy
    'astropy',
    'astropy.io.fits',
    'astropy.io.fits.hdu',
    'astropy.io.fits.hdu.compressed',
    'astropy.wcs',
    'astropy.wcs.utils',
    'astropy.coordinates',
    'astropy.time',
    'astropy.stats',
    'astropy.visualization',
    'astropy.utils.data',
    'astropy.units',
    'astropy.constants',
    # Photutils — detection submodule (missed by static analysis)
    'photutils',
    'photutils.aperture',
    'photutils.background',
    'photutils.detection',
    'photutils.detection.core',
    'photutils.detection.daofinder',
    'photutils.detection.irafstarfinder',
    'photutils.detection.peakfinder',
    'photutils.utils._optional_deps',
    'photutils.utils._progress_bars',
    'photutils.utils.depths',
    # importlib.metadata — needed by photutils version checks
    'importlib.metadata',
    'importlib_metadata',
    # Astroquery
    'astroquery',
    'astroquery.simbad',
    'astroquery.gaia',
    'astroquery.vizier',
    'astroquery.astrometry_net',
    # Scipy internals commonly missed by PyInstaller
    'scipy.special._ufuncs',
    'scipy.special.cython_special',
    'scipy._lib.messagestream',
    'scipy.integrate',
    'scipy.optimize',
    # Matplotlib Qt backend
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_agg',
    # Lightkurve
    'lightkurve',
    # Encoding / misc
    'encodings.utf_8',
    'encodings.ascii',
    'pkg_resources.py2_warn',
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ['photon/__main__.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavyweight unused modules to reduce bundle size
        'tkinter',
        'PyQt5',
        'PyQt6',
        'wx',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Photon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX compression disabled — UPX-packed binaries trigger Windows Defender
    # false positives on apps that embed numpy/scipy native extensions.
    upx=False,
    console=False,     # no terminal window on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Photon',    # output directory inside dist/
)
