"""Optional IOD sensitivity: does the Dipole Mode Index (DMI) alter the ENSO–rainfall results?

Source: NOAA PSL, HadISST1.1-based DMI (Saji-type definition stated in the file header:
SST anomaly 10S-10N, 50-70E minus 10S-0, 90-110E), monthly, 1870-present.
Alignment: the monthly DMI is re-anomalised against its own 1998-2019 calendar-month
mean (the file does not state its base period), then a centred 3-month mean
(t-1..t+1) is taken so that it is constructed like RONI.

Analyses (discovery period 1998-01..2019-12 only; the test period is NOT used):
  1. RONI–DMI correlation by season (collinearity).
  2. Lag-0 partial correlations of rainfall with RONI controlling for DMI and vice versa,
     main regions R1–R3, with effective-sample-size p-values and BH within this family.
  3. Headline-equation check: validation MSE (2014-2019) of the frozen R3-SON model with and
     without an added DMI term. This is NOT used to re-select the model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from beyond_prediction import equations as E  # noqa: E402
from beyond_prediction import stats as S  # noqa: E402
from beyond_prediction.provenance import DATA, ROOT, sha256_bytes, utc_now, write_json  # noqa: E402

URL = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data"
RAW = DATA / "raw" / "iod" / "dmi.had.long.data"
CFG = json.loads((ROOT / "config" / "analysis.json").read_text())
START, END = CFG["split"]["discovery_period"]


def parse_psl(text: str) -> pd.Series:
    lines = text.strip().splitlines()
    y0, y1 = map(int, lines[0].split()[:2])
    vals = {}
    for ln in lines[1:]:
        p = ln.split()
        if len(p) == 13 and p[0].isdigit() and y0 <= int(p[0]) <= y1:
            for m, v in enumerate(p[1:], 1):
                vals[pd.Timestamp(int(p[0]), m, 1)] = float(v)
    s = pd.Series(vals).sort_index()
    return s.where(s > -999)


def main() -> None:
    if not RAW.exists():
        r = requests.get(URL, timeout=60)
        r.raise_for_status()
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(r.content)
    raw = RAW.read_bytes()
    text = raw.decode()
    header = [ln.strip() for ln in text.strip().splitlines()[-6:]]
    dmi_m = parse_psl(text)
    base = dmi_m.loc[START:END]
    dmi_m = dmi_m - base.groupby(base.index.month).mean().reindex(dmi_m.index.month).to_numpy()
    dmi3 = dmi_m.rolling(3, center=True).mean()

    e = pd.read_csv(DATA / "processed" / "enso_monthly.csv", parse_dates=["date"]).set_index("date")
    roni = e["roni_anom_degC"]
    s = pd.read_csv(DATA / "processed" / "imerg_regional_monthly.csv")
    s["date"] = pd.to_datetime(s["month"] + "-01")
    s = s[s["date"] <= pd.Timestamp(END + "-01")]
    rain = {r: g.set_index("date")["precip_mm_month"].asfreq("MS") for r, g in s.groupby("region")}

    rows = []
    for reg in ["R1", "R2", "R3"]:
        x = rain[reg].loc[START:END]
        an = S.anomalies(x, S.monthly_climatology(x))["anom_mm"]
        acf_r = S.acf(an.to_numpy(), 24)
        for season, months in CFG["seasons"].items():
            pr = S.lagged_pairs(roni, an, months, 0, START, END)
            d = dmi3.reindex(pd.DatetimeIndex(pr["t_enso"])).to_numpy()
            xr, y = pr["enso"].to_numpy(), pr["rain"].to_numpy()

            def resid(a, b):
                b1 = np.column_stack([np.ones_like(b), b])
                return a - b1 @ np.linalg.lstsq(b1, a, rcond=None)[0]
            r_rd = S.pearson(xr, d)
            pr_roni = S.pearson(resid(xr, d), resid(y, d))
            pr_dmi = S.pearson(resid(d, xr), resid(y, xr))
            t = pd.DatetimeIndex(pr["t_rain"])
            neff = S.effective_n(t, S.acf(roni.loc[START:END].to_numpy(), 24), acf_r)
            neff_d = S.effective_n(t, S.acf(dmi3.loc[START:END].dropna().to_numpy(), 24), acf_r)
            rows.append({"region": reg, "season": season, "lag": 0, "n": len(y),
                         "r_roni_dmi": r_rd, "r_rain_roni": S.pearson(xr, y),
                         "r_rain_dmi": S.pearson(d, y),
                         "partial_r_roni_given_dmi": pr_roni,
                         "partial_r_dmi_given_roni": pr_dmi,
                         "n_eff_roni": neff, "n_eff_dmi": neff_d,
                         "p_ess_partial_roni": S.t_test_p(pr_roni, neff - 1),
                         "p_ess_partial_dmi": S.t_test_p(pr_dmi, neff_d - 1)})
    df = pd.DataFrame(rows)
    df["q_bh_partial_roni"] = S.benjamini_hochberg(df["p_ess_partial_roni"].to_numpy())
    df["q_bh_partial_dmi"] = S.benjamini_hochberg(df["p_ess_partial_dmi"].to_numpy())
    out = DATA / "results" / "iod_sensitivity.csv"
    df.to_csv(out, index=False)

    # 3. headline equation: validation-only comparison, no re-selection
    s3 = pd.read_csv(DATA / "processed" / "imerg_regional_monthly_k3train.csv")
    s3["date"] = pd.to_datetime(s3["month"] + "-01")
    r3 = s3[s3.region == "R3"].set_index("date")["precip_mm_month"].asfreq("MS").loc[:END]
    months = CFG["seasons"]["SON"]
    base_c = next(c for c in E.candidates(months) if c.key == "month-varying slope@lag0")
    errs = {"frozen": [], "frozen+DMI": []}
    for Y in range(2014, 2020):
        fe = pd.Timestamp(f"{Y - 1}-12-01")
        clim = E.climatology(r3.loc[:fe], fe)
        tr = E.frame(r3, roni, clim, months, 0, "1998-01", fe)
        va = E.frame(r3, roni, clim, months, 0, f"{Y}-01", f"{Y}-12")
        for f in (tr, va):
            f["dmi"] = dmi3.reindex(f.index).to_numpy()
        b = E.fit(tr, base_c)
        errs["frozen"].append(va["y"] - E.predict(va, base_c, b))
        X = np.column_stack([E.design(tr, base_c), tr["dmi"]])
        bd = np.linalg.lstsq(X, tr["y"].to_numpy(), rcond=None)[0]
        errs["frozen+DMI"].append(va["y"] - np.column_stack([E.design(va, base_c), va["dmi"]]) @ bd)
    val = {k: float(np.sqrt(np.mean(np.square(np.concatenate(v))))) for k, v in errs.items()}

    write_json(DATA / "provenance" / "iod.json", {
        "built_utc": utc_now(), "source_url": URL, "sha256": sha256_bytes(raw),
        "file_header": header, "definition_page_status": "landing page linked in file returned HTTP 404",
        "base_period": "not stated in file; re-anomalised against 1998-2019 calendar-month means",
        "temporal_alignment": "centred 3-month mean (t-1..t+1), matching RONI's construction",
        "permissions": "public NOAA PSL data; host psl.noaa.gov added to the environment allowlist",
        "period_used": [START, END], "test_period_used": False,
        "headline_validation_rmse_2014_2019": val,
        "results_file": str(out.relative_to(DATA.parent)),
    })
    pd.set_option("display.width", 220)
    print(df.drop(columns=["n", "lag"]).round(3).to_string(index=False))
    print("R3-SON validation RMSE:", val)


if __name__ == "__main__":
    main()
