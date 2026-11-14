"""Stage I: primary candidate hypothesis — does the DJF ENSO–rainfall coefficient differ
between eastern Indonesia (R3) and R1/R2?

Pre-stated specification (written before running):
  Coefficient   beta_k = OLS slope of rainfall anomaly (mm/month) on RONI (degC), DJF rainfall
                months, lag 0 (RONI centred on the rainfall month), region k.
  H0            beta_R3 = beta_R1   and   beta_R3 = beta_R2   (two contrasts)
  H1            beta_R3 != beta_Rk  (two-sided); the Stage F direction suggests beta_R3 < beta_Rk.
  Direct test   Because all regions share the same RONI values and months,
                beta_R3 - beta_Rk = slope of d(t) = y_R3(t) - y_Rk(t) on RONI(t) exactly.
                The contrast is therefore tested as one regression, which keeps shared ENSO
                observations and cross-region rainfall correlation intact.
  Inference     (1) phase-randomised RONI surrogates (persistence-preserving), 2000 draws;
                (2) effective-sample-size t-test from the ACFs of RONI and d;
                (3) 95% CI from a joint 2-year moving-block bootstrap of season-years
                    (all regions resampled together).
                Holm correction across the 2 contrasts (surrogate p is primary).
  Decision      "Supported in the discovery data" if both Holm-adjusted surrogate p < 0.05 and both
                bootstrap CIs exclude 0. Otherwise "not supported".
Data roles
  A. Discovery data 1998-01..2019-12, main regions (the data that generated the hypothesis):
     IN-SAMPLE test, not confirmatory.
  B. Held-out period 2020-01..2025-09, training-derived regions (k3train), climatology 1998-2019:
     temporal held-out check. These months were already used for the Stage H evaluation (no selection
     was based on them). Low power (17 DJF months). NOT independent external validation.
  C. Sensitivities: k3train regions on discovery data; standardised anomalies; lags 1-3.
Output: data/results/stage_i_hypothesis.json, stage_i_djf_points.csv, stage_i_equation_panel.csv
"""

from __future__ import annotations

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
DJF = CFG["seasons"]["DJF"]
D0, D1 = CFG["split"]["discovery_period"]
T0, T1 = CFG["split"]["test"]
RES = DATA / "results"
SEED = CFG["inference"]["seed"]
NSUR, NBOOT = 2000, 2000


def load(tag=""):
    e = pd.read_csv(DATA / "processed" / "enso_monthly.csv", parse_dates=["date"]).set_index("date")
    s = pd.read_csv(DATA / "processed" / f"imerg_regional_monthly{tag}.csv")
    s["date"] = pd.to_datetime(s["month"] + "-01")
    rain = {r: g.set_index("date")["precip_mm_month"].astype(float).asfreq("MS") for r, g in s.groupby("region")}
    return e["roni_anom_degC"], rain


def anoms(rain, clim_start, clim_end, standardise=False):
    out = {}
    for r, x in rain.items():
        c = S.monthly_climatology(x.loc[clim_start:clim_end])
        a = S.anomalies(x, c)
        out[r] = a["anom_std" if standardise else "anom_mm"]
    return out


