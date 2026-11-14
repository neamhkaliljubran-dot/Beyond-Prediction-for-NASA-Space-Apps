"""Resumable IMERG V07 monthly download -> Indonesia box subset -> delete granule.

For each month in the requested range:
  1. look up the granule in NASA CMR (listing cached in data/provenance/),
  2. skip it if its subset already exists in the cache and the manifest,
  3. download the global HDF5 to a temporary file (with retries),
  4. check the byte size against CMR and record a SHA-256,
  5. cut out the Indonesia box, validate grid/units/time bounds, save .npz,
  6. delete the global file, and append a row to the manifest.

Only the small box subsets are kept; full global granules never accumulate.

Usage:
    python scripts/fetch_imerg_subset.py --start 2024-10 --end 2025-09
    python scripts/fetch_imerg_subset.py --granule-file local.HDF5   # one local file
Requires a NASA Earthdata token accepted by data.gesdisc.earthdata.nasa.gov
(injected by the environment proxy here; elsewhere set EARTHDATA_TOKEN).
"""

from __future__ import annotations

import argparse
import csv
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from beyond_prediction import imerg  # noqa: E402
from beyond_prediction.provenance import DATA, sha256_bytes, utc_now  # noqa: E402

CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
CACHE = DATA / "interim" / "imerg_box"
LISTING = DATA / "provenance" / "imerg_granules.csv"
MANIFEST = DATA / "provenance" / "imerg_manifest.csv"
LSM_OUT = DATA / "interim" / "imerg_landsea_box.npz"
MANIFEST_COLS = ["month", "granule", "bytes", "cmr_size_mib", "sha256", "hours",
                 "n_cells", "n_fill", "box_mean_rate_mm_hr", "download_s", "processed_utc"]


def session() -> requests.Session:
    s = requests.Session()
    tok = os.environ.get("EARTHDATA_TOKEN")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


