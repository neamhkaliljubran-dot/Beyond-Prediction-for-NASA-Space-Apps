"""Stage G: build cached network tables from Stage F results (no new ENSO statistics).

ENSO->region edges are copied from data/results/associations_primary.csv (full
discovery period) and data/results/rolling.csv (11-year windows). Region–region edges
(same-month rainfall anomaly correlations) are computed here on the discovery period
only, with the same 2-year season-year block bootstrap; they are labelled exploratory.

Outputs: data/results/network_edges.csv, network_patterns.csv, network_nodes.json
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from beyond_prediction import network as N  # noqa: E402
from beyond_prediction import stats as S  # noqa: E402
from beyond_prediction.provenance import DATA, ROOT, read_json, utc_now, write_json  # noqa: E402

CFG = json.loads((ROOT / "config" / "analysis.json").read_text())
START, END = CFG["split"]["discovery_period"]
RES = DATA / "results"
REGS = ["R1", "R2", "R3"]


def enso_edges() -> pd.DataFrame:
    p = pd.read_csv(RES / "associations_primary.csv")
    full = pd.DataFrame({"kind": "ENSO-region", "source": "ENSO", "target": p.region, "season": p.season,
                         "lag": p.lag, "window": N.FULL, "r": p.r, "ci_lo": p.r_ci_lo, "ci_hi": p.r_ci_hi,
                         "n": p.n, "n_eff": p.n_eff, "q_bh": p.q_bh_surrogate,
                         "slope_mm_per_degC": p.slope_mm_per_degC})
    r = pd.read_csv(RES / "rolling.csv")
    roll = pd.DataFrame({"kind": "ENSO-region", "source": "ENSO", "target": r.region, "season": r.season,
                         "lag": r.lag, "window": r.window, "r": r.r, "ci_lo": r.r_ci_lo, "ci_hi": r.r_ci_hi,
                         "n": r.n, "n_eff": np.nan, "q_bh": np.nan, "slope_mm_per_degC": r.slope_mm_per_degC})
    return pd.concat([full, roll], ignore_index=True)


def region_edges(rng) -> pd.DataFrame:
    s = pd.read_csv(DATA / "processed" / "imerg_regional_monthly.csv")
    s["date"] = pd.to_datetime(s["month"] + "-01")
    s = s[(s.date >= pd.Timestamp(START + "-01")) & (s.date <= pd.Timestamp(END + "-01"))]
    an = {}
    for reg, g in s.groupby("region"):
        x = g.set_index("date")["precip_mm_month"].asfreq("MS")
        an[reg] = S.anomalies(x, S.monthly_climatology(x))["anom_mm"]
    w = CFG["rolling"]["window_years"]
    windows = [(N.FULL, START, END)] + [
        (f"{y}-{y + w - 1}", max(pd.Timestamp(f"{y - 1}-12-01"), pd.Timestamp(START + "-01")).strftime("%Y-%m"),
         f"{y + w - 1}-11") for y in range(int(START[:4]), int(END[:4]) - w + 2)]
    rows = []
    for a, b in combinations(REGS, 2):
        for season, months in CFG["seasons"].items():
            for lab, st, en in windows:
                p = S.lagged_pairs(an[a], an[b], months, 0, st, en)
                x, y = p.enso.to_numpy(), p.rain.to_numpy()
                sy = S.season_year(pd.DatetimeIndex(p.t_rain))
                nb = 2000 if lab == N.FULL else 500
                br = [S.pearson(x[i], y[i]) for i in S.block_bootstrap_years(sy, nb, 2, rng)]
                rows.append({"kind": "region-region", "source": a, "target": b, "season": season, "lag": 0,
                             "window": lab, "r": S.pearson(x, y), "ci_lo": np.percentile(br, 2.5),
                             "ci_hi": np.percentile(br, 97.5), "n": len(x), "n_eff": np.nan, "q_bh": np.nan,
                             "slope_mm_per_degC": np.nan})
    return pd.DataFrame(rows)


def main() -> None:
    rng = np.random.default_rng(CFG["inference"]["seed"])
    edges = pd.concat([enso_edges(), region_edges(rng)], ignore_index=True)
    edges["status"] = edges.apply(N.edge_status, axis=1)
    pats = N.patterns(edges)
    edges = edges.merge(pats[["kind", "source", "target", "season", "lag", "pattern"]],
                        on=["kind", "source", "target", "season", "lag"], how="left")
    edges.to_csv(RES / "network_edges.csv", index=False)
    pats.to_csv(RES / "network_patterns.csv", index=False)

    reg = read_json(DATA / "provenance" / "regions.json")["regions"]
    sel = read_json(RES / "stage_h_selection.json")
    tst = {r["target"]: r for r in read_json(RES / "stage_h_test.json")["results"]}
    notes = {}
    for k, v in sel["choices"].items():
        t = tst[k]
        if v["reliable"]:
            notes[k] = (f"validated equation ({v['selected']}); held-out skill vs climatology "
                        f"{t['msess_selected']:.2f}, linear lag-0 {t['msess_linear_lag0']:.2f}")
        else:
            notes[k] = f"no validated ENSO equation (validation chose {v['selected']})"
    write_json(RES / "network_nodes.json", {
        "built_utc": utc_now(),
        "nodes": {"ENSO": {"label": "ENSO (RONI, degC)", "pos": list(N.NODE_POS["ENSO"]),
                           "note": "schematic position; RONI is a Pacific SST index"},
                  **{r: {"label": f"{r} rainfall anomaly (mm/month)",
                         "pos": [round(reg[r]["centroid_lon"], 2), round(reg[r]["centroid_lat"], 2)],
                         "area_share": reg[r]["area_share"]} for r in REGS}},
        "stage_h_notes": notes,
        "rules": N.__doc__,
    })
    print(pats.groupby(["kind", "pattern"]).size())


if __name__ == "__main__":
    main()
