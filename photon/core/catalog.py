"""Remote catalog query stubs.

Wraps ``astroquery`` services for SIMBAD, Gaia DR3, and the AAVSO Variable
Star Index (VSX via VizieR).  Each function is a pure data-fetching routine
with no Qt imports.  All calls should be dispatched through a worker so the
main thread is never blocked.

Catalog routing:
- SIMBAD  → ``astroquery.simbad.Simbad``
- Gaia DR3 → ``astroquery.gaia.Gaia`` (table ``gaiadr3.gaia_source``)
- VSX      → ``astroquery.vizier.Vizier`` (catalog ``B/vsx/vsx``)
"""

from __future__ import annotations

import astropy.units as u
from astropy.coordinates import SkyCoord


class CatalogQueryError(Exception):
    """Raised when a remote catalog query fails."""


def query_simbad(
    coord: SkyCoord,
    radius: u.Quantity = 5 * u.arcmin,
) -> object:
    """Query SIMBAD for objects within *radius* of *coord*.

    Parameters
    ----------
    coord : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius : astropy.units.Quantity
        Angular search radius.  Default is 5 arcmin.

    Returns
    -------
    astropy.table.Table
        SIMBAD result table with at minimum the columns ``MAIN_ID``, ``RA``,
        ``DEC``, ``OTYPE``, and ``FLUX_V``.  Returns an empty table when no
        sources are found.

    Raises
    ------
    CatalogQueryError
        On network error or malformed response from the SIMBAD TAP service.
    """
    raise NotImplementedError(
        "query_simbad() is not yet implemented. "
        "It will call astroquery.simbad.Simbad().query_region(coord, radius)."
    )


def query_gaia_dr3(
    coord: SkyCoord,
    radius: u.Quantity = 5 * u.arcmin,
    row_limit: int = 500,
) -> object:
    """Query Gaia DR3 for sources within *radius* of *coord*.

    Parameters
    ----------
    coord : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius : astropy.units.Quantity
        Angular search radius.  Default is 5 arcmin.
    row_limit : int
        Maximum number of rows to return.  Default is 500.

    Returns
    -------
    astropy.table.Table
        Gaia DR3 ``gaia_source`` table with astrometric and photometric
        columns for all sources within the search cone.

    Raises
    ------
    CatalogQueryError
        On network error, TAP query failure, or job timeout.
    """
    raise NotImplementedError(
        "query_gaia_dr3() is not yet implemented. "
        "It will use astroquery.gaia.Gaia with MAIN_GAIA_TABLE='gaiadr3.gaia_source' "
        "and Gaia.cone_search_async(coord, radius)."
    )


def query_vsx(
    coord: SkyCoord,
    radius: u.Quantity = 10 * u.arcmin,
) -> object:
    """Query the AAVSO Variable Star Index (VSX) via VizieR.

    Parameters
    ----------
    coord : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius : astropy.units.Quantity
        Angular search radius.  Default is 10 arcmin.

    Returns
    -------
    astropy.table.Table
        VSX result table (VizieR catalog ``B/vsx/vsx``) containing variable
        star designations, types, periods, and magnitudes near *coord*.
        Returns an empty table when no variables are found.

    Raises
    ------
    CatalogQueryError
        On network error or VizieR query failure.
    """
    raise NotImplementedError(
        "query_vsx() is not yet implemented. "
        "It will use astroquery.vizier.Vizier(catalog='B/vsx/vsx') "
        "and call query_region(coord, radius)."
    )
