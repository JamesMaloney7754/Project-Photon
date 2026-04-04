"""Catalog query worker — off-thread wrapper for :func:`photon.core.catalog.query_all_catalogs`.

Usage::

    worker = CatalogWorker(wcs=session.wcs, radius_arcmin=15.0)
    worker.signals.result.connect(self._on_catalog_results)
    worker.signals.error.connect(self._on_catalog_error)
    QThreadPool.globalInstance().start(worker)
"""

from __future__ import annotations

import logging

from photon.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class CatalogWorker(BaseWorker):
    """Off-thread worker that calls :func:`~photon.core.catalog.query_all_catalogs`.

    Derives the field center from the WCS object by projecting the image
    centre pixel to sky coordinates.

    Parameters
    ----------
    wcs : astropy.wcs.WCS
        Plate solution used to compute the field centre.
    radius_arcmin : float
        Query radius passed to each catalog function.
    """

    def __init__(self, wcs: object, radius_arcmin: float = 15.0) -> None:
        super().__init__()
        self._wcs = wcs
        self._radius_arcmin = radius_arcmin

    def execute(self) -> dict:
        """Run all three catalog queries and return a results dict.

        Returns
        -------
        dict
            ``{"simbad": Table, "gaia": Table, "vsx": Table}``
        """
        from astropy.coordinates import SkyCoord

        from photon.core.catalog import query_all_catalogs

        wcs = self._wcs

        # Derive field centre from WCS
        try:
            px = getattr(wcs, "pixel_shape", None)
            if px:
                nx, ny = px[1] or 256, px[0] or 256
            else:
                nx, ny = 256, 256
            sky = wcs.pixel_to_world(nx / 2, ny / 2)
            center = SkyCoord(sky.ra, sky.dec)
        except Exception as exc:
            raise RuntimeError(f"Could not determine field centre from WCS: {exc}") from exc

        logger.debug(
            "CatalogWorker: querying %.1f arcmin around %s",
            self._radius_arcmin, center,
        )
        return query_all_catalogs(center, self._radius_arcmin)
