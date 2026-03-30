"""Catalog query stubs.

Wraps astroquery services for SIMBAD, Gaia DR3, and VSX (variable stars).
Each function is a pure data-fetching routine; no Qt imports.
"""

from __future__ import annotations

import logging
from typing import Any

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table

logger = logging.getLogger(__name__)


class CatalogQueryError(Exception):
    """Raised when a remote catalog query fails."""


# ---------------------------------------------------------------------------
# SIMBAD
# ---------------------------------------------------------------------------

def query_simbad(
    coord: SkyCoord,
    radius: u.Quantity = 5 * u.arcmin,
) -> Table:
    """Query SIMBAD for objects within *radius* of *coord*.

    Parameters
    ----------
    coord : SkyCoord
        Sky position to search around.
    radius : astropy.units.Quantity
        Search radius (angular).

    Returns
    -------
    astropy.table.Table
        SIMBAD result table with columns ``MAIN_ID``, ``RA``, ``DEC``,
        ``OTYPE``, and ``V``.

    Raises
    ------
    CatalogQueryError
        On network error or empty/malformed response.
    """
    try:
        from astroquery.simbad import Simbad  # type: ignore[import]
    except ImportError as exc:
        raise CatalogQueryError("astroquery is not installed.") from exc

    simbad = Simbad()
    simbad.add_votable_fields("otype", "flux(V)")
    logger.info("Querying SIMBAD at %s r=%s", coord.to_string("hmsdms"), radius)
    try:
        result: Table | None = simbad.query_region(coord, radius=radius)
    except Exception as exc:
        raise CatalogQueryError(f"SIMBAD query failed: {exc}") from exc

    if result is None or len(result) == 0:
        logger.debug("SIMBAD returned no results.")
        return Table()

    return result


# ---------------------------------------------------------------------------
# Gaia DR3
# ---------------------------------------------------------------------------

def query_gaia_dr3(
    coord: SkyCoord,
    radius: u.Quantity = 5 * u.arcmin,
    row_limit: int = 500,
) -> Table:
    """Query Gaia DR3 for sources within *radius* of *coord*.

    Parameters
    ----------
    coord : SkyCoord
        Sky position to search around.
    radius : astropy.units.Quantity
        Search radius (angular).
    row_limit : int
        Maximum number of rows to return.

    Returns
    -------
    astropy.table.Table
        Gaia DR3 result table.

    Raises
    ------
    CatalogQueryError
        On network error or query failure.
    """
    try:
        from astroquery.gaia import Gaia  # type: ignore[import]
    except ImportError as exc:
        raise CatalogQueryError("astroquery is not installed.") from exc

    Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"
    Gaia.ROW_LIMIT = row_limit
    logger.info("Querying Gaia DR3 at %s r=%s", coord.to_string("hmsdms"), radius)
    try:
        job = Gaia.cone_search_async(coord, radius=radius)
        result: Table = job.get_results()
    except Exception as exc:
        raise CatalogQueryError(f"Gaia DR3 query failed: {exc}") from exc

    logger.debug("Gaia DR3 returned %d rows.", len(result))
    return result


# ---------------------------------------------------------------------------
# VSX (Variable Star Index via VizieR)
# ---------------------------------------------------------------------------

def query_vsx(
    coord: SkyCoord,
    radius: u.Quantity = 10 * u.arcmin,
) -> Table:
    """Query the AAVSO Variable Star Index (VSX) via VizieR.

    Parameters
    ----------
    coord : SkyCoord
        Sky position to search around.
    radius : astropy.units.Quantity
        Search radius (angular).

    Returns
    -------
    astropy.table.Table
        VSX result table with variable star entries near *coord*.

    Raises
    ------
    CatalogQueryError
        On network error or query failure.
    """
    try:
        from astroquery.vizier import Vizier  # type: ignore[import]
    except ImportError as exc:
        raise CatalogQueryError("astroquery is not installed.") from exc

    vizier = Vizier(catalog="B/vsx/vsx", row_limit=-1)
    logger.info("Querying VSX at %s r=%s", coord.to_string("hmsdms"), radius)
    try:
        result_list = vizier.query_region(coord, radius=radius)
    except Exception as exc:
        raise CatalogQueryError(f"VSX query failed: {exc}") from exc

    if not result_list or len(result_list) == 0:
        logger.debug("VSX returned no results.")
        return Table()

    return result_list[0]