def test_block(roni, an, start, end, lag, rng, label):
    """Regional slopes + direct contrasts for DJF rainfall months in [start, end]."""
    pairs = {r: S.lagged_pairs(roni, an[r], DJF, lag, start, end) for r in ["R1", "R2", "R3"]}
    t = pd.DatetimeIndex(pairs["R3"]["t_rain"])
    assert all(pd.DatetimeIndex(p["t_rain"]).equals(t) for p in pairs.values()), "months differ"
    x = pairs["R3"]["enso"].to_numpy()
    y = {r: p["rain"].to_numpy() for r, p in pairs.items()}
    sy = S.season_year(t)
    boots = S.block_bootstrap_years(sy, NBOOT, 2, rng)
    slopes = {r: {"beta": S.ols_slope(x, y[r]), "r": S.pearson(x, y[r])} for r in y}
    for r in y:
        b = [S.ols_slope(x[i], y[r][i]) for i in boots]
        slopes[r]["ci95"] = [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]

    # surrogates of RONI over the span needed
    lo = t.min() - pd.DateOffset(months=lag)
    span = roni.loc[lo:t.max()]
    pos = pd.Series(np.arange(len(span)), index=span.index).reindex(t - pd.DateOffset(months=lag)).to_numpy()
    sur = S.phase_surrogates(span.to_numpy(), NSUR, rng)[:, pos]
    sur_c = sur - sur.mean(axis=1, keepdims=True)
    acf_x = S.acf(span.to_numpy(), 24)

    contrasts = {}
    for k in ["R1", "R2"]:
        d = y["R3"] - y[k]
        beta = S.ols_slope(x, d)
        bs = np.array([S.ols_slope(x[i], d[i]) for i in boots])
        dc = d - d.mean()
        bsur = (sur_c @ dc) / (sur_c * sur_c).sum(axis=1)
        p_sur = (1 + np.sum(np.abs(bsur) >= abs(beta))) / (1 + NSUR)
        dser = (an["R3"] - an[k]).loc[start:end].dropna().to_numpy()
        neff = S.effective_n(t, acf_x, S.acf(dser, 24))
        r_d = S.pearson(x, d)
        contrasts[f"R3-{k}"] = {
            "delta_beta": beta, "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "p_surrogate": float(p_sur), "n_eff": neff, "p_ess": S.t_test_p(r_d, neff),
            "check_equals_difference_of_slopes": abs(beta - (slopes["R3"]["beta"] - slopes[k]["beta"])) < 1e-9}
    ps = np.array([contrasts[c]["p_surrogate"] for c in contrasts])
    for c, ph in zip(contrasts, S.holm(ps)):
        contrasts[c]["p_holm_surrogate"] = float(ph)
    excl = all(v["ci95"][0] > 0 or v["ci95"][1] < 0 for v in contrasts.values())
    supported = all(v["p_holm_surrogate"] < 0.05 for v in contrasts.values()) and excl
    pts = pd.DataFrame({"date": t, "roni": x, **{f"anom_{r}": y[r] for r in y}, "block": label})
    return {"label": label, "period": [start, end], "lag": lag, "n_months": int(len(x)),
            "n_season_years": int(len(np.unique(sy))), "slopes": slopes, "contrasts": contrasts,
            "decision_rule_met": bool(supported)}, pts


def equation_panel():
    """Per held-out R3-SON month: frozen equation, linear lag-0 and climatology references."""
    sel = read_json(RES / "stage_h_selection.json")
    roni, rain = load("_k3train")
    r3 = rain["R3"]
    months = CFG["seasons"]["SON"]
    fit_end = pd.Timestamp(D1 + "-01")
    clim = E.climatology(r3.loc[:fit_end], fit_end)
    cands = {c.key: c for c in E.candidates(months)}
    fr_fit = E.frame(r3, roni, clim, months, 0, "1998-01", fit_end)
    fr_te = E.frame(r3, roni, clim, months, 0, T0, T1)
    frozen = cands[sel["choices"]["R3-SON"]["selected"]]
    lin = cands["linear@lag0"]
    b_lin = E.fit(fr_fit, lin)
    coefs = {k: v["value"] for k, v in sel["final_models"]["R3-SON"]["coefficients"].items()}
    out = fr_te[["x", "P", "C", "y", "month"]].copy()
    out["pred_frozen"] = out["C"] + coefs["a"] + out["month"].map(
        {9: coefs["b_m9"], 10: coefs["b_m10"], 11: coefs["b_m11"]}) * out["x"]
    out["pred_linear_lag0"] = out["C"] + b_lin[0] + b_lin[1] * out["x"]
    out["pred_climatology"] = out["C"]
    assert np.allclose(out["pred_frozen"] - out["C"], E.predict(fr_te, frozen, E.fit(fr_fit, frozen)))
    out = out.reset_index(names="date")
    out.to_csv(RES / "stage_i_equation_panel.csv", index=False)
    return {"frozen_model": frozen.key, "frozen_coefficients": coefs,
            "linear_lag0_coefficients": {"a": float(b_lin[0]), "b": float(b_lin[1])},
            "climatology_mm_month": {int(k): float(v) for k, v in clim.items() if k in months}}


