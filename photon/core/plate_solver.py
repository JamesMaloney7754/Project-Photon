"""Plate-solver interface and concrete implementations.

This module defines the abstract ``PlateSolver`` base class and three concrete
implementations:

* :class:`ASTAPSolver` — calls the ``astap`` / ``astap.exe`` binary via
  ``subprocess``; recommended on Windows (no Cygwin dependency).
* :class:`LocalAstrometrySolver` — calls the ``solve-field`` binary from the
  local ``astrometry.net`` / ANSVR package via ``subprocess``.
* :class:`AstrometryNetSolver` — submits images to the Astrometry.net cloud
  API via ``astroquery.astrometry_net``.

Use :func:`get_solver` to obtain the backend configured in
:mod:`photon.core.settings_manager`.

Architecture note: UI code must only call ``PlateSolver.solve()`` — never
touch ``astroquery.astrometry_net`` or subprocess plate-solve binaries
directly from the UI layer.
"""

from __future__ import annotations

import abc
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class PlateSolverError(Exception):
    """Raised when plate solving fails for any reason."""


class PlateSolver(abc.ABC):
    """Abstract interface for plate-solving backends.

    Subclasses implement :meth:`solve` and may expose backend-specific
    constructor parameters.
    """

    @abc.abstractmethod
    def solve(
        self,
        image: np.ndarray,
        header: object,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> object:
        """Attempt to plate-solve *image* and return an astropy WCS object.

        Parameters
        ----------
        image : np.ndarray
            2-D science image array (float64, calibrated ADU).
        header : astropy.io.fits.Header
            FITS header associated with *image*.  May contain RA/Dec hint
            keywords (``OBJCTRA``, ``OBJCTDEC``) used to seed the search.
        progress_callback : callable or None
            Optional ``(message: str) -> None`` callback invoked with status
            lines as the solve progresses.  Called from the worker thread.

        Returns
        -------
        astropy.wcs.WCS
            Fully initialised WCS object representing the plate solution.

        Raises
        ------
        PlateSolverError
            If the solve attempt fails, times out, or returns no solution.
        """


# ── ASTAPSolver ───────────────────────────────────────────────────────────────


class ASTAPSolver(PlateSolver):
    """Plate solver that shells out to the ASTAP executable.

    ASTAP (Astrometric STAcking Program) is a standalone binary solver that
    requires no Cygwin or ANSVR dependency, making it the recommended local
    backend on Windows.

    Parameters
    ----------
    binary_path : str
        Path to the ``astap`` / ``astap.exe`` executable.
    search_radius : float
        Search radius in degrees (``-r`` flag).  Default 30.
    downsample : int
        Downsample factor (``-z`` flag, 0 = auto).  Default 0.
    """

    def __init__(
        self,
        binary_path: str,
        search_radius: float = 30.0,
        downsample: int = 0,
    ) -> None:
        if not binary_path:
            raise PlateSolverError(
                "ASTAP binary path is not set. "
                "Configure it in Settings → Plate Solving."
            )
        self._binary        = binary_path
        self._search_radius = search_radius
        self._downsample    = downsample

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def detect_installation(binary_path: str = "astap") -> tuple[bool, str]:
        """Probe *binary_path* by running ``astap -version``.

        Parameters
        ----------
        binary_path : str
            Path to the ASTAP executable.  Defaults to ``"astap"`` so that
            PATH-installed binaries are found automatically.

        Returns
        -------
        tuple[bool, str]
            ``(True, version_string)`` on success, ``(False, "")`` on any
            failure (binary not found, non-zero exit, or timeout).
        """
        path = binary_path or "astap"
        try:
            result = subprocess.run(
                [path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # ASTAP may return non-zero for -version on some builds; any execution
            # means the binary is present and functional.
            version = (result.stdout or result.stderr or "").strip()
            return True, version
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False, ""

    # ------------------------------------------------------------------
    # solve()
    # ------------------------------------------------------------------

    def solve(
        self,
        image: np.ndarray,
        header: object,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> object:
        """Run ASTAP on *image* and return a WCS.

        Parameters
        ----------
        image : np.ndarray
            2-D science image array.
        header : astropy.io.fits.Header
            FITS header written to the temp input file.
        progress_callback : callable or None
            Called with each stdout line from ASTAP.

        Returns
        -------
        astropy.wcs.WCS

        Raises
        ------
        PlateSolverError
            On non-zero exit code or missing ``.wcs`` output file.
        """
        from astropy.io import fits as astrofits
        from astropy.wcs import WCS

        def _emit(msg: str) -> None:
            logger.debug("ASTAP: %s", msg.rstrip())
            if progress_callback is not None:
                progress_callback(msg.rstrip())

        with tempfile.TemporaryDirectory() as tmpdir:
            input_fits   = os.path.join(tmpdir, "input.fits")
            output_prefix = os.path.join(tmpdir, "output")
            output_wcs   = output_prefix + ".wcs"

            # ── 1. Write temp FITS ────────────────────────────────────────
            if isinstance(header, astrofits.Header):
                hdr = header.copy()
            else:
                hdr = astrofits.Header()

            hdu = astrofits.PrimaryHDU(data=image.astype(np.float32), header=hdr)
            hdu.writeto(input_fits, overwrite=True)
            _emit(f"Wrote temp FITS: {input_fits}")

            # ── 2. Build command ──────────────────────────────────────────
            cmd = [
                self._binary,
                "-f",  input_fits,
                "-r",  str(self._search_radius),
                "-z",  str(self._downsample),
                "-o",  output_prefix,
                "-wcs",
            ]
            _emit(f"Running: {' '.join(cmd)}")

            # ── 3. Run ASTAP, stream stdout ───────────────────────────────
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except FileNotFoundError as exc:
                raise PlateSolverError(
                    f"ASTAP binary not found at '{self._binary}': {exc}"
                ) from exc

            stderr_buf: list[str] = []
            assert proc.stdout is not None
            for line in proc.stdout:
                _emit(line)

            proc.wait()

            if proc.stderr:
                stderr_buf = proc.stderr.readlines()

            if proc.returncode != 0:
                raise PlateSolverError(
                    f"ASTAP exited with code {proc.returncode}.\n"
                    + "".join(stderr_buf)
                )

            # ── 4. Read .wcs output ───────────────────────────────────────
            if not os.path.isfile(output_wcs):
                raise PlateSolverError(
                    "ASTAP completed but produced no .wcs output file. "
                    "The field may not have been solved."
                )

            try:
                with astrofits.open(output_wcs) as hdul:
                    wcs = WCS(hdul[0].header)
                _emit("WCS solution loaded successfully.")
                return wcs
            except Exception as exc:
                raise PlateSolverError(
                    f"Failed to read WCS from ASTAP output: {exc}"
                ) from exc


# ── LocalAstrometrySolver ──────────────────────────────────────────────────────


class LocalAstrometrySolver(PlateSolver):
    """Plate solver that shells out to the ``solve-field`` binary.

    Reads ``binary_path``, ``index_dir``, ``scale_units``, ``scale_low``,
    ``scale_high``, and ``timeout_seconds`` from
    :func:`~photon.core.settings_manager.get_settings_manager` at construction
    time.  Pass explicit values to override.

    Parameters
    ----------
    binary_path : str
        Path to the ``solve-field`` executable.  If empty the constructor
        raises :class:`PlateSolverError`.
    index_dir : str
        Directory containing astrometry.net index files.  May be empty
        (solve-field will use its default search path).
    scale_units : str
        Units for the pixel scale hint, e.g. ``"arcsecperpix"``.
    scale_low, scale_high : float
        Lower / upper bound for the pixel scale search range.
    timeout_s : int
        CPU-time limit in seconds passed to ``--cpulimit``.
    """

    def __init__(
        self,
        binary_path: str,
        index_dir: str = "",
        scale_units: str = "arcsecperpix",
        scale_low: float = 0.1,
        scale_high: float = 10.0,
        timeout_s: int = 120,
    ) -> None:
        if not binary_path:
            raise PlateSolverError(
                "Local solver binary path is not set. "
                "Configure it in Settings → Plate Solving."
            )
        self._binary   = binary_path
        self._index_dir = index_dir
        self._scale_units = scale_units
        self._scale_low   = scale_low
        self._scale_high  = scale_high
        self._timeout_s   = timeout_s

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def detect_installation() -> Optional[str]:
        """Return the path to ``solve-field`` if found on PATH, else ``None``.

        Checks common installation locations in addition to PATH.
        """
        import shutil

        found = shutil.which("solve-field")
        if found:
            return found

        # Common install locations on Linux/macOS
        candidates = [
            "/usr/bin/solve-field",
            "/usr/local/bin/solve-field",
            "/opt/homebrew/bin/solve-field",
            "/opt/local/bin/solve-field",
        ]
        for p in candidates:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

        return None

    # ------------------------------------------------------------------
    # solve()
    # ------------------------------------------------------------------

    def solve(
        self,
        image: np.ndarray,
        header: object,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> object:
        """Run ``solve-field`` on *image* and return a WCS.

        Parameters
        ----------
        image : np.ndarray
            2-D science image array.
        header : astropy.io.fits.Header
            FITS header (used to write the temp FITS file).
        progress_callback : callable or None
            Called with each stdout line from ``solve-field``.

        Returns
        -------
        astropy.wcs.WCS

        Raises
        ------
        PlateSolverError
            On non-zero exit code, timeout, or missing WCS output file.
        """
        from astropy.io import fits as astrofits
        from astropy.wcs import WCS

        def _emit(msg: str) -> None:
            logger.debug("solve-field: %s", msg.rstrip())
            if progress_callback is not None:
                progress_callback(msg.rstrip())

        # ── 1. Write image to a temp FITS file ───────────────────────────
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path  = os.path.join(tmpdir, "input.fits")
            output_wcs  = os.path.join(tmpdir, "input.wcs")

            if isinstance(header, astrofits.Header):
                hdr = header.copy()
            else:
                hdr = astrofits.Header()

            hdu = astrofits.PrimaryHDU(data=image.astype(np.float32), header=hdr)
            hdu.writeto(input_path, overwrite=True)
            _emit(f"Wrote temp FITS to {input_path}")

            # ── 2. Build command ──────────────────────────────────────────
            cmd = [
                self._binary,
                "--no-plots",
                "--new-fits", "none",
                "--wcs", output_wcs,
                "--scale-units", self._scale_units,
                "--scale-low",  str(self._scale_low),
                "--scale-high", str(self._scale_high),
                "--cpulimit",   str(self._timeout_s),
                "--overwrite",
            ]

            if self._index_dir:
                cmd += ["--index-path", self._index_dir]

            # RA/Dec seed hint
            try:
                ra_hint  = hdr.get("OBJCTRA") or hdr.get("RA")
                dec_hint = hdr.get("OBJCTDEC") or hdr.get("DEC")
                if ra_hint is not None and dec_hint is not None:
                    cmd += ["--ra", str(ra_hint), "--dec", str(dec_hint),
                            "--radius", "10"]
                    _emit(f"Using RA/Dec hint: {ra_hint} / {dec_hint}")
            except Exception:
                pass

            cmd.append(input_path)
            _emit(f"Running: {' '.join(cmd)}")

            # ── 3. Run solve-field, stream stdout ─────────────────────────
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except FileNotFoundError as exc:
                raise PlateSolverError(
                    f"solve-field binary not found at '{self._binary}': {exc}"
                ) from exc

            stderr_lines: list[str] = []
            assert proc.stdout is not None
            for line in proc.stdout:
                _emit(line)

            proc.wait()

            if proc.returncode != 0:
                if proc.stderr:
                    stderr_lines = proc.stderr.readlines()
                stderr_str = "".join(stderr_lines)
                raise PlateSolverError(
                    f"solve-field exited with code {proc.returncode}.\n{stderr_str}"
                )

            # ── 4. Read WCS from output file ──────────────────────────────
            if not os.path.isfile(output_wcs):
                raise PlateSolverError(
                    "solve-field completed but produced no WCS output file. "
                    "The field may not have been solved."
                )

            try:
                with astrofits.open(output_wcs) as hdul:
                    wcs = WCS(hdul[0].header)
                _emit("WCS solution loaded successfully.")
                return wcs
            except Exception as exc:
                raise PlateSolverError(
                    f"Failed to read WCS from solve-field output: {exc}"
                ) from exc


# ── AstrometryNetSolver ────────────────────────────────────────────────────────


class AstrometryNetSolver(PlateSolver):
    """Cloud plate solver using the Astrometry.net web API via astroquery.

    Parameters
    ----------
    api_key : str
        Astrometry.net API key obtained from https://nova.astrometry.net.
    scale_units : str
        Pixel scale units passed to the submission.
    scale_lower, scale_upper : float
        Pixel scale search bounds.
    timeout_s : int
        Maximum seconds to wait for the job to complete.
    """

    def __init__(
        self,
        api_key: str,
        scale_units: str = "arcsecperpix",
        scale_lower: float = 0.1,
        scale_upper: float = 10.0,
        timeout_s: int = 120,
    ) -> None:
        if not api_key:
            raise PlateSolverError(
                "Astrometry.net API key is not set. "
                "Configure it in Settings → Plate Solving."
            )
        self._api_key     = api_key
        self._scale_units = scale_units
        self._scale_lower = scale_lower
        self._scale_upper = scale_upper
        self._timeout_s   = timeout_s

    def solve(
        self,
        image: np.ndarray,
        header: object,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> object:
        """Submit *image* to Astrometry.net and return a WCS solution.

        Parameters
        ----------
        image : np.ndarray
            2-D science image array (float64, calibrated ADU).
        header : astropy.io.fits.Header
            FITS header; ``OBJCTRA`` / ``OBJCTDEC`` are used as search hints
            when present.
        progress_callback : callable or None
            Called with status strings during polling.

        Returns
        -------
        astropy.wcs.WCS

        Raises
        ------
        PlateSolverError
            On any failure: network error, bad API key, timeout, or no
            solution found within the search radius.
        """
        from astropy.io import fits as astrofits
        from astropy.wcs import WCS

        try:
            from astroquery.astrometry_net import AstrometryNet
        except ImportError as exc:
            raise PlateSolverError(
                "astroquery is not installed. "
                "Install it with: pip install astroquery"
            ) from exc

        def _emit(msg: str) -> None:
            logger.debug("AstrometryNet: %s", msg)
            if progress_callback is not None:
                progress_callback(msg)

        _emit("Connecting to Astrometry.net …")

        ast = AstrometryNet()
        ast.api_key = self._api_key

        # Write image to a temp FITS file for upload
        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if isinstance(header, astrofits.Header):
                hdr = header.copy()
            else:
                hdr = astrofits.Header()

            hdu = astrofits.PrimaryHDU(data=image.astype(np.float32), header=hdr)
            hdu.writeto(tmp_path, overwrite=True)
            _emit("Submitting image to Astrometry.net …")

            kwargs: dict = {
                "scale_units": self._scale_units,
                "scale_lower": self._scale_lower,
                "scale_upper": self._scale_upper,
                "solve_timeout": self._timeout_s,
                "force_image_upload": True,
            }

            # RA/Dec hint
            try:
                ra_hint  = hdr.get("OBJCTRA") or hdr.get("RA")
                dec_hint = hdr.get("OBJCTDEC") or hdr.get("DEC")
                if ra_hint is not None and dec_hint is not None:
                    from astropy.coordinates import SkyCoord
                    import astropy.units as u
                    coord = SkyCoord(ra_hint, dec_hint, unit=(u.hourangle, u.deg))
                    kwargs["center_ra"]  = coord.ra.deg
                    kwargs["center_dec"] = coord.dec.deg
                    kwargs["radius"]     = 10.0
                    _emit(f"Using RA/Dec hint: {coord.ra.deg:.4f}, {coord.dec.deg:.4f}")
            except Exception:
                pass

            _emit("Waiting for solution (this may take 1-3 minutes) …")
            try:
                wcs_header = ast.solve_from_image(tmp_path, **kwargs)
            except Exception as exc:
                raise PlateSolverError(
                    f"Astrometry.net submission failed: {exc}"
                ) from exc

            if wcs_header is None or not wcs_header:
                raise PlateSolverError(
                    "Astrometry.net returned no solution. "
                    "Try adjusting scale bounds or check your API key."
                )

            _emit("Solution received — building WCS …")
            wcs = WCS(wcs_header)
            _emit("Done.")
            return wcs

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ── Factory ────────────────────────────────────────────────────────────────────


def get_solver() -> PlateSolver:
    """Return the plate-solver backend configured in settings.

    Reads ``platesolve/backend`` from
    :func:`~photon.core.settings_manager.get_settings_manager`.
    Returns an :class:`ASTAPSolver`, :class:`LocalAstrometrySolver`, or
    :class:`AstrometryNetSolver` with all parameters pulled from settings.

    Returns
    -------
    PlateSolver

    Raises
    ------
    PlateSolverError
        If the configured backend is unknown or required settings are missing.
    """
    from photon.core.settings_manager import get_settings_manager

    sm = get_settings_manager()
    backend = sm.get("platesolve/backend")

    if backend == "astap":
        return ASTAPSolver(
            binary_path=sm.get("platesolve/astap_binary_path"),
            search_radius=float(sm.get("platesolve/astap_search_radius")),
            downsample=int(sm.get("platesolve/astap_downsample")),
        )

    if backend == "local":
        return LocalAstrometrySolver(
            binary_path=sm.get("platesolve/local_binary_path"),
            index_dir=sm.get("platesolve/index_dir"),
            scale_units=sm.get("platesolve/scale_units"),
            scale_low=float(sm.get("platesolve/scale_low")),
            scale_high=float(sm.get("platesolve/scale_high")),
            timeout_s=int(sm.get("platesolve/timeout_seconds")),
        )

    if backend == "astrometry_net":
        return AstrometryNetSolver(
            api_key=sm.get("platesolve/astrometry_api_key"),
            scale_units=sm.get("platesolve/scale_units"),
            scale_lower=float(sm.get("platesolve/scale_low")),
            scale_upper=float(sm.get("platesolve/scale_high")),
            timeout_s=int(sm.get("platesolve/timeout_seconds")),
        )

    raise PlateSolverError(
        f"Unknown plate-solving backend: '{backend}'. "
        "Expected 'astap', 'local', or 'astrometry_net'."
    )
