import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from beyond_prediction import network as N  # noqa: E402

RES = ROOT / "data" / "results"


def _g(rs, lo, hi):
    return pd.DataFrame({"window": [f"w{i}" for i in range(len(rs))], "r": rs, "ci_lo": lo, "ci_hi": hi})


def test_pattern_rules():
    assert N.pattern(_g([-.5] * 12, [-.7] * 12, [-.2] * 12)) == "recurring"
    assert N.pattern(_g([-.5] * 12, [-.7] * 12, [-.2] * 8 + [.1] * 4)) == "weak-recurring"
    assert N.pattern(_g([-.5] * 6 + [.4] * 6, [-.7] * 6 + [.1] * 6, [-.2] * 6 + [.6] * 6)) == "divergent"
    assert N.pattern(_g([-.1] * 6 + [.1] * 6, [-.4] * 12, [.3] * 12)) == "sign-variable"


def test_status_rules():
    full = pd.Series({"window": N.FULL, "kind": "ENSO-region", "q_bh": 0.2, "ci_lo": -.6, "ci_hi": -.1})
    assert N.edge_status(full) == "inconclusive"          # q governs the full-period ENSO edges
    win = pd.Series({"window": "2000-2010", "kind": "ENSO-region", "q_bh": float("nan"),
                     "ci_lo": -.6, "ci_hi": -.1})
    assert N.edge_status(win) == "CI excludes 0"


@pytest.mark.skipif(not (RES / "network_edges.csv").exists(), reason="network not built")
def test_every_enso_edge_comes_from_stage_f():
    e = pd.read_csv(RES / "network_edges.csv")
    p = pd.read_csv(RES / "associations_primary.csv")
    r = pd.read_csv(RES / "rolling.csv")
    full = e[(e.kind == "ENSO-region") & (e.window == N.FULL)].merge(
        p, left_on=["target", "season", "lag"], right_on=["region", "season", "lag"], suffixes=("", "_f"))
    assert len(full) == 48 and (full.r == full.r_f).all() and (full.q_bh == full.q_bh_surrogate).all()
    roll = e[(e.kind == "ENSO-region") & (e.window != N.FULL)].merge(
        r, left_on=["target", "season", "lag", "window"], right_on=["region", "season", "lag", "window"],
        suffixes=("", "_f"))
    assert len(roll) == len(r) and (roll.r == roll.r_f).all()
    assert set(e.kind) == {"ENSO-region", "region-region"}


@pytest.mark.skipif(not (RES / "network_edges.csv").exists(), reason="network not built")
def test_app_network_controls_change_displayed_data():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    at.button[0].click().run()
    assert not at.exception

    def table():
        return next(d for d in at.dataframe if "status" in d.value.columns and "window" in d.value.columns).value

    base = table()
    assert set(base.loc[base.kind == "ENSO-region", "lag"]) == {0}
    at.radio(key="net_season").set_value("DJF").run()
    djf = table()
    assert not djf["r"].reset_index(drop=True).equals(base["r"].reset_index(drop=True))
    at.selectbox(key="net_lag").set_value(2).run()
    lag2 = table()
    assert set(lag2.loc[lag2.kind == "ENSO-region", "lag"]) == {2}
    at.selectbox(key="net_window").set_value("2005-2015").run()
    win = table()
    assert set(win.window) == {"2005-2015"}
    at.checkbox(key="net_rr").uncheck().run()
    assert set(table().kind) == {"ENSO-region"}
    assert not at.exception
