import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RES = ROOT / "data" / "results"
HYP = RES / "stage_i_hypothesis.json"
pytestmark = pytest.mark.skipif(not HYP.exists(), reason="Stage I not built")


def test_contrast_equals_difference_of_regional_slopes():
    h = json.loads(HYP.read_text())
    for blk in [h["A_primary_in_sample"], h["B_held_out"], *h["C_sensitivity"].values()]:
        for c, v in blk["contrasts"].items():
            k = c.split("-")[1]
            assert v["check_equals_difference_of_slopes"]
            assert v["delta_beta"] == pytest.approx(blk["slopes"]["R3"]["beta"] - blk["slopes"][k]["beta"])


def test_decision_follows_prestated_rule():
    h = json.loads(HYP.read_text())
    for blk in [h["A_primary_in_sample"], h["B_held_out"], *h["C_sensitivity"].values()]:
        c = blk["contrasts"].values()
        rule = all(v["p_holm_surrogate"] < 0.05 for v in c) and all(v["ci95"][0] > 0 or v["ci95"][1] < 0 for v in c)
        assert blk["decision_rule_met"] == rule


def test_frozen_selection_preserved():
    t = json.loads((RES / "stage_h_test.json").read_text())
    assert hashlib.sha256((RES / "stage_h_selection.json").read_bytes()).hexdigest() == t["selection_sha256"]
    sel = json.loads((RES / "stage_h_selection.json").read_text())
    h = json.loads(HYP.read_text())["equation_panel"]
    assert h["frozen_model"] == sel["choices"]["R3-SON"]["selected"]
    assert h["frozen_coefficients"] == {k: v["value"] for k, v in sel["final_models"]["R3-SON"]["coefficients"].items()}


def test_equation_panel_matches_stage_h_predictions():
    ep = pd.read_csv(RES / "stage_i_equation_panel.csv", parse_dates=["date"])
    hp = pd.read_csv(RES / "stage_h_test_predictions.csv", parse_dates=["date"])
    hp = hp[(hp.region == "R3") & (hp.season == "SON")].set_index("date")
    ep = ep.set_index("date")
    assert ep.index.equals(hp.index) and len(ep) == 16
    assert np.allclose(ep.pred_frozen, hp.pred_total)
    assert np.allclose(ep.P, hp.P)


def test_app_verification_panels_respond():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    at.button[0].click().run()
    assert not at.exception

    def df_with(col):
        return next(d for d in at.dataframe if col in d.value.columns).value

    first = df_with("estimate − observed (mm/month)")
    at.selectbox(key="eq_month").set_value("2023-10").run()
    second = df_with("estimate − observed (mm/month)")
    assert not np.allclose(first["estimate (mm/month)"], second["estimate (mm/month)"])
    assert second.iloc[3]["estimate (mm/month)"] == pytest.approx(144.07, abs=0.01)   # IMERG Oct 2023, R3

    a = df_with("Δβ = β_R3 − β_Rk")
    blocks = at.selectbox(key="hyp_block").options
    at.selectbox(key="hyp_block").set_value(blocks[1]).run()
    b = df_with("Δβ = β_R3 − β_Rk")
    assert not np.allclose(a["Δβ = β_R3 − β_Rk"], b["Δβ = β_R3 − β_Rk"])
    assert not at.exception


def test_presentation_journey_and_text():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    landing = " ".join(m.value for m in at.markdown)
    assert "<h1>Meta Prediction</h1>" in landing
    assert "An Earth System Hypothesis Discovery Engine" in landing
    assert at.button[0].label.startswith("How do relationships between ENSO variability")
    at.button[0].click().run()
    assert not at.exception
    heads = [h.value for h in at.subheader]
    order = ["The hypothesis — and its honest test", "The equation — discovered, frozen and tested",
             "What the real data show", "The dynamic scientific network", "Four scientific answers"]
    pos = [next(i for i, h in enumerate(heads) if h == s) for s in order]
    assert pos == sorted(pos), heads
    md = " ".join(m.value for m in at.markdown)
    assert "“The universe whispers in patterns. Discovery begins when we learn to listen.”" in md
    assert "PYRAMID" not in md.upper().replace("PYRAMID_", "")
    assert "CC BY 4.0" in md and "Matilda" in md
    assert len(at.get("plotly_chart")) >= 10