def list_granules(refresh: bool = False) -> pd.DataFrame:
    """All granules of the collection from CMR, cached as CSV."""
    if LISTING.exists() and not refresh:
        return pd.read_csv(LISTING, dtype={"month": str})
    rows, after = [], None
    while True:
        headers = {"CMR-Search-After": after} if after else {}
        r = requests.get(CMR, params={"collection_concept_id": imerg.COLLECTION_ID,
                                      "page_size": 200, "sort_key": "start_date"},
                         headers=headers, timeout=60)
        r.raise_for_status()
        for it in r.json()["items"]:
            u = it["umm"]
            url = next(x["URL"] for x in u["RelatedUrls"] if x["Type"] == "GET DATA")
            size = u["DataGranule"]["ArchiveAndDistributionInformation"][0]
            rows.append({"month": u["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:7],
                         "granule": url.rsplit("/", 1)[1], "url": url,
                         "cmr_size_mib": size["Size"] if size.get("SizeUnit") == "MB" else None})
        after = r.headers.get("CMR-Search-After")
        if not after or not r.json()["items"]:
            break
    df = pd.DataFrame(rows).drop_duplicates("month")
    LISTING.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(LISTING, index=False)
    return df


def download(s: requests.Session, url: str, dest: Path, tries: int = 4) -> float:
    for k in range(tries):
        try:
            t = time.time()
            with s.get(url, stream=True, timeout=(30, 300), allow_redirects=True) as r:
                if r.status_code in (401, 403):
                    raise SystemExit(f"Access denied ({r.status_code}): {r.text[:200]}")
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            return time.time() - t
        except (requests.RequestException, OSError) as e:
            if k == tries - 1:
                raise
            wait = 5 * 2 ** k
            print(f"  retry {k + 1} after error: {e} (sleep {wait}s)")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def done_months() -> set[str]:
    if not MANIFEST.exists():
        return set()
    m = pd.read_csv(MANIFEST, dtype={"month": str})
    return {mo for mo in m["month"] if (CACHE / f"{mo}.npz").exists()}


def process_file(path: Path, month: str, granule: str, cmr_size: float | None,
                 download_s: float) -> dict:
    raw = path.read_bytes()
    size_mib = len(raw) / 2**20
    if cmr_size is not None and abs(size_mib - cmr_size) > 1e-3:
        raise ValueError(f"{granule}: size {size_mib:.4f} MiB != CMR {cmr_size:.4f} MiB")
    sub = imerg.read_granule_subset(path)
    if sub["period_start"][:7] != month:
        raise ValueError(f"{granule}: time_bnds start {sub['period_start']} != {month}")
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = CACHE / f".{month}.tmp.npz"
    np.savez_compressed(tmp, lon=sub["lon"], lat=sub["lat"],
                        precip_rate_mm_hr=sub["precip_rate_mm_hr"],
                        random_error_mm_hr=sub["random_error_mm_hr"],
                        hours=np.float64(sub["hours"]), granule=np.str_(granule))
    tmp.replace(CACHE / f"{month}.npz")
    return {"month": month, "granule": granule, "bytes": len(raw),
            "cmr_size_mib": cmr_size, "sha256": sha256_bytes(raw), "hours": sub["hours"],
            "n_cells": int(sub["precip_rate_mm_hr"].size), "n_fill": sub["n_fill"],
            "box_mean_rate_mm_hr": float(np.nanmean(sub["precip_rate_mm_hr"])),
            "download_s": round(download_s, 2), "processed_utc": utc_now()}


def append_manifest(row: dict) -> None:
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


def ensure_landsea(s: requests.Session, tmpdir: Path) -> None:
    if LSM_OUT.exists():
        return
    p = tmpdir / "lsm.nc4"
    download(s, imerg.LSM_URL, p)
    raw = p.read_bytes()
    m = imerg.read_landsea_subset(p)
    LSM_OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(LSM_OUT, lon=m["lon"], lat=m["lat"], water_pct=m["water_pct"],
                        source_url=np.str_(imerg.LSM_URL), sha256=np.str_(sha256_bytes(raw)))
    p.unlink()
    print(f"land/sea mask subset saved ({sha256_bytes(raw)[:12]}…)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", help="YYYY-MM")
    ap.add_argument("--end", help="YYYY-MM")
    ap.add_argument("--granule-file", type=Path, help="process one local granule")
    ap.add_argument("--refresh-listing", action="store_true")
    ap.add_argument("--tmpdir", type=Path, default=None)
    args = ap.parse_args()

    s = session()
    tmpdir = Path(args.tmpdir or tempfile.mkdtemp(prefix="imerg_"))
    tmpdir.mkdir(parents=True, exist_ok=True)
    ensure_landsea(s, tmpdir)
    listing = list_granules(args.refresh_listing)

    if args.granule_file:
        name = args.granule_file.name
        row = listing[listing["granule"] == name]
        if row.empty:
            raise SystemExit(f"{name} is not in the CMR listing")
        r = process_file(args.granule_file, row["month"].iloc[0], name,
                         row["cmr_size_mib"].iloc[0], 0.0)
        if r["month"] not in done_months():
            append_manifest(r)
        print(r)
        return

    sel = listing[(listing["month"] >= args.start) & (listing["month"] <= args.end)]
    expected = pd.period_range(args.start, args.end, freq="M").strftime("%Y-%m")
    missing = sorted(set(expected) - set(sel["month"]))
    if missing:
        print(f"WARNING: {len(missing)} requested months have no granule in CMR: {missing}")
    done = done_months()
    todo = sel[~sel["month"].isin(done)]
    print(f"{len(sel)} granules in range, {len(sel) - len(todo)} already cached, {len(todo)} to fetch")
    t_all = time.time()
    for _, g in todo.iterrows():
        dest = tmpdir / g["granule"]
        dt = download(s, g["url"], dest)
        try:
            r = process_file(dest, g["month"], g["granule"], g["cmr_size_mib"], dt)
        finally:
            dest.unlink(missing_ok=True)
        append_manifest(r)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(f"{g['month']}: {r['bytes'] / 2**20:.1f} MiB in {dt:.1f}s, fill={r['n_fill']}, "
              f"box mean {r['box_mean_rate_mm_hr']:.3f} mm/hr, peak RSS {rss:.0f} MiB")
    print(f"done in {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()
