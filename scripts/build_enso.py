"""Download NOAA CPC ONI and RONI, save raw copies, build a monthly table.

Usage:
    python scripts/build_enso.py            # download fresh copies from CPC
    python scripts/build_enso.py --offline  # rebuild from data/raw/enso/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from beyond_prediction import enso  # noqa: E402
from beyond_prediction.provenance import DATA, read_json, sha256_bytes, utc_now, write_json  # noqa: E402

RAW = DATA / "raw" / "enso"
FILES = {"oni": ("oni.ascii.txt", enso.ONI_URL), "roni": ("RONI.ascii.txt", enso.RONI_URL)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use existing raw files")
    args = ap.parse_args()

    prov_path = DATA / "provenance" / "enso.json"
    old = read_json(prov_path) or {}
    sources, texts = {}, {}
    for key, (fname, url) in FILES.items():
        path = RAW / fname
        if args.offline:
            raw = path.read_bytes()
            accessed = old.get("sources", {}).get(key, {}).get("accessed_utc", "unknown")
        else:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            raw = r.content
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            accessed = utc_now()
        texts[key] = raw.decode("utf-8")
        sources[key] = {"url": url, "local_file": str(path.relative_to(DATA.parent)),
                        "sha256": sha256_bytes(raw), "bytes": len(raw), "accessed_utc": accessed}

    df = enso.build_monthly(texts["oni"], texts["roni"])
    out = DATA / "processed" / "enso_monthly.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_csv(out, index=False, float_format="%.2f")

    write_json(prov_path, {
        "dataset": "NOAA CPC ENSO indices (ONI and RONI), ERSSTv6-based",
        "built_utc": utc_now(),
        "sources": sources,
        "definitions": {
            "oni": ("3-month running mean of ERSST.v6 SST anomalies in the Nino 3.4 region "
                    "(5N-5S, 120-170W), based on centered 30-year base periods updated every "
                    "5 years. Source: " + enso.ONI_PAGE),
            "roni": ("3-month running mean of ERSST.v6 Nino 3.4 SST anomalies (1991-2020 base) "
                     "with the tropical-mean (20N-20S) SST anomaly subtracted, then rescaled so "
                     "its variance equals the original Nino 3.4 index. Per NWS Public Information "
                     "Statement 26-05, RONI is used for official ENSO monitoring. Source: "
                     + enso.RONI_PAGE),
            "units": "degC",
            "temporal_alignment": ("Each 3-month season is assigned to its centre month: "
                                   "DJF of year Y -> Jan Y (window Dec Y-1..Feb Y); NDJ of year "
                                   "Y -> Dec Y (window Nov Y..Jan Y+1)."),
            "caveat": ("CPC notes the most recent values may change for up to two months "
                       "after first posting and should be treated as estimates."),
            "version_check": ("oni.ascii.txt values were matched against CPC's ERSSTv6 ONI table "
                              "(DJF 1950: file -1.32, v6 table -1.3, v5 table -1.5)."),
        },
        "processed_file": str(out.relative_to(DATA.parent)),
        "rows": len(df),
        "first_month": df["date"].iloc[0].strftime("%Y-%m"),
        "last_month": df["date"].iloc[-1].strftime("%Y-%m"),
    })
    print(f"Wrote {out} ({len(df)} rows, {df['date'].iloc[0]:%Y-%m} to {df['date'].iloc[-1]:%Y-%m})")


if __name__ == "__main__":
    main()
