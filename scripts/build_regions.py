"""Stage D checks + Stage E regionalization from the cached IMERG box subsets.

1. Verify the cache: 1998-01..2025-09 continuous, one file per month, hours in
   each averaging period == calendar days x 24, units already checked at subset time.
2. Build the Indonesian territory mask (Natural Earth 1:10m, IDN) on the IMERG grid
   and combine it with the IMERG land/sea mask.
3. Derive k regions from the standardised climatological annual cycle (k-means),
   with silhouette scores for k=2..6 and stability checks (seeds, year bootstrap).
4. Write area-weighted regional monthly totals (mm/month), no gap filling.

Usage: python scripts/build_regions.py [--k 3]
"""

from __future__ import annotations

import argparse
import calendar
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from beyond_prediction import regions as rg  # noqa: E402
from beyond_prediction.provenance import DATA, sha256_bytes, utc_now, write_json  # noqa: E402

CACHE = DATA / "interim" / "imerg_box"
NE_DIR = DATA / "raw" / "naturalearth"
START, END = "1998-01", "2025-09"
CLIM_YEARS = (1998, 2024)  # complete calendar years only, so each month has equal weight
SEED = 20261114


def get_natural_earth() -> tuple[Path, dict]:
    z = NE_DIR / "ne_10m_admin_0_countries.zip"
    if not z.exists():
        r = requests.get(rg.NE_URL, timeout=120)
        r.raise_for_status()
        NE_DIR.mkdir(parents=True, exist_ok=True)
        z.write_bytes(r.content)
    raw = z.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        zf.extractall(NE_DIR)
        version = zf.read("ne_10m_admin_0_countries.VERSION.txt").decode().strip()
    return NE_DIR / "ne_10m_admin_0_countries.shp", {
        "url": rg.NE_URL, "sha256": sha256_bytes(raw), "version": version,
        "feature": "ADM0_A3 == IDN", "licence": "public domain (Natural Earth)"}


