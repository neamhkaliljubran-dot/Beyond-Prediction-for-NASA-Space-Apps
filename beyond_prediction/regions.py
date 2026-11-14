"""Indonesian territory mask and reproducible rainfall regions on the IMERG grid.

Territory: Natural Earth 1:10m Admin-0 countries (v5.1.1, public domain),
feature ADM0_A3 == "IDN". For each 0.1-degree IMERG cell we estimate the
fraction of the cell covered by the Indonesia polygon by testing an n x n grid
of sub-points (default 10 x 10 = 100 points per cell).

Cell inclusion rule (documented, adjustable):
    indonesia_fraction >= 0.5  AND  IMERG water_pct < 50
i.e. the cell must be mostly Indonesian land according to Natural Earth AND
mostly land according to the IMERG land/sea mask. Coastal cells and small
islands that fail either test are excluded; counts are reported.

Regions: k-means on the *shape* of each cell's climatological annual cycle
(12 monthly means, each standardised to zero mean and unit variance across
months). This follows the idea of grouping by annual-cycle similarity used by
Aldrian & Susanto (2003) but is NOT a reproduction of their station-based
regions A/B/C; derived regions are labelled R1..Rk.
"""

from __future__ import annotations

import numpy as np

NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
MIN_COUNTRY_FRAC = 0.5
MAX_WATER_PCT = 50.0


def cell_fraction(geom, lon: np.ndarray, lat: np.ndarray, n: int = 10,
                  step: float = 0.1) -> np.ndarray:
    """Fraction of each (lat, lon) cell inside ``geom`` via n x n sub-sampling."""
    import shapely

    shapely.prepare(geom)
    off = (np.arange(n) + 0.5) / n * step - step / 2
    frac = np.zeros((lat.size, lon.size), dtype=np.float32)
    LON, LAT = np.meshgrid(lon, lat)
    for dy in off:
        for dx in off:
            frac += shapely.contains_xy(geom, LON + dx, LAT + dy)
    return frac / (n * n)


def load_country(shp_path, adm0_a3: str = "IDN"):
    import shapefile
    from shapely.geometry import shape

    r = shapefile.Reader(str(shp_path))
    for sr in r.iterShapeRecords():
        if sr.record["ADM0_A3"] == adm0_a3:
            return shape(sr.shape.__geo_interface__)
    raise ValueError(f"{adm0_a3} not found in {shp_path}")


def include_mask(country_frac: np.ndarray, water_pct: np.ndarray) -> np.ndarray:
    return (country_frac >= MIN_COUNTRY_FRAC) & (water_pct < MAX_WATER_PCT)


def standardized_cycle(clim: np.ndarray) -> np.ndarray:
    """clim: (12, ncell) monthly means -> (ncell, 12) z-scored annual cycles."""
    x = clim.T.astype(np.float64)
    sd = x.std(axis=1, keepdims=True)
    sd[sd == 0] = np.nan
    return (x - x.mean(axis=1, keepdims=True)) / sd


def kmeans(x: np.ndarray, k: int, seed: int, n_init: int = 20, iters: int = 300):
    """Plain k-means (Euclidean). Returns labels sorted so region 1 is largest."""
    from sklearn.cluster import KMeans

    km = KMeans(n_clusters=k, n_init=n_init, max_iter=iters, random_state=seed).fit(x)
    order = np.argsort(-np.bincount(km.labels_, minlength=k))
    remap = np.empty(k, dtype=int)
    remap[order] = np.arange(k)
    return remap[km.labels_], km.cluster_centers_[order], km.inertia_


def adjusted_rand(a: np.ndarray, b: np.ndarray) -> float:
    from sklearn.metrics import adjusted_rand_score

    return float(adjusted_rand_score(a, b))


def area_weighted_mean(field: np.ndarray, weights: np.ndarray, sel: np.ndarray):
    """Area-weighted mean over selected cells, ignoring NaN; also returns valid fraction."""
    v = field[sel]
    w = weights[sel]
    ok = ~np.isnan(v)
    if not ok.any():
        return np.nan, 0.0
    return float(np.sum(v[ok] * w[ok]) / np.sum(w[ok])), float(w[ok].sum() / w.sum())
