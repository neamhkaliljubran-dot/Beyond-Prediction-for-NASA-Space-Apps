"""Verify the GPM IMERG monthly V07 collection before any bulk download.

Queries NASA CMR (no login needed) for collection metadata and granule
coverage, and optionally inspects one locally downloaded granule's variables
and units. Writes data/provenance/imerg_verification.json.

Usage:
    python scripts/verify_imerg.py [--granule path/to/3B-MO...V07B.HDF5]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from beyond_prediction.provenance import DATA, sha256_bytes, utc_now, write_json  # noqa: E402

CMR = "https://cmr.earthdata.nasa.gov/search"
SHORT_NAME, VERSION = "GPM_3IMERGM", "07"


def cmr_get(path: str, **params) -> requests.Response:
    r = requests.get(f"{CMR}/{path}", params=params, timeout=60)
    r.raise_for_status()
    return r


def granule_summary(item: dict) -> dict:
    u = item["umm"]
    urls = {r["Type"]: r["URL"] for r in u.get("RelatedUrls", [])
            if r["Type"] in ("GET DATA", "USE SERVICE API")}
    size = u.get("DataGranule", {}).get("ArchiveAndDistributionInformation", [{}])[0]
    return {"granule_ur": u["GranuleUR"], "time": u["TemporalExtent"]["RangeDateTime"],
            "download_url": urls.get("GET DATA"), "opendap_url": urls.get("USE SERVICE API"),
            "size": f"{size.get('Size')} {size.get('SizeUnit')}"}


def inspect_granule(path: Path) -> dict:
    import h5py

    def clean(v):
        v = v.decode() if isinstance(v, bytes) else v
        return " ".join(v.split()) if isinstance(v, str) else (v.item() if hasattr(v, "item") else v)

    info = {"file": path.name, "sha256": sha256_bytes(path.read_bytes()),
            "bytes": path.stat().st_size, "variables": {}}
    with h5py.File(path, "r") as f:
        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                info["variables"][name] = {
                    "shape": list(obj.shape), "dtype": str(obj.dtype),
                    **{k: clean(obj.attrs[k]) for k in
                       ("units", "LongName", "DimensionNames", "_FillValue") if k in obj.attrs}}
        f.visititems(visit)
        lat, lon = f["Grid/lat"][:], f["Grid/lon"][:]
        info["grid"] = {"lat_first": float(lat[0]), "lat_last": float(lat[-1]),
                        "lon_first": float(lon[0]), "lon_last": float(lon[-1]),
                        "resolution_deg": round(float(lat[1] - lat[0]), 4)}
        header = clean(f.attrs.get("FileHeader", b""))
        info["file_header_excerpt"] = header[:600]
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--granule", type=Path)
    args = ap.parse_args()

    coll = cmr_get("collections.umm_json", short_name=SHORT_NAME, version=VERSION).json()
    if coll["hits"] != 1:
        raise SystemExit(f"Expected 1 collection, got {coll['hits']}")
    item = coll["items"][0]
    u = item["umm"]
    cid = item["meta"]["concept-id"]

    first = cmr_get("granules.umm_json", collection_concept_id=cid, page_size=1,
                    sort_key="start_date")
    last = cmr_get("granules.umm_json", collection_concept_id=cid, page_size=1,
                   sort_key="-start_date")
    report = {
        "verified_utc": utc_now(),
        "collection": {
            "concept_id": cid, "short_name": u["ShortName"], "version": u["Version"],
            "title": u["EntryTitle"], "doi": u.get("DOI", {}).get("DOI"),
            "temporal_extent_metadata": u.get("TemporalExtents"),
            "abstract_first_sentence": u.get("Abstract", "").split("\n")[0],
        },
        "granules": {
            "count": int(first.headers["CMR-Hits"]),
            "first": granule_summary(first.json()["items"][0]),
            "last": granule_summary(last.json()["items"][0]),
        },
        "access": {
            "requires": "NASA Earthdata Login; account must authorise 'NASA GESDISC DATA ARCHIVE'",
            "download_host": "data.gesdisc.earthdata.nasa.gov (redirects to a signed CloudFront URL)",
            "subsetting_service": "opendap.earthdata.nasa.gov (OPeNDAP)",
        },
    }
    if args.granule:
        report["sample_granule"] = inspect_granule(args.granule)
    out = DATA / "provenance" / "imerg_verification.json"
    write_json(out, report)
    g = report["granules"]
    print(f"{cid}: {g['count']} granules, {g['first']['time']['BeginningDateTime']} -> "
          f"{g['last']['time']['EndingDateTime']}; wrote {out}")


if __name__ == "__main__":
    main()
