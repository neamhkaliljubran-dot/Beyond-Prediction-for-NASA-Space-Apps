"""Parse NOAA CPC ENSO index files (ONI, RONI) into a tidy monthly table.

Both CPC ASCII files list 3-month running means labelled by season code
(DJF, JFM, ..., NDJ) and a year. Per the CPC RONI/ONI tables, season ``DJF``
of year Y covers Dec(Y-1), Jan(Y), Feb(Y), and ``NDJ`` of year Y covers
Nov(Y), Dec(Y), Jan(Y+1). We therefore assign each value to the *centre*
month of its window: DJF -> January of Y, ..., NDJ -> December of Y.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
           "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
CENTER_MONTH = {s: i + 1 for i, s in enumerate(SEASONS)}

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
RONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
ONI_PAGE = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/"
RONI_PAGE = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/"


def parse_cpc_index(text: str) -> pd.DataFrame:
    """Parse a CPC season/year index file.

    Returns columns: season, year, date (centre month, first of month), plus
    every numeric column in the file, lower-cased (e.g. ``total``, ``anom``).
    """
    df = pd.read_csv(io.StringIO(text), sep=r"\s+")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"seas": "season", "yr": "year"})
    if not {"season", "year", "anom"} <= set(df.columns):
        raise ValueError(f"Unexpected CPC header: {list(df.columns)}")
    bad = set(df["season"]) - set(SEASONS)
    if bad:
        raise ValueError(f"Unknown season codes: {sorted(bad)}")
    df["year"] = df["year"].astype(int)
    for c in df.columns.difference(["season", "year"]):
        df[c] = pd.to_numeric(df[c], errors="raise").astype(float)
        # CPC uses -99.9 / -9999 style codes for missing values in some files.
        df.loc[df[c] <= -90, c] = np.nan
    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["season"].map(CENTER_MONTH), day=1))
    if df["date"].duplicated().any():
        raise ValueError("Duplicate season/year rows in CPC file")
    df = df.sort_values("date").reset_index(drop=True)
    expected = pd.date_range(df["date"].iloc[0], df["date"].iloc[-1], freq="MS")
    if len(expected) != len(df):
        raise ValueError(f"Gaps in CPC series: {len(expected) - len(df)} months missing")
    return df


def build_monthly(oni_text: str, roni_text: str) -> pd.DataFrame:
    """Merge ONI and RONI onto a common centre-month index (inner join)."""
    oni = parse_cpc_index(oni_text).rename(
        columns={"total": "oni_total_degC", "anom": "oni_anom_degC"})
    roni = parse_cpc_index(roni_text).rename(columns={"anom": "roni_anom_degC"})
    merged = oni.merge(roni[["date", "season", "roni_anom_degC"]],
                       on=["date", "season"], how="inner", validate="1:1")
    cols = ["date", "year", "season", "oni_anom_degC", "roni_anom_degC"]
    if "oni_total_degC" in merged:
        cols.insert(3, "oni_total_degC")
    return merged[cols]


def episode_flags(values: pd.Series, threshold: float = 0.5,
                  min_run: int = 5) -> pd.Series:
    """Label months +1 (warm), -1 (cold) or 0 using CPC's historical rule.

    A month is warm (cold) if it belongs to a run of at least ``min_run``
    consecutive overlapping seasons with index >= +threshold (<= -threshold).
    Applied to the file's two-decimal values, so edge cases may differ from
    CPC's published colour table, which uses values rounded to 0.1 degC.
    """
    v = values.to_numpy()
    out = np.zeros(len(v), dtype=int)
    for sign in (1, -1):
        hit = (sign * v) >= threshold
        i = 0
        while i < len(v):
            if hit[i]:
                j = i
                while j < len(v) and hit[j]:
                    j += 1
                if j - i >= min_run:
                    out[i:j] = sign
                i = j
            else:
                i += 1
    return pd.Series(out, index=values.index, name="episode")
