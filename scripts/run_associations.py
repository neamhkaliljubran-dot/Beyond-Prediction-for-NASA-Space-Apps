"""Stage F: ENSO–Indonesian rainfall association analysis (exploratory).

Reads config/analysis.json. Uses ONLY the discovery period (train + validation);
rainfall rows after it are dropped immediately after loading and never used.

Outputs (data/results/):
  associations_primary.csv       RONI x R1-R3 x 4 seasons x lags 0-3 (48 tests, BH within)
  associations_oni.csv           sensitivity: ONI, same 48 cells, separate BH
  associations_all_indonesia.csv sensitivity: RONI x ALL, separate BH
  associations_k2.csv            sensitivity: RONI x k=2 regions, separate BH
  associations_k3train.csv       sensitivity: RONI x k=3 regions fitted on 1998-2013 only
  seasonal_aggregate.csv         robustness: seasonal means vs centre-month ENSO, lag 0
  illustrative_family.csv        SON, RONI, lag 0, R1-R3, Holm (illustrative only)
  rolling.csv                    11-yr windows stepped 1 yr (exploratory)
  halves.csv                     1998-2008 vs 2009-2019 (non-overlapping), bootstrap diff
  stage_f_summary.json           diagnostics + provenance
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from beyond_prediction import stats as S  # noqa: E402
from beyond_prediction.provenance import DATA, ROOT, utc_now, write_json  # noqa: E402

CFG_PATH = ROOT / "config" / "analysis.json"
CFG = json.loads(CFG_PATH.read_text())
OUT = DATA / "results"
START, END = CFG["split"]["discovery_period"]
SEASONS = CFG["seasons"]
LAGS = CFG["lags_months"]
INF = CFG["inference"]


# ----------------------------------------------------------------- loading
def load_enso() -> pd.DataFrame:
    e = pd.read_csv(DATA / "processed" / "enso_monthly.csv", parse_dates=["date"]).set_index("date")
    return e[["roni_anom_degC", "oni_anom_degC"]]


def load_rain(tag: str = "") -> dict[str, pd.Series]:
    s = pd.read_csv(DATA / "processed" / f"imerg_regional_monthly{tag}.csv")
    s["date"] = pd.to_datetime(s["month"] + "-01")
    s = s[(s["date"] >= pd.Timestamp(START + "-01")) & (s["date"] <= pd.Timestamp(END + "-01"))]
    assert s["date"].max() <= pd.Timestamp(END + "-01"), "test period leaked into Stage F"
    return {r: g.set_index("date")["precip_mm_month"].astype(float).asfreq("MS")
            for r, g in s.groupby("region")}


def make_anoms(rain: dict[str, pd.Series]) -> tuple[dict[str, pd.DataFrame], dict]:
    out, clims = {}, {}
    for r, x in rain.items():
        if x.isna().any():
            raise ValueError(f"{r}: missing months in discovery period")
        c = S.monthly_climatology(x)
        out[r] = S.anomalies(x, c)
        clims[r] = c.round(3).to_dict()
    return out, clims


# ----------------------------------------------------------------- core analysis
class Engine:
    def __init__(self, enso: pd.Series, rng: np.random.Generator):
        self.enso = enso
        lo = pd.Timestamp(START + "-01") - pd.DateOffset(months=max(LAGS))
        self.span = enso.loc[lo:pd.Timestamp(END + "-01")]
        if self.span.isna().any():
            raise ValueError("ENSO gaps in analysis span")
        self.pos = pd.Series(np.arange(len(self.span)), index=self.span.index)
        self.sur = S.phase_surrogates(self.span.to_numpy(), INF["n_surrogates"], rng)
        self.acf_e = S.acf(self.span.loc[START:END].to_numpy(), INF["ess_max_lag"])
        self.rng = rng
        self._boot = {}

    def boot_rows(self, key, years, n_boot):
        k = (key, n_boot, len(years))
        if k not in self._boot:
            self._boot[k] = S.block_bootstrap_years(years, n_boot, 2, self.rng)
        return self._boot[k]

    def cell(self, an: pd.DataFrame, season: str, lag: int, start=START, end=END,
             n_boot=INF["n_bootstrap"], surrogate=True, acf_r=None) -> dict:
        p = S.lagged_pairs(self.enso, an["anom_mm"], SEASONS[season], lag, start, end)
        pz = S.lagged_pairs(self.enso, an["anom_std"], SEASONS[season], lag, start, end)
        pp = S.lagged_pairs(self.enso, an["anom_pct"], SEASONS[season], lag, start, end)
        x, y = p["enso"].to_numpy(), p["rain"].to_numpy()
        n = len(x)
        r = S.pearson(x, y)
        res = {"season": season, "lag": lag, "n": n,
               "r": r, "spearman": S.spearman(x, y),
               "slope_mm_per_degC": S.ols_slope(x, y),
               "r_std_anom": S.pearson(pz["enso"].to_numpy(), pz["rain"].to_numpy()),
               "slope_std_per_degC": S.ols_slope(pz["enso"].to_numpy(), pz["rain"].to_numpy()),
               "slope_pct_per_degC": S.ols_slope(pp["enso"].to_numpy(), pp["rain"].to_numpy())}
        years = S.season_year(pd.DatetimeIndex(p["t_rain"]))
        res["n_season_years"] = int(len(np.unique(years)))
        rows = self.boot_rows((season, lag, start, end), years, n_boot)
        br = np.array([S.pearson(x[i], y[i]) for i in rows])
        bs = np.array([S.ols_slope(x[i], y[i]) for i in rows])
        res.update(r_ci_lo=np.percentile(br, 2.5), r_ci_hi=np.percentile(br, 97.5),
                   slope_ci_lo=np.percentile(bs, 2.5), slope_ci_hi=np.percentile(bs, 97.5))
        if surrogate:
            idx = self.pos.reindex(pd.DatetimeIndex(p["t_enso"])).to_numpy()
            xs = self.sur[:, idx]
            xs = xs - xs.mean(axis=1, keepdims=True)
            yc = y - y.mean()
            rs = (xs @ yc) / np.sqrt((xs * xs).sum(axis=1) * (yc @ yc))
            res["p_surrogate"] = (1 + np.sum(np.abs(rs) >= abs(r))) / (1 + len(rs))
            res["n_eff"] = S.effective_n(pd.DatetimeIndex(p["t_rain"]), self.acf_e, acf_r)
            res["p_ess"] = S.t_test_p(r, res["n_eff"])
        return res


def family(engine: Engine, anoms: dict, regions: list[str], label: str) -> pd.DataFrame:
    rows = []
    for reg in regions:
        acf_r = S.acf(anoms[reg]["anom_mm"].loc[START:END].to_numpy(), INF["ess_max_lag"])
        for season in SEASONS:
            for lag in LAGS:
                rows.append({"family": label, "region": reg,
                             **engine.cell(anoms[reg], season, lag, acf_r=acf_r)})
    df = pd.DataFrame(rows)
    df["q_bh_surrogate"] = S.benjamini_hochberg(df["p_surrogate"].to_numpy())
    df["q_bh_ess"] = S.benjamini_hochberg(df["p_ess"].to_numpy())
    df["family_size"] = len(df)
    return df


def seasonal_aggregate(enso: pd.Series, anoms: dict, regions: list[str], label: str) -> pd.DataFrame:
    centre = {"DJF": 1, "MAM": 4, "JJA": 7, "SON": 10}
    rows = []
    for reg in regions:
        a = anoms[reg]["anom_mm"].loc[START:END]
        for season, months in SEASONS.items():
            sub = a[a.index.month.isin(months)]
            sy = S.season_year(sub.index)
            g = sub.groupby(sy).agg(["mean", "size"])
            g = g[g["size"] == 3]["mean"]
            e = enso.reindex(pd.to_datetime([f"{y}-{centre[season]:02d}-01" for y in g.index])).to_numpy()
            x, y = e, g.to_numpy()
            r = S.pearson(x, y)
            r1x, r1y = S.acf(x, 1)[1], S.acf(y, 1)[1]
            neff = min(len(x), len(x) * (1 - r1x * r1y) / (1 + r1x * r1y))
            rows.append({"family": label, "region": reg, "season": season, "lag": 0,
                         "n_season_years": len(x), "r": r,
                         "slope_mm_per_degC": S.ols_slope(x, y),
                         "lag1_acf_enso": r1x, "lag1_acf_rain": r1y,
                         "n_eff_ar1": neff, "p_ess": S.t_test_p(r, neff)})
    df = pd.DataFrame(rows)
    df["q_bh_ess"] = S.benjamini_hochberg(df["p_ess"].to_numpy())
    return df


def rolling(engine: Engine, anoms: dict, regions: list[str]) -> pd.DataFrame:
    w = CFG["rolling"]["window_years"]
    y0, y1 = int(START[:4]), int(END[:4])
    rows = []
    for s in range(y0, y1 - w + 2, CFG["rolling"]["step_years"]):
        e_ = s + w - 1
        # Season-year window [s, e_]: DJF of year s starts in Dec s-1, so start in Dec s-1
        # but never before the discovery period; Dec of the last year belongs to e_+1.
        start = max(pd.Timestamp(f"{s - 1}-12-01"), pd.Timestamp(START + "-01")).strftime("%Y-%m")
        end = f"{e_}-11"
        for reg in regions:
            for season in SEASONS:
                for lag in LAGS:
                    c = engine.cell(anoms[reg], season, lag, start, end,
                                    n_boot=CFG["rolling"]["n_bootstrap"], surrogate=False)
                    rows.append({"window": f"{s}-{e_}", "start_year": s, "end_year": e_,
                                 "region": reg, **c})
    return pd.DataFrame(rows)


def halves(engine: Engine, anoms: dict, regions: list[str]) -> pd.DataFrame:
    a_start, a_end, b_start, b_end = "1998-01", "2008-11", "2008-12", END
    rows = []
    for reg in regions:
        for season in SEASONS:
            for lag in LAGS:
                A = engine.cell(anoms[reg], season, lag, a_start, a_end, n_boot=1000, surrogate=False)
                B = engine.cell(anoms[reg], season, lag, b_start, b_end, n_boot=1000, surrogate=False)
                pa = S.lagged_pairs(engine.enso, anoms[reg]["anom_mm"], SEASONS[season], lag, a_start, a_end)
                pb = S.lagged_pairs(engine.enso, anoms[reg]["anom_mm"], SEASONS[season], lag, b_start, b_end)
                ra = engine.boot_rows((season, lag, a_start, a_end), S.season_year(pd.DatetimeIndex(pa.t_rain)), 1000)
                rb = engine.boot_rows((season, lag, b_start, b_end), S.season_year(pd.DatetimeIndex(pb.t_rain)), 1000)
                xa, ya = pa.enso.to_numpy(), pa.rain.to_numpy()
                xb, yb = pb.enso.to_numpy(), pb.rain.to_numpy()
                d = np.array([S.pearson(xb[j], yb[j]) - S.pearson(xa[i], ya[i]) for i, j in zip(ra, rb)])
                rows.append({"region": reg, "season": season, "lag": lag,
                             "r_1998_2008": A["r"], "n_1998_2008": A["n"],
                             "r_2009_2019": B["r"], "n_2009_2019": B["n"],
                             "delta_r": B["r"] - A["r"],
                             "delta_ci_lo": np.percentile(d, 2.5), "delta_ci_hi": np.percentile(d, 97.5)})
    return pd.DataFrame(rows)


def main() -> None:
    t0 = time.time()
    rng = np.random.default_rng(INF["seed"])
    OUT.mkdir(parents=True, exist_ok=True)
    enso = load_enso()
    rain3, rain2, rain3t = load_rain(), load_rain("_k2"), load_rain("_k3train")
    an3, clim3 = make_anoms(rain3)
    an2, _ = make_anoms(rain2)
    an3t, _ = make_anoms(rain3t)

    roni = Engine(enso["roni_anom_degC"], rng)
    oni = Engine(enso["oni_anom_degC"], rng)
    regs = CFG["primary_regions"]

    prim = family(roni, an3, regs, "PRIMARY: RONI x R1-R3 (48)")
    prim.to_csv(OUT / "associations_primary.csv", index=False)
    family(oni, an3, regs, "SENSITIVITY: ONI x R1-R3").to_csv(OUT / "associations_oni.csv", index=False)
    family(roni, an3, ["ALL"], "SENSITIVITY: RONI x Indonesia-wide").to_csv(
        OUT / "associations_all_indonesia.csv", index=False)
    family(roni, an2, ["R1", "R2"], "SENSITIVITY: RONI x k=2 regions").to_csv(
        OUT / "associations_k2.csv", index=False)
    family(roni, an3t, ["R1", "R2", "R3"], "SENSITIVITY: RONI x k=3 regions fitted 1998-2013").to_csv(
        OUT / "associations_k3train.csv", index=False)
    seasonal_aggregate(enso["roni_anom_degC"], an3, regs, "ROBUSTNESS: seasonal means, RONI").to_csv(
        OUT / "seasonal_aggregate.csv", index=False)

    ill = prim[(prim.season == "SON") & (prim.lag == 0)].copy()
    ill["p_holm_surrogate"] = S.holm(ill["p_surrogate"].to_numpy())
    ill["p_holm_ess"] = S.holm(ill["p_ess"].to_numpy())
    ill["status"] = CFG["illustrative_family"]["status"]
    ill.to_csv(OUT / "illustrative_family.csv", index=False)

    rolling(roni, an3, regs).to_csv(OUT / "rolling.csv", index=False)
    halves(roni, an3, regs).to_csv(OUT / "halves.csv", index=False)

    diag = {
        "lag1_acf": {"RONI": float(roni.acf_e[1]), "ONI": float(oni.acf_e[1]),
                     **{r: float(S.acf(an3[r]["anom_mm"].to_numpy(), 1)[1]) for r in an3}},
        "acf_RONI_lags_0_24": [round(float(v), 3) for v in roni.acf_e],
    }
    write_json(OUT / "stage_f_summary.json", {
        "built_utc": utc_now(), "runtime_s": round(time.time() - t0, 1),
        "config_sha256": hashlib.sha256(CFG_PATH.read_bytes()).hexdigest(),
        "discovery_period": [START, END], "test_period_read": False,
        "n_months_discovery": int(len(rain3["R1"])),
        "climatology_stage_f": clim3, "diagnostics": diag,
        "regions_source": {"main": "regions.json (k=3, climatology 1998-2024: overlaps test period)",
                           "k3train": "regions_k3train.json (k=3, climatology 1998-2013)",
                           "k2": "regions_k2.json"},
    })
    print(f"Stage F done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
