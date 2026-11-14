"""Verify Stage H test metrics: identical observations and baseline for every compared model.

MSESS (mean-squared-error skill score vs climatology), per target:
    MSESS = 1 - sum_i (y_i - yhat_i)^2 / sum_i (y_i - 0)^2
where y_i is the observed rainfall anomaly (mm/month) in test month i relative to the
1998-01..2019-12 calendar-month climatology C(m), and the climatology baseline predicts
anomaly 0 (i.e. P = C(m)). All models are fitted on 1998-01..2019-12 and scored on the
same test months. This script does not re-select anything; it recomputes and asserts.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.argv = [sys.argv[0]]
import scripts.run_equation_search as H  # noqa: E402
from beyond_prediction import equations as E  # noqa: E402

enso, rain = H.load()
sel = json.load(open(H.SEL_PATH))
reported = pd.read_csv(H.OUT / "stage_h_test.csv").set_index("target")
out = {}
for target in ["R3-SON", "R1-SON"]:
    reg, season = target.split("-")
    months = H.SEASONS[season]
    r = rain[reg]
    clim = E.climatology(r.loc["1998-01":H.FIT_END], H.FIT_END)
    cands = {c.key: c for c in E.candidates(months)}
    te = H.frames_for(r, enso, clim, months, H.TEST_START, H.TEST_END, list(cands.values()))
    fit = H.frames_for(r, enso, clim, months, "1998-01", H.FIT_END, list(cands.values()))
    models = [sel["choices"][target]["selected"], "linear@lag0", "climatology", "persistence"]
    idx = {k: te[cands[k].lag or 0].index for k in models}
    y = {k: te[cands[k].lag or 0]["y"].to_numpy() for k in models}
    assert all(idx[k].equals(idx[models[0]]) for k in models), "different test months"
    assert all(np.array_equal(y[k], y[models[0]]) for k in models), "different observations"
    yy = y[models[0]]
    sse0 = float(np.sum(yy ** 2))
    res = {"n_test": len(yy), "months": [d.strftime("%Y-%m") for d in idx[models[0]]],
           "sse_climatology": sse0}
    for k in models:
        c = cands[k]
        f = te[c.lag or 0]
        e = yy - E.predict(f, c, E.fit(fit[c.lag or 0], c))
        res[k] = {"sse": float(np.sum(e ** 2)), "msess": 1 - float(np.sum(e ** 2)) / sse0}
    sel_key = models[0]
    assert abs(res[sel_key]["msess"] - reported.loc[target, "msess_selected"]) < 1e-9
    assert abs(res["linear@lag0"]["msess"] - reported.loc[target, "msess_linear_lag0"]) < 1e-9
    out[target] = res
    print(target, "n =", res["n_test"], {k: round(res[k]["msess"], 4) for k in models})
Path(H.OUT / "stage_h_metric_verification.json").write_text(json.dumps(
    {"definition": __doc__.strip(), "results": out}, indent=2) + "\n")
