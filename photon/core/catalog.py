"""Remote catalog query functions.

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

import concurrent.futures
import logging

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table

logger = logging.getLogger(__name__)

# Default per-query network timeout (seconds)
_QUERY_TIMEOUT = 30


class CatalogQueryError(Exception):
    """Raised when a remote catalog query fails."""


# ── SIMBAD ─────────────────────────────────────────────────────────────────────


def query_simbad(
    center: SkyCoord,
    radius_arcmin: float,
) -> Table:
    """Query SIMBAD for objects within *radius_arcmin* of *center*.

    Parameters
    ----------
    center : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius_arcmin : float
        Angular search radius in arcminutes.

    Returns
    -------
    astropy.table.Table
        Table with columns ``ra``, ``dec``, ``name``, ``type``, ``vmag``.
        Returns an empty table on no results, timeout, or network error.
    """
    try:
        from astroquery.simbad import Simbad

        simbad = Simbad()
        simbad.reset_votable_fields()
        simbad.add_votable_fields("otype", "flux(V)", "sptype")

        radius = radius_arcmin * u.arcmin
        result = simbad.query_region(center, radius=radius)

        if result is None or len(result) == 0:
            return _empty_simbad_table()

        # Normalise to standard column names
        out = Table()
        out["ra"]   = result["RA"].filled("") if hasattr(result["RA"], "filled") else result["RA"]
        out["dec"]  = result["DEC"].filled("") if hasattr(result["DEC"], "filled") else result["DEC"]
        out["name"] = result["MAIN_ID"].filled("") if hasattr(result["MAIN_ID"], "filled") else result["MAIN_ID"]
        out["type"] = result["OTYPE"].filled("") if hasattr(result["OTYPE"], "filled") else result["OTYPE"]

        # V-mag column may be missing or masked
        if "FLUX_V" in result.colnames:
            raw_vmag = result["FLUX_V"]
            if hasattr(raw_vmag, "filled"):
                raw_vmag = raw_vmag.filled(float("nan"))
            out["vmag"] = raw_vmag
        else:
            import numpy as np
            out["vmag"] = [float("nan")] * len(result)

        logger.debug("SIMBAD: %d objects within %.1f arcmin", len(out), radius_arcmin)
        return out

    except Exception as exc:
        logger.warning("SIMBAD query failed: %s", exc)
        return _empty_simbad_table()


def _empty_simbad_table() -> Table:
    import numpy as np
    return Table(
        names=["ra", "dec", "name", "type", "vmag"],
        dtype=[str, str, str, str, float],
    )


# ── Gaia DR3 ───────────────────────────────────────────────────────────────────


def query_gaia_dr3(
    center: SkyCoord,
    radius_arcmin: float,
    row_limit: int = 500,
) -> Table:
    """Query Gaia DR3 for sources within *radius_arcmin* of *center*.

    Parameters
    ----------
    center : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius_arcmin : float
        Angular search radius in arcminutes.
    row_limit : int
        Maximum number of rows to return.  Default is 500.

    Returns
    -------
    astropy.table.Table
        Table with columns ``source_id``, ``ra``, ``dec``,
        ``phot_g_mean_mag``, ``parallax``, ``pmra``, ``pmdec``.
        Returns an empty table on failure.
    """
    try:
        from astroquery.gaia import Gaia

        Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"
        Gaia.ROW_LIMIT = row_limit

        radius = (radius_arcmin * u.arcmin).to(u.deg)
        job = Gaia.cone_search_async(center, radius=radius)
        result = job.get_results()

        if result is None or len(result) == 0:
            return _empty_gaia_table()

        keep = ["source_id", "ra", "dec", "phot_g_mean_mag", "parallax", "pmra", "pmdec"]
        cols = [c for c in keep if c in result.colnames]
        out = result[cols]
        logger.debug("Gaia DR3: %d sources within %.1f arcmin", len(out), radius_arcmin)
        return out

    except Exception as exc:
        logger.warning("Gaia DR3 query failed: %s", exc)
        return _empty_gaia_table()


def _empty_gaia_table() -> Table:
    import numpy as np
    return Table(
        names=["source_id", "ra", "dec", "phot_g_mean_mag", "parallax", "pmra", "pmdec"],
        dtype=[str, float, float, float, float, float, float],
    )


# ── VSX ────────────────────────────────────────────────────────────────────────


def query_vsx(
    center: SkyCoord,
    radius_arcmin: float,
) -> Table:
    """Query the AAVSO Variable Star Index (VSX) via VizieR.

    Parameters
    ----------
    center : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius_arcmin : float
        Angular search radius in arcminutes.

    Returns
    -------
    astropy.table.Table
        Table with columns ``ra``, ``dec``, ``name``, ``type``,
        ``period``, ``magnitude``.
        Returns an empty table when no variables are found.
    """
    try:
        from astroquery.vizier import Vizier

        viz = Vizier(
            catalog="B/vsx/vsx",
            columns=["Name", "RAJ2000", "DEJ2000", "Type", "Period", "max"],
        )
        viz.ROW_LIMIT = -1  # no row limit
        radius = radius_arcmin * u.arcmin
        result_list = viz.query_region(center, radius=radius)

        if not result_list or len(result_list) == 0:
            return _empty_vsx_table()

        raw = result_list[0]
        if len(raw) == 0:
            return _empty_vsx_table()

        out = Table()
        # RA/Dec columns in VSX are "RAJ2000" and "DEJ2000"
        ra_col  = "RAJ2000" if "RAJ2000" in raw.colnames else raw.colnames[0]
        dec_col = "DEJ2000" if "DEJ2000" in raw.colnames else raw.colnames[1]
        out["ra"]  = raw[ra_col]
        out["dec"] = raw[dec_col]

        def _masked_str(col: str) -> list:
            if col in raw.colnames:
                vals = raw[col]
                return [str(v) if v is not None else "" for v in
                        (vals.filled("") if hasattr(vals, "filled") else vals)]
            return [""] * len(raw)

        def _masked_float(col: str) -> list:
            import numpy as np
            if col in raw.colnames:
                vals = raw[col]
                if hasattr(vals, "filled"):
                    vals = vals.filled(float("nan"))
                return list(vals)
            return [float("nan")] * len(raw)

        out["name"]      = _masked_str("Name")
        out["type"]      = _masked_str("Type")
        out["period"]    = _masked_float("Period")
        out["magnitude"] = _masked_float("max")

        logger.debug("VSX: %d variables within %.1f arcmin", len(out), radius_arcmin)
        return out

    except Exception as exc:
        logger.warning("VSX query failed: %s", exc)
        return _empty_vsx_table()


def _empty_vsx_table() -> Table:
    import numpy as np
    return Table(
        names=["ra", "dec", "name", "type", "period", "magnitude"],
        dtype=[float, float, str, str, float, float],
    )


# ── Combined query ─────────────────────────────────────────────────────────────


def query_all_catalogs(
    center: SkyCoord,
    radius_arcmin: float,
) -> dict[str, Table]:
    """Query all three catalogs in parallel with a per-query timeout.

    Calls :func:`query_simbad`, :func:`query_gaia_dr3`, and :func:`query_vsx`
    concurrently using a thread pool.  Each query is limited to
    ``_QUERY_TIMEOUT`` seconds; timed-out queries return an empty table.

    Parameters
    ----------
    center : astropy.coordinates.SkyCoord
        Sky position to search around.
    radius_arcmin : float
        Angular search radius in arcminutes.

    Returns
    -------
    dict
        ``{"simbad": Table, "gaia": Table, "vsx": Table}``
    """
    def _safe(fn, *args) -> Table:
        try:
            return fn(*args)
        except Exception as exc:
            logger.warning("%s failed: %s", fn.__name__, exc)
            return Table()

    futures: dict[str, concurrent.futures.Future] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures["simbad"] = pool.submit(_safe, query_simbad,    center, radius_arcmin)
        futures["gaia"]   = pool.submit(_safe, query_gaia_dr3,  center, radius_arcmin)
        futures["vsx"]    = pool.submit(_safe, query_vsx,       center, radius_arcmin)

        results: dict[str, Table] = {}
        for key, fut in futures.items():
            try:
                results[key] = fut.result(timeout=_QUERY_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.warning("Catalog query '%s' timed out after %ds", key, _QUERY_TIMEOUT)
                results[key] = Table()
            except Exception as exc:
                logger.warning("Catalog query '%s' raised: %s", key, exc)
                results[key] = Table()

    return results