def main() -> None:
    rng = np.random.default_rng(SEED)
    roni, rain_main = load()
    _, rain_tr = load("_k3train")
    a_main = anoms(rain_main, D0, D1)
    primary, pts = test_block(roni, a_main, D0, D1, 0, rng, "A: discovery 1998-2019 (in-sample)")
    a_tr = anoms(rain_tr, D0, D1)                      # climatology from 1998-2019 only
    held, pts_h = test_block(roni, a_tr, T0, T1, 0, rng, "B: held-out 2020-2025 (temporal check)")
    sens = {
        "k3train regions, discovery": test_block(roni, a_tr, D0, D1, 0, rng, "C1")[0],
        "standardised anomalies, discovery": test_block(roni, anoms(rain_main, D0, D1, True), D0, D1, 0, rng, "C2")[0],
        **{f"lag {L}, discovery": test_block(roni, a_main, D0, D1, L, rng, f"C3-lag{L}")[0] for L in (1, 2, 3)},
    }
    pd.concat([pts, pts_h]).to_csv(RES / "stage_i_djf_points.csv", index=False)
    a_ok = primary["decision_rule_met"]
    h = held["contrasts"]
    same_sign = all(np.sign(h[c]["delta_beta"]) == np.sign(primary["contrasts"][c]["delta_beta"]) for c in h)
    write_json(RES / "stage_i_hypothesis.json", {
        "built_utc": utc_now(),
        "hypothesis": {
            "statement": ("During DJF, the association between RONI and monthly rainfall anomalies in eastern "
                          "Indonesia (R3) differs from that in R1 and R2: R3 rainfall decreases more per degC of RONI."),
            "H0": "beta_R3 = beta_R1 and beta_R3 = beta_R2 (DJF, lag 0, mm/month per degC)",
            "H1": "beta_R3 != beta_R1 and beta_R3 != beta_R2 (expected direction: beta_R3 < beta_Rk)",
            "falsification": ("Rejected in new data if the R3-minus-Rk slope contrasts are not negative with 95% "
                              "CIs excluding 0 in an independent rainfall product or gauge network (e.g. CHIRPS, "
                              "BMKG stations) over the same or later years."),
            "spec": __doc__.split("Data roles")[0].strip(),
        },
        "A_primary_in_sample": primary, "B_held_out": held, "C_sensitivity": sens,
        "conclusion": {
            "in_sample": ("decision rule met: both direct contrasts differ from 0 (Holm surrogate p < 0.05, CIs "
                          "exclude 0)" if a_ok else "decision rule NOT met in the discovery data"),
            "held_out": (f"same sign as discovery for both contrasts: {same_sign}; "
                         + "; ".join(f"{c}: {h[c]['delta_beta']:+.1f} [{h[c]['ci95'][0]:+.1f}, {h[c]['ci95'][1]:+.1f}] "
                                     f"Holm p={h[c]['p_holm_surrogate']:.3f}" for c in h)),
            "status": "candidate hypothesis; not independently validated",
        },
        "equation_panel": equation_panel(),
    })
    for blk in [primary, held] + list(sens.values()):
        print(blk["label"], blk["n_months"], {r: round(v["beta"], 2) for r, v in blk["slopes"].items()},
              {c: (round(v["delta_beta"], 2), [round(q, 1) for q in v["ci95"]], round(v["p_surrogate"], 4),
                   round(v["p_holm_surrogate"], 4), round(v["p_ess"], 4)) for c, v in blk["contrasts"].items()},
              "RULE MET" if blk["decision_rule_met"] else "rule not met")


if __name__ == "__main__":
    main()