def load_cache() -> tuple[pd.PeriodIndex, np.ndarray, np.ndarray, dict]:
    months = pd.period_range(START, END, freq="M")
    files = {p.stem: p for p in CACHE.glob("[0-9]*.npz")}
    missing = [m.strftime("%Y-%m") for m in months if m.strftime("%Y-%m") not in files]
    extra = sorted(set(files) - {m.strftime("%Y-%m") for m in months})
    stack, hours, bad_hours = [], [], []
    for m in months:
        key = m.strftime("%Y-%m")
        if key not in files:
            continue
        d = np.load(files[key])
        h = float(d["hours"])
        exp = calendar.monthrange(m.year, m.month)[1] * 24
        if abs(h - exp) > 1e-6:
            bad_hours.append((key, h, exp))
        stack.append(d["precip_rate_mm_hr"] * np.float32(h))  # mm/month
        hours.append(h)
    checks = {"expected_months": len(months), "cached_months": len(stack),
              "missing_months": missing, "unexpected_files": extra,
              "hours_mismatch": bad_hours,
              "leap_februaries_696h": [m.strftime("%Y-%m") for m, h in zip(months, hours)
                                       if m.month == 2 and h == 696.0]}
    if missing or bad_hours:
        print("CHECK FAILED:", checks)
    return months, np.stack(stack), np.array(hours), checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--clim-years", type=int, nargs=2, default=list(CLIM_YEARS),
                    help="years whose climatology defines the regions")
    ap.add_argument("--tag", default="", help="suffix for sensitivity outputs, e.g. _k2")
    args = ap.parse_args()
    clim_years = tuple(args.clim_years)
    tag = args.tag

    months, mm, hours, cache_checks = load_cache()
    lsm = np.load(DATA / "interim" / "imerg_landsea_box.npz")
    lon, lat, water = lsm["lon"].astype(np.float64), lsm["lat"].astype(np.float64), lsm["water_pct"]

    shp, ne_meta = get_natural_earth()
    idn = rg.load_country(shp)
    frac = rg.cell_fraction(idn, lon, lat)
    include = rg.include_mask(frac, water)

    area = np.cos(np.deg2rad(lat))[:, None] * np.ones((1, lon.size))  # relative cell area
    any_idn = frac > 0
    mask_stats = {
        "rule": f"indonesia_fraction >= {rg.MIN_COUNTRY_FRAC} AND imerg_water_pct < {rg.MAX_WATER_PCT}",
        "subsampling": "10 x 10 points per 0.1-degree cell",
        "cells_touching_indonesia": int(any_idn.sum()),
        "cells_included": int(include.sum()),
        "excluded_low_indonesia_fraction": int((any_idn & (frac < rg.MIN_COUNTRY_FRAC)).sum()),
        "excluded_by_imerg_water_only": int(((frac >= rg.MIN_COUNTRY_FRAC) & (water >= rg.MAX_WATER_PCT)).sum()),
        "indonesian_land_area_captured_frac": float((frac * area)[include].sum() / (frac * area).sum()),
        "ne_polygon_area_deg2": float(idn.area),
        "grid_estimated_area_deg2": float(frac.sum() * 0.01),
    }

    import shapely
    LONg, LATg = np.meshgrid(lon, lat)
    tree = shapely.STRtree(shapely.points(LONg[include], LATg[include]))
    parts = list(getattr(idn, "geoms", [idn]))
    lost = [p for p in parts if len(tree.query(p, predicate="contains")) == 0]
    mask_stats["natural_earth_polygon_parts"] = len(parts)
    mask_stats["parts_without_included_cell_centre"] = len(lost)
    mask_stats["area_share_of_those_parts"] = float(sum(p.area for p in lost) / sum(p.area for p in parts))

    # ---- all-month fill check inside the included cells (no gap filling anywhere)
    sel = include
    nan_cells = np.isnan(mm[:, sel]).sum(axis=1)
    cache_checks["months_with_nan_in_included_cells"] = int((nan_cells > 0).sum())
    cache_checks["max_nan_cells_in_a_month"] = int(nan_cells.max())

    # ---- climatological annual cycle on complete years
    yrs = months.year
    clim_sel = (yrs >= clim_years[0]) & (yrs <= clim_years[1])
    cells = mm[:, sel]                                   # (time, ncell)
    clim = np.stack([np.nanmean(cells[clim_sel & (months.month == m)], axis=0)
                     for m in range(1, 13)])             # (12, ncell)
    X = rg.standardized_cycle(clim)
    ok = ~np.isnan(X).any(axis=1)
    if not ok.all():
        raise SystemExit(f"{(~ok).sum()} cells have a flat/undefined annual cycle")

    from sklearn.metrics import silhouette_score
    rng = np.random.default_rng(SEED)
    sub = rng.choice(len(X), size=min(5000, len(X)), replace=False)
    sil = {}
    for k in range(2, 7):
        lab, _, _ = rg.kmeans(X, k, SEED)
        sil[k] = float(silhouette_score(X[sub], lab[sub]))

    labels, centers, inertia = rg.kmeans(X, args.k, SEED)
    seed_ari = [rg.adjusted_rand(labels, rg.kmeans(X, args.k, SEED + i)[0]) for i in range(1, 6)]
    years = np.arange(clim_years[0], clim_years[1] + 1)
    boot_ari = []
    for b in range(20):
        ys = rng.choice(years, size=years.size, replace=True)
        cb = np.stack([np.nanmean(np.concatenate([cells[(yrs == y) & (months.month == m)] for y in ys]), axis=0)
                       for m in range(1, 13)])
        boot_ari.append(rg.adjusted_rand(labels, rg.kmeans(rg.standardized_cycle(cb), args.k, SEED)[0]))

    region = np.zeros(include.shape, dtype=np.int8)
    region[sel] = labels + 1

    # ---- regional series (area-weighted, NaN-aware, no interpolation)
    rows = []
    names = [f"R{i}" for i in range(1, args.k + 1)] + ["ALL"]
    for t, m in enumerate(months):
        for i, nm in enumerate(names):
            s = include if nm == "ALL" else region == i + 1
            v, vf = rg.area_weighted_mean(mm[t], area, s)
            rows.append({"month": m.strftime("%Y-%m"), "region": nm,
                         "precip_mm_month": round(v, 3), "valid_area_frac": round(vf, 4),
                         "n_cells": int(s.sum()), "hours": hours[t]})
    series = pd.DataFrame(rows)
    out_csv = DATA / "processed" / f"imerg_regional_monthly{tag}.csv"
    series.to_csv(out_csv, index=False)

    # ---- descriptors (computed) for each region
    desc = {}
    LON, LAT = np.meshgrid(lon, lat)
    for i, nm in enumerate(names[:-1]):
        s = region == i + 1
        w = area[s]
        r = series[series.region == nm].assign(cal=lambda d: d.month.str[5:7].astype(int))
        r = r[r.month.str[:4].astype(int).between(*clim_years)]
        cyc = r.groupby("cal")["precip_mm_month"].mean()
        peaks = [int(m) for m in range(1, 13)
                 if cyc[m] > cyc[(m - 2) % 12 + 1] and cyc[m] > cyc[m % 12 + 1]]
        desc[nm] = {"n_cells": int(s.sum()),
                    "area_share": float(w.sum() / area[include].sum()),
                    "centroid_lon": float((LON[s] * w).sum() / w.sum()),
                    "centroid_lat": float((LAT[s] * w).sum() / w.sum()),
                    "lon_range": [float(LON[s].min()), float(LON[s].max())],
                    "lat_range": [float(LAT[s].min()), float(LAT[s].max())],
                    "climatology_mm_month": {int(k): round(float(v), 1) for k, v in cyc.items()},
                    "wettest_month": int(cyc.idxmax()), "driest_month": int(cyc.idxmin()),
                    "local_maxima_months": peaks}

    np.savez_compressed(DATA / "processed" / f"indonesia_regions{tag}.npz", lon=lon.astype(np.float32),
                        lat=lat.astype(np.float32), indonesia_frac=frac, water_pct=water,
                        include=include, region=region)
    main = DATA / "processed" / "indonesia_regions.npz"
    ari_vs_main = None
    if tag and main.exists():
        ref = np.load(main)["region"]
        both = include & (ref > 0)
        ari_vs_main = rg.adjusted_rand(ref[both], region[both])
    write_json(DATA / "provenance" / f"regions{tag}.json", {
        "ARI_vs_main_regions": ari_vs_main,
        "built_utc": utc_now(),
        "period": [START, END], "climatology_years": list(clim_years),
        "cache_checks": cache_checks,
        "territory_source": ne_meta,
        "landsea_mask": "GES DISC GPM_IMERG_LandSeaMask V2, DOI 10.5067/6P5EM1HPR3VD (percent water)",
        "mask": mask_stats,
        "regionalization": {
            "method": ("k-means (scikit-learn, n_init=20) on each included cell's standardised "
                       "climatological annual cycle (12 values, z-scored across months)"),
            "k": args.k, "k_choice": "a priori, matching the number of published regions; "
                                     "silhouette scores reported for k=2..6",
            "seed": SEED, "silhouette_by_k_subsample5000": sil,
            "seed_stability_ARI": seed_ari, "year_bootstrap_ARI_20": boot_ari,
            "labels": "R1..Rk ordered by cell count; NOT Aldrian & Susanto (2003) A/B/C",
            "spatial_contiguity": "not enforced",
        },
        "regions": desc,
        "regional_series": {"file": str(out_csv.relative_to(DATA.parent)),
                            "units": "mm/month (area-weighted mean of monthly totals)",
                            "weights": "cos(latitude)", "gap_filling": "none"},
    })
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        r = region.astype(float)
        r[r == 0] = np.nan
        colors = ["#2f6f8f", "#e0a03d", "#b5542f", "#6b8e4e", "#7a5c9e", "#999999"][:args.k]
        fig, ax = plt.subplots(figsize=(12, 4.8))
        ax.pcolormesh(lon, lat, r, cmap=matplotlib.colors.ListedColormap(colors), shading="nearest")
        for p in parts:
            ax.plot(*p.exterior.xy, lw=0.3, c="k")
        ax.set_aspect("equal")
        ax.set_xlabel("Longitude (°E)")
        ax.set_ylabel("Latitude (°N)")
        ax.set_title("IMERG-derived annual-cycle regions " + ", ".join(
            f"R{i + 1} ({c})" for i, c in enumerate(["blue", "gold", "rust", "green", "purple", "grey"][:args.k]))
            + " — not Aldrian & Susanto A/B/C", fontsize=10)
        fig_path = DATA.parent / "docs" / "figures" / f"regions_map{tag}.png"
        fig_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_path, dpi=110, bbox_inches="tight")
    except ImportError:
        print("matplotlib not installed; map skipped")

    print("cache:", {k: v for k, v in cache_checks.items() if k != "leap_februaries_696h"})
    print("mask:", mask_stats)
    print("silhouette:", sil, "\nseed ARI:", np.round(seed_ari, 3), "\nboot ARI:",
          np.round(np.percentile(boot_ari, [0, 50, 100]), 3))
    for nm, d in desc.items():
        print(nm, {k: d[k] for k in ("n_cells", "area_share", "centroid_lon", "centroid_lat",
                                     "wettest_month", "driest_month", "local_maxima_months")})


if __name__ == "__main__":
    main()
