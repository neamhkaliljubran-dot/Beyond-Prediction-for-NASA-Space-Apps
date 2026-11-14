"""Stage H: equation discovery with time-aware validation and a frozen held-out test.

Phase 1 (select): uses rainfall months 1998-01..2019-12 only.
  - Regions: k=3 regions fitted on the 1998-2013 climatology (regions_k3train), so region
    definitions use training years only.
  - Expanding-window validation: for each validation year Y in 2014..2019, climatology and
    coefficients are fitted on months 1998-01..(Y-1)-12 and predictions are made for the
    target-season months of calendar year Y.
  - Selection rule (fixed in advance; see SELECTION_RULE): per target, the lowest validation
    MSE, then a one-standard-error parsimony rule (year blocks).
  - The headline equation is chosen by HEADLINE_RULE. Final coefficients are refitted on
    1998-01..2019-12 with block-bootstrap 95% CIs. Everything is written to
    data/results/stage_h_selection.json, which must be committed before phase 2.
Phase 2 (test): reads the frozen selection and evaluates once on 2020-01..2025-09.

Usage:
    python scripts/run_equation_search.py select
    python scripts/run_equation_search.py test
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from beyond_prediction import equations as E  # noqa: E402
from beyond_prediction import stats as S  # noqa: E402
from beyond_prediction.provenance import DATA, ROOT, read_json, utc_now, write_json  # noqa: E402

CFG = json.loads((ROOT / "config" / "analysis.json").read_text())
SEASONS = CFG["seasons"]
TRAIN_END = pd.Timestamp(CFG["split"]["train"][1] + "-01")
VAL_YEARS = list(range(int(CFG["split"]["validation"][0][:4]), int(CFG["split"]["validation"][1][:4]) + 1))
FIT_END = pd.Timestamp(CFG["split"]["validation"][1] + "-01")
TEST_START, TEST_END = (pd.Timestamp(m + "-01") for m in CFG["split"]["test"])
OUT = DATA / "results"
SEL_PATH = OUT / "stage_h_selection.json"
REGION_TAG = "_k3train"
PRIORITY = [("R1", "JJA"), ("R2", "JJA"), ("R3", "JJA"),
            ("R1", "SON"), ("R2", "SON"), ("R3", "SON"), ("R3", "DJF")]
SELECTION_RULE = ("Per target: compute expanding-window validation MSE (2014-2019) for every candidate. "
                  "Let 'best' have the lowest MSE. Among candidates whose mean squared-error excess over "
                  "'best' is <= 1 standard error (SE over the 6 validation years), pick the fewest "
                  "parameters (ties: lower MSE). The target is 'reliable' if the selected model is not "
                  "climatology/persistence, its validation MSESS vs climatology > 0.10, and it beats "
                  "climatology in >= 4 of 6 validation years.")
HEADLINE_RULE = ("Among PRIORITY targets (post-hoc from Stage F) flagged reliable, the one with the highest "
                 "validation MSESS. Worked example: the test-period month of that target season with the "
                 "largest |ENSO predictor|.")
SEED = CFG["inference"]["seed"]


def load():
    e = pd.read_csv(DATA / "processed" / "enso_monthly.csv", parse_dates=["date"]).set_index("date")
    s = pd.read_csv(DATA / "processed" / f"imerg_regional_monthly{REGION_TAG}.csv")
    s["date"] = pd.to_datetime(s["month"] + "-01")
    rain = {r: g.set_index("date")["precip_mm_month"].astype(float).asfreq("MS")
            for r, g in s.groupby("region") if r != "ALL"}
    return e["roni_anom_degC"], rain


def mse(e):
    return float(np.mean(np.square(e)))


def frames_for(rain, enso, clim, months, start, end, cands):
    """Frames per lag restricted to rows valid for ALL candidates (paired comparison)."""
    fr = {L: E.frame(rain, enso, clim, months, L, start, end) for L in range(4)}
    ok = np.ones(len(fr[0]), dtype=bool)
    for L, f in fr.items():
        ok &= ~f[["y", "y_prev", "x", "x_tend"]].isna().any(axis=1).to_numpy()
    return {L: f[ok] for L, f in fr.items()}


def validate_target(rain, enso, months, cands):
    """Expanding-window validation errors per candidate, per validation year."""
    errs = {c.key: [] for c in cands}
    years = []
    for Y in VAL_YEARS:
        fit_end = pd.Timestamp(f"{Y - 1}-12-01")
        clim = E.climatology(rain.loc["1998-01":fit_end], fit_end)
        tr = frames_for(rain, enso, clim, months, "1998-01", fit_end, cands)
        va = frames_for(rain, enso, clim, months, f"{Y}-01", f"{Y}-12", cands)
        for c in cands:
            L = c.lag or 0
            beta = E.fit(tr[L], c)
            errs[c.key].append(va[L]["y"].to_numpy() - E.predict(va[L], c, beta))
        years.append(np.full(len(va[0]), Y))
    return {k: np.concatenate(v) for k, v in errs.items()}, np.concatenate(years)


def select_target(errs, years, cands):
    by = {c.key: c for c in cands}
    m = {k: mse(v) for k, v in errs.items()}
    best = min(m, key=m.get)
    uy = np.unique(years)
    rows = []
    for k, v in errs.items():
        d = np.square(v) - np.square(errs[best])
        yearly = np.array([d[years == y].mean() for y in uy])
        se = yearly.std(ddof=1) / np.sqrt(len(uy))
        clim_y = np.array([mse(errs["climatology"][years == y]) for y in uy])
        cand_y = np.array([mse(v[years == y]) for y in uy])
        rows.append({"candidate": k, "k": by[k].k, "val_mse": m[k], "val_rmse": np.sqrt(m[k]),
                     "excess_vs_best": d.mean(), "excess_se": se,
                     "val_msess": 1 - m[k] / m["climatology"],
                     "years_beating_climatology": int((cand_y < clim_y).sum())})
    tab = pd.DataFrame(rows).sort_values("val_mse").reset_index(drop=True)
    within = tab[tab.excess_vs_best <= tab.excess_se.fillna(0) + 1e-12]
    chosen = within.sort_values(["k", "val_mse"]).iloc[0]
    c = by[chosen.candidate]
    reliable = (c.name not in ("climatology", "persistence") and chosen.val_msess > 0.10
                and chosen.years_beating_climatology >= 4)
    return tab, chosen, bool(reliable)


def final_fit(rain, enso, months, c, n_boot=2000):
    clim = E.climatology(rain.loc["1998-01":FIT_END], FIT_END)
    fr = frames_for(rain, enso, clim, months, "1998-01", FIT_END, [c])[c.lag or 0]
    beta = E.fit(fr, c)
    resid = fr["y"].to_numpy() - E.predict(fr, c, beta)
    rng = np.random.default_rng(SEED)
    sy = S.season_year(fr.index)
    boots = np.array([E.fit(fr.iloc[i], c) for i in S.block_bootstrap_years(sy, n_boot, 2, rng)])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0) if len(beta) else ([], [])
    tr_clim = E.climatology(rain.loc["1998-01":TRAIN_END], TRAIN_END)
    tr = frames_for(rain, enso, tr_clim, months, "1998-01", TRAIN_END, [c])[c.lag or 0]
    beta_tr = E.fit(tr, c)
    names = E.coef_names(c)
    return {
        "coefficients": {n: {"value": float(b), "ci95": [float(l), float(h)], "units": unit_of(c, n),
                             "value_fit_1998_2013": float(bt)}
                         for n, b, l, h, bt in zip(names, beta, lo, hi, beta_tr)},
        "fit_period": ["1998-01", FIT_END.strftime("%Y-%m")], "n_fit": int(len(fr)),
        "in_sample_r2": float(1 - np.sum(resid ** 2) / np.sum((fr["y"] - fr["y"].mean()) ** 2)),
        "in_sample_rmse": float(np.sqrt(np.mean(resid ** 2))),
        "residual_lag1_acf": float(S.acf(resid, 1)[1]),
        "climatology_mm_month": {int(k): round(float(v), 3) for k, v in clim.items() if k in months},
    }


def unit_of(c, name):
    return {**c.units, "a": "mm/month"}.get(name, "mm/month per degC")


def phase_select():
    enso, rain = load()
    rows, choices = [], {}
    for reg in sorted(rain):
        for season, months in SEASONS.items():
            cands = E.candidates(months)
            errs, years = validate_target(rain[reg], enso, months, cands)
            tab, chosen, reliable = select_target(errs, years, cands)
            tab.insert(0, "season", season)
            tab.insert(0, "region", reg)
            rows.append(tab)
            choices[f"{reg}-{season}"] = {
                "region": reg, "season": season, "priority": (reg, season) in PRIORITY,
                "selected": chosen.candidate, "k": int(chosen.k), "val_rmse": float(chosen.val_rmse),
                "val_msess": float(chosen.val_msess),
                "years_beating_climatology": int(chosen.years_beating_climatology),
                "best_by_mse": tab.iloc[0].candidate, "reliable": reliable,
                "n_validation": int(len(years))}
    allv = pd.concat(rows)
    allv.to_csv(OUT / "stage_h_validation.csv", index=False)

    pri = [v for v in choices.values() if v["priority"] and v["reliable"]]
    headline = max(pri, key=lambda v: v["val_msess"]) if pri else None
    finals = {}
    for key, v in choices.items():
        months = SEASONS[v["season"]]
        c = next(c for c in E.candidates(months) if c.key == v["selected"])
        if c.name == "climatology":
            continue
        finals[key] = {"formula": c.formula, **final_fit(rain[v["region"]], enso, months, c)}
    sel = {
        "frozen_utc": utc_now(), "phase": "selection complete; test not yet run",
        "regions": f"regions{REGION_TAG}.json (k=3, climatology 1998-2013)",
        "validation_years": VAL_YEARS, "selection_rule": SELECTION_RULE, "headline_rule": HEADLINE_RULE,
        "priority_targets_post_hoc": [f"{r}-{s}" for r, s in PRIORITY],
        "n_candidates_per_target": len(E.candidates([1, 2, 3])),
        "choices": choices, "final_models": finals,
        "headline": headline and f"{headline['region']}-{headline['season']}",
        "validation_table_sha256": hashlib.sha256((OUT / "stage_h_validation.csv").read_bytes()).hexdigest(),
    }
    write_json(SEL_PATH, sel)
    for k, v in choices.items():
        print(f"{k:7s} pri={v['priority']!s:5s} sel={v['selected']:32s} k={v['k']} "
              f"valMSESS={v['val_msess']:+.3f} yrs>clim={v['years_beating_climatology']} rel={v['reliable']}")
    print("HEADLINE:", sel["headline"])


def phase_test():
    sel = read_json(SEL_PATH)
    if not sel:
        raise SystemExit("Run the select phase (and commit its output) first.")
    enso, rain = load()
    rows, preds = [], []
    for key, v in sel["choices"].items():
        months = SEASONS[v["season"]]
        r = rain[v["region"]]
        clim = E.climatology(r.loc["1998-01":FIT_END], FIT_END)
        cands = {c.key: c for c in E.candidates(months)}
        te = frames_for(r, enso, clim, months, TEST_START, TEST_END, list(cands.values()))
        fit_fr = frames_for(r, enso, clim, months, "1998-01", FIT_END, list(cands.values()))
        models = {"selected": cands[v["selected"]], "climatology": cands["climatology"],
                  "persistence": cands["persistence"], "linear@lag0": cands["linear@lag0"]}
        out = {}
        for lab, c in models.items():
            L = c.lag or 0
            beta = E.fit(fit_fr[L], c)
            p = E.predict(te[L], c, beta)
            out[lab] = te[L]["y"].to_numpy() - p
            if lab == "selected":
                f = te[L].assign(pred_anom=p, pred_total=p + te[L]["C"], region=v["region"],
                                 season=v["season"], model=c.key)
                preds.append(f.reset_index(names="month"))
        sy = S.season_year(te[0].index)
        rng = np.random.default_rng(SEED)
        bs = []
        for idx in S.block_bootstrap_years(sy, 2000, 2, rng):
            bs.append(1 - mse(out["selected"][idx]) / mse(out["climatology"][idx]))
        rows.append({"target": key, "selected": v["selected"], "priority": v["priority"],
                     "reliable_on_validation": v["reliable"], "n_test": len(out["selected"]),
                     "n_test_season_years": int(len(np.unique(sy))),
                     **{f"rmse_{k}": float(np.sqrt(mse(e))) for k, e in out.items()},
                     "msess_selected": 1 - mse(out["selected"]) / mse(out["climatology"]),
                     "msess_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                     "msess_linear_lag0": 1 - mse(out["linear@lag0"]) / mse(out["climatology"]),
                     "msess_persistence": 1 - mse(out["persistence"]) / mse(out["climatology"]),
                     "bias_selected": float(-np.mean(out["selected"]))})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "stage_h_test.csv", index=False)
    pr = pd.concat(preds)
    pr.to_csv(OUT / "stage_h_test_predictions.csv", index=False)

    h = sel["headline"]
    example = None
    if h:
        m = sel["final_models"][h]
        hp = pr[(pr.region + "-" + pr.season) == h]
        row = hp.loc[hp["x"].abs().idxmax()]
        coefs = {k: v["value"] for k, v in m["coefficients"].items()}
        example = {"target": h, "formula": m["formula"], "month": str(row["month"])[:7],
                   "inputs": {"x (RONI, degC)": float(row["x"]), "y(t-1) (mm/month)": float(row["y_prev"]),
                              "x_tend (degC)": float(row["x_tend"])},
                   "coefficients": coefs,
                   "climatology_mm_month": float(row["C"]),
                   "predicted_anomaly_mm_month": float(row["pred_anom"]),
                   "predicted_total_mm_month": float(row["pred_total"]),
                   "observed_total_mm_month": float(row["P"]),
                   "observed_anomaly_mm_month": float(row["y"]),
                   "error_mm_month": float(row["y"] - row["pred_anom"])}
    write_json(OUT / "stage_h_test.json", {"tested_utc": utc_now(), "selection_frozen_utc": sel["frozen_utc"],
                                           "selection_sha256": hashlib.sha256(SEL_PATH.read_bytes()).hexdigest(),
                                           "test_period": [TEST_START.strftime("%Y-%m"), TEST_END.strftime("%Y-%m")],
                                           "results": rows, "worked_example": example})
    print(res[["target", "selected", "n_test", "rmse_selected", "rmse_climatology", "msess_selected",
               "msess_ci95", "msess_linear_lag0", "msess_persistence"]].to_string(index=False))
    print(json.dumps(example, indent=1))


if __name__ == "__main__":
    {"select": phase_select, "test": phase_test}[sys.argv[1]]()
