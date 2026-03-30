@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  Photon — Windows build script
echo ============================================================

:: ── 1. Check Python is available ─────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ and add it to PATH.
    exit /b 1
)
echo [1/7] Python OK

:: ── 2. Install package + dev dependencies ────────────────────────────────
echo [2/7] Installing package and dev dependencies...
pip install -e ".[dev]"
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)

:: ── 3. Install Pillow ─────────────────────────────────────────────────────
echo [3/7] Installing Pillow...
pip install Pillow pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install Pillow or PyInstaller.
    exit /b 1
)

:: ── 4. Generate icon ──────────────────────────────────────────────────────
echo [4/7] Generating app icon...
python scripts\generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    exit /b 1
)

:: ── 5. Clean previous build artifacts ────────────────────────────────────
echo [5/7] Cleaning previous build output...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
echo     Cleaned.

:: ── 6. Run PyInstaller ────────────────────────────────────────────────────
echo [6/7] Running PyInstaller...
pyinstaller photon.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed. Check the output above for details.
    exit /b 1
)

:: ── 7. Verify EXE was produced ───────────────────────────────────────────
if not exist "dist\Photon\Photon.exe" (
    echo ERROR: dist\Photon\Photon.exe was not created. Build failed.
    exit /b 1
)
echo [7/7] Build verified: dist\Photon\Photon.exe exists.

:: ── 8. Zip the distribution folder ───────────────────────────────────────
echo Packaging into zip...
python -c "
import zipfile, pathlib, sys
src = pathlib.Path('dist/Photon')
out = pathlib.Path('dist/Photon-local-build.zip')
if not src.is_dir():
    print('ERROR: dist/Photon directory not found.', file=sys.stderr)
    sys.exit(1)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in src.rglob('*'):
        if f.is_file():
            zf.write(f, f.relative_to(src.parent))
print(f'Zipped {sum(1 for _ in src.rglob(\"*\") if _.is_file())} files.')
"
if errorlevel 1 (
    echo ERROR: Zip creation failed.
    exit /b 1
)

echo.
echo ============================================================
echo  Build complete: dist\Photon-local-build.zip
echo ============================================================
endlocal
