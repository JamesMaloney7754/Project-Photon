"""Worker that loads a FITS file off the main thread.

Dispatches :func:`photon.core.fits_loader.load_fits` via the
:class:`~photon.workers.base_worker.BaseWorker` pattern so the UI thread is
never blocked by disk I/O.
"""

from __future__ import annotations

from pathlib import Path

from photon.core.fits_loader import load_fits
from photon.core.session import FitsFrame
from photon.workers.base_worker import BaseWorker


class FitsWorker(BaseWorker):
    """Load a single FITS file asynchronously.

    On success, ``signals.result`` is emitted with a :class:`~photon.core.session.FitsFrame`.
    On failure, ``signals.error`` is emitted with the exception details.

    Parameters
    ----------
    path : str | Path
        Path to the FITS file to load.

    Examples
    --------
    ::

        worker = FitsWorker("/data/image.fits")
        worker.signals.result.connect(self._on_fits_loaded)
        worker.signals.error.connect(self._on_fits_error)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, path: str | Path) -> None:
        super().__init__(path)

    def run_task(self, path: str | Path) -> FitsFrame:  # type: ignore[override]
        """Load *path* and return a :class:`~photon.core.session.FitsFrame`.

        Parameters
        ----------
        path : str | Path
            Path to the FITS file.

        Returns
        -------
        FitsFrame
            Fully loaded frame with data, header, and optional WCS.

        Raises
        ------
        photon.core.fits_loader.FitsLoadError
            If the file cannot be loaded.
        """
        return load_fits(path)
