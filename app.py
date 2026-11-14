"""Beyond Prediction — Streamlit entry point.

Run:  streamlit run app.py

Everything displayed as a result is computed from files in data/. Steps whose
inputs do not exist yet are shown as PENDING; nothing is filled in by hand.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from beyond_prediction import enso
from beyond_prediction import network as gnet
from beyond_prediction.provenance import DATA, read_json
from beyond_prediction.visuals import PYRAMID_HTML, walker_schematic

st.set_page_config(page_title="Beyond Prediction · Team Hypatia", layout="wide")

QUESTION = ("How do relationships between ENSO variability in the Pacific Ocean and rainfall "
            "across different regions of Indonesia change over time and across seasons, and do "
            "these changes reveal recurring or divergent patterns in a dynamic network?")

ENSO_CSV = DATA / "processed" / "enso_monthly.csv"
REGIONAL_CSV = DATA / "processed" / "imerg_regional_monthly.csv"   # not built yet
ENSO_PROV = DATA / "provenance" / "enso.json"
IMERG_PROV = DATA / "provenance" / "imerg_verification.json"
REGIONS_PROV = DATA / "provenance" / "regions.json"
REGION_MAP = Path(__file__).parent / "docs" / "figures" / "regions_map.png"
RESULTS = DATA / "results"


@st.cache_data
def load_edges() -> pd.DataFrame:
    return pd.read_csv(RESULTS / "network_edges.csv")


@st.cache_data
def load_enso() -> pd.DataFrame:
    df = pd.read_csv(ENSO_CSV, parse_dates=["date"])
    for col in ("oni_anom_degC", "roni_anom_degC"):
        df[col.replace("_anom_degC", "_episode")] = enso.episode_flags(df[col]).to_numpy()
    return df


# ---------------------------------------------------------------- header
st.markdown("""<style>
[data-testid="stMainBlockContainer"], .block-container {max-width: 1120px; padding-top: 2.2rem;}
h2, h3 {font-weight: 500; letter-spacing: .01em;}
.bp-hero {background: radial-gradient(1px 1px at 8% 22%, rgba(233,242,255,0.8), transparent), radial-gradient(1px 1px at 17% 64%, rgba(233,242,255,0.5), transparent), radial-gradient(1px 1px at 26% 35%, rgba(233,242,255,0.7), transparent), radial-gradient(1px 1px at 34% 80%, rgba(233,242,255,0.4), transparent), radial-gradient(1px 1px at 43% 15%, rgba(233,242,255,0.6), transparent), radial-gradient(1px 1px at 52% 58%, rgba(233,242,255,0.5), transparent), radial-gradient(1px 1px at 61% 28%, rgba(233,242,255,0.8), transparent), radial-gradient(1px 1px at 69% 74%, rgba(233,242,255,0.4), transparent), radial-gradient(1px 1px at 77% 40%, rgba(233,242,255,0.6), transparent), radial-gradient(1px 1px at 85% 18%, rgba(233,242,255,0.7), transparent), radial-gradient(1px 1px at 92% 62%, rgba(233,242,255,0.5), transparent), radial-gradient(1px 1px at 13% 88%, rgba(233,242,255,0.4), transparent), radial-gradient(1px 1px at 57% 90%, rgba(233,242,255,0.4), transparent), radial-gradient(1px 1px at 97% 35%, rgba(233,242,255,0.6), transparent), linear-gradient(180deg, #0A1C33 0%, #071426 100%);
  border: 1px solid rgba(87,185,245,.18); border-radius: 16px; padding: 56px 24px 40px; text-align: center;
  margin-bottom: 1.6rem;}
.bp-hero h1 {letter-spacing: .16em; font-weight: 600; color: #E9F2FF; margin: 0 0 .5rem 0; font-size: 2.4rem;}
.bp-hero .sub {color: #57B9F5; font-size: 1.15rem; margin: 0 0 .4rem 0;}
.bp-hero .meta {color: #A9BBD6; font-size: .95rem; margin: 0;}
</style>
<div class="bp-hero"><h1>PYRAMID PRODUCTION</h1>
<p class="sub"><b>Beyond Prediction</b> — an evidence-grounded hypothesis discovery engine for Earth &amp; space data</p>
<p class="meta">Team Hypatia · NASA Space Apps 2026 · <i>Be An Earth System Trend Detective</i></p></div>""",
            unsafe_allow_html=True)

st.markdown(
    "Earth's climate is a connected system: sea-surface temperatures in the tropical Pacific "
    "reorganise where the atmosphere rises and sinks, which shifts rainfall thousands of "
    "kilometres away. Rather than forecasting a single number, this prototype analyses real "
    "observations to find **how such relationships behave and change**, then turns what it finds "
    "into **candidate, testable hypotheses**. Results are labelled by type: observed data, "
    "published findings, computed results, and hypotheses. Associations are never presented "
    "as causation.")

c1, c2 = st.columns([3, 2])
with c1:
    state = st.radio("Schematic state", ["Neutral / La Niña-like", "El Niño"], horizontal=True)
    svg, cap = walker_schematic("elnino" if state == "El Niño" else "neutral")
    st.markdown(svg, unsafe_allow_html=True)
    st.caption(cap + " Other drivers — notably the Indian Ocean Dipole, the Asian–Australian "
               "monsoon and the Madden–Julian Oscillation — also shape Indonesian rainfall.")
with c2:
    st.markdown(PYRAMID_HTML, unsafe_allow_html=True)

AUDIO = Path(__file__).parent / "assets" / "audio" / "bach_prelude_c_bwv846_synth.wav"
if AUDIO.exists():
    with st.expander("♪ Optional music — off until you press play"):
        st.audio(str(AUDIO), format="audio/wav")
        st.caption("J. S. Bach, Prelude in C major, BWV 846 (bars 1–8). Public-domain composition; original "
                   "synthesised recording generated by scripts/make_music.py. Use the player for play, pause and volume.")

# ---------------------------------------------------------------- question
st.divider()
st.subheader("Scientific question")
question = st.text_area("Question", QUESTION, height=90, label_visibility="collapsed")
run = st.button("Run Analysis", type="primary")
with st.expander("Demo guide (for judges)"):
    st.markdown("1. Press **Run Analysis** — results load from cached, versioned files (no live NASA download).\n"
                "2. **Four scientific answers**: nature, location, direction and magnitude of change.\n"
                "3. **Hypothesis + test**: switch the data block and watch the contrasts and decision update.\n"
                "4. **Equation + test**: pick a held-out month (e.g. 2023-10, El Niño) — RONI is substituted into the "
                "frozen equation and compared with the IMERG observation; graphs follow.\n"
                "5. **Dynamic network**: change season, lag and time window; every edge is a computed correlation.\n"
                "6. **Integrated interpretation** and the closing quote.")
if run:
    st.session_state["ran"] = True
if question.strip() != QUESTION:
    st.info("This prototype's pipeline is built for the fixed demonstration question above; "
            "edited questions are not parsed.")

# ---------------------------------------------------------------- workflow
if st.session_state.get("ran"):
    enso_df = load_enso() if ENSO_CSV.exists() else None
    imerg_v = read_json(IMERG_PROV)
    have_regional = REGIONAL_CSV.exists()
    regions_v = read_json(REGIONS_PROV)
    steps = [
        ("Load & validate NOAA CPC ENSO indices (ONI, RONI)", enso_df is not None),
        ("Verify GPM IMERG V07 monthly collection, coverage, units, access", imerg_v is not None),
        ("Subset IMERG over Indonesia → monthly land rainfall (mm/month)", have_regional),
        ("Derive rainfall regions R1–R3 (IMERG-derived; not the published A/B/C)", regions_v is not None),
        ("Seasonal & lagged associations with autocorrelation-aware inference and FDR control",
         (RESULTS / "associations_primary.csv").exists()),
        ("Equation discovery with leakage-free time-blocked validation vs baselines",
         (RESULTS / "stage_h_test.json").exists()),
        ("Dynamic association network across seasons and time windows",
         (RESULTS / "network_edges.csv").exists()),
        ("Candidate hypothesis with a direct between-region test and validation plan",
         (RESULTS / "stage_i_hypothesis.json").exists()),
    ]
    with st.expander(f"Analysis workflow — {sum(d for _, d in steps)} of {len(steps)} steps computed from real data"):
        for i, (label, done) in enumerate(steps, 1):
            st.markdown(f"{'✅' if done else '⏳'} **Step {i}.** {label} — "
                        f"{'complete' if done else '*pending: not yet computed*'}")

    # ------------------------------------------------------------ integrated answer
    hyp_i = read_json(RESULTS / "stage_i_hypothesis.json")
    tst_i = read_json(RESULTS / "stage_h_test.json")
    if hyp_i and tst_i and (RESULTS / "network_patterns.csv").exists():
        st.divider()
        st.subheader("Four scientific answers")
        st.markdown(f"*{QUESTION}*")
        pat = pd.read_csv(RESULTS / "network_patterns.csv")
        ee = pd.read_csv(RESULTS / "network_edges.csv")
        prim_i = pd.read_csv(RESULTS / "associations_primary.csv")
        halves_i = pd.read_csv(RESULTS / "halves.csv")
        full0 = ee[(ee.kind == "ENSO-region") & (ee.window == gnet.FULL) & (ee.lag == 0)]
        sup = {s: ", ".join(full0[(full0.season == s) & (full0.status == "supported")].target) or "none"
               for s in ["DJF", "MAM", "JJA", "SON"]}
        n_sup = int((ee[(ee.kind == "ENSO-region") & (ee.window == gnet.FULL)].status == "supported").sum())
        pc = pat[pat.kind == "ENSO-region"].pattern.value_counts()
        r3 = pd.DataFrame(tst_i["results"]).set_index("target").loc["R3-SON"]
        A = hyp_i["A_primary_in_sample"]["contrasts"]
        js = prim_i[(prim_i.lag == 0) & prim_i.season.isin(["JJA", "SON"])]
        r3d = prim_i[(prim_i.lag == 0) & (prim_i.season == "DJF") & (prim_i.region == "R3")].iloc[0]
        sup_pos = int(((prim_i.q_bh_surrogate < 0.05) & (prim_i.r > 0)).sum())
        hw = (halves_i.delta_ci_hi - halves_i.delta_ci_lo) / 2
        n_change = int(((halves_i.delta_ci_lo > 0) | (halves_i.delta_ci_hi < 0)).sum())
        cols = st.columns(2)
        cols[0].markdown(f"""
**1 · Nature of change**

The relationship changes mainly **with the season**, not over the years. Associations that pass correction
(lag 0, BH q < 0.05): DJF {sup['DJF']} · MAM {sup['MAM']} · JJA {sup['JJA']} · SON {sup['SON']}.
Over 1998–2019, {pc.get('recurring', 0)} of 48 ENSO→region edges are *recurring* (same sign in all twelve 11-year
windows, CI excluding 0 in ≥ 9) and {pc.get('divergent', 0)} are divergent; {n_change} of 48 early-vs-late comparisons show a detectable change.
*No detectable change ≠ proof of stability.*
""")
        cols[1].markdown(f"""
**2 · Location of change**

In Jun–Nov all three regions show supported associations. In DJF only **R3 (eastern Indonesia)** has a supported
association; R1 and R2 are inconclusive (not evidence of no relationship). The **direct test** of whether R3's DJF
coefficient differs from R1/R2 is **not significant** (Holm p = {A['R3-R1']['p_holm_surrogate']:.4f} and
{A['R3-R2']['p_holm_surrogate']:.4f}), so the east–west contrast is an **observed pattern, not a confirmed difference**.
""")
        cols = st.columns(2)
        cols[0].markdown(f"""
**3 · Direction of change**

All {n_sup} statistically supported ENSO→rainfall associations are **negative**: higher RONI (El Niño-like) goes with
**less** rain, lower RONI (La Niña-like) with more. {sup_pos} supported associations are positive. The only
positive hint (R2 in DJF in recent windows) is inconclusive.
""")
        cols[1].markdown(f"""
**4 · Magnitude of change**

Jun–Nov, lag 0: **{js.slope_mm_per_degC.max():.0f} to {js.slope_mm_per_degC.min():.0f} mm/month per °C** of RONI
(r {js.r.max():.2f} to {js.r.min():.2f}); R3 in DJF: {r3d.slope_mm_per_degC:.0f} mm/month per °C. The held-out-tested
R3 Sep–Nov equation cut error from {r3.rmse_climatology:.1f} to {r3.rmse_selected:.1f} mm/month (skill
{r3.msess_selected:.2f}; simpler one-slope model {r3.msess_linear_lag0:.2f}). The 95% CIs for early-vs-late
changes in r span about ±{hw.min():.2f} to ±{hw.max():.2f}, so smaller changes cannot be detected with this record.
""")

    # ------------------------------------------------------------ outputs
    o1, o2, o3 = st.container(), st.container(), st.container()
    pending = ("**Not yet computed.** This output requires the IMERG regional rainfall series "
               "(step 3) and the association analysis (step 5). No placeholder values are shown.")
    with o1:
        st.divider()
        st.subheader("Candidate hypothesis and its test")
        hyp = read_json(RESULTS / "stage_i_hypothesis.json")
        if not hyp:
            st.warning("Not yet computed (Stage I).")
        else:
            hh = hyp["hypothesis"]
            st.markdown("**CANDIDATE HYPOTHESIS** (generated from the Stage F/G evidence; not independently validated)")
            st.markdown(f"> {hh['statement']}")
            st.markdown(f"- **H₀:** {hh['H0']}  \n- **H₁:** {hh['H1']}")
            st.markdown("**TEST HYPOTHESIS — direct test of the difference between regional coefficients.** "
                        "Because every region is paired with the same RONI values, β_R3 − β_Rk equals the "
                        "slope of the rainfall *difference* (R3 − Rk) on RONI. That single slope is tested with "
                        "persistence-preserving RONI surrogates (primary), an effective-sample-size t-test, and a "
                        "joint season-year block bootstrap; Holm correction across the two contrasts.")
            blocks = {"A — discovery data 1998–2019 (in-sample; generated the hypothesis)": hyp["A_primary_in_sample"],
                      "B — held-out months 2020–2025 (temporal check; low power)": hyp["B_held_out"],
                      **{f"Sensitivity — {k}": v for k, v in hyp["C_sensitivity"].items()}}
            bk = st.selectbox("Data used for the test", list(blocks), key="hyp_block")
            blk = blocks[bk]
            sl = pd.DataFrame([{"region": r, "β (mm/month per °C)" if "standardised" not in bk else "β (SD per °C)": v["beta"],
                                "95% CI": f"[{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]", "r": v["r"]}
                               for r, v in blk["slopes"].items()])
            st.markdown(f"**Estimated regional effects** — DJF, lag {blk['lag']}, {blk['n_months']} months "
                        f"({blk['n_season_years']} season-years)")
            st.dataframe(sl.round(3), use_container_width=True, hide_index=True, key="hyp_slopes")
            ct = pd.DataFrame([{"contrast": c, "Δβ = β_R3 − β_Rk": v["delta_beta"],
                                "95% CI (block bootstrap)": f"[{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]",
                                "p (surrogate)": v["p_surrogate"], "p Holm (surrogate)": v["p_holm_surrogate"],
                                "p (eff. sample size)": v["p_ess"], "n_eff": v["n_eff"]}
                               for c, v in blk["contrasts"].items()])
            st.markdown("**Between-region contrasts (the actual hypothesis test)**")
            st.dataframe(ct.round(4), use_container_width=True, hide_index=True, key="hyp_contrasts")
            units = "SD per °C" if "standardised" in bk else "mm/month per °C"
            g1, g2 = st.columns(2)
            regc = {"R1": "#57B9F5", "R2": "#8275DA", "R3": "#F2A65A"}
            rs = list(blk["slopes"])
            f1 = go.Figure(go.Scatter(
                x=rs, y=[blk["slopes"][r]["beta"] for r in rs], mode="markers",
                marker=dict(size=15, color=[regc[r] for r in rs]),
                error_y=dict(type="data", symmetric=False,
                             array=[blk["slopes"][r]["ci95"][1] - blk["slopes"][r]["beta"] for r in rs],
                             arrayminus=[blk["slopes"][r]["beta"] - blk["slopes"][r]["ci95"][0] for r in rs],
                             thickness=2, width=10, color="#A9BBD6"),
                hovertemplate="%{x}: β = %{y:.2f}<extra></extra>"))
            f1.add_hline(y=0, line_color="#3A4E6B")
            f1.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                             title=dict(text="Regional DJF coefficient β (95% CI)", font=dict(size=14)),
                             yaxis_title=f"β, {units}")
            g1.plotly_chart(f1, use_container_width=True, key=f"hyp_beta_{bk}")
            cs = list(blk["contrasts"])
            status = []
            for c in cs:
                v = blk["contrasts"][c]
                excl = v["ci95"][0] > 0 or v["ci95"][1] < 0
                status.append("supported" if (excl and v["p_holm_surrogate"] < 0.05) else
                              "suggestive (CI excludes 0, Holm p ≥ 0.05)" if excl else "inconclusive")
            f2 = go.Figure(go.Scatter(
                y=cs, x=[blk["contrasts"][c]["delta_beta"] for c in cs], mode="markers+text",
                marker=dict(size=15, color=["#57B9F5" if s == "supported" else "#F2A65A" if s.startswith("sugg")
                                            else "#7A8799" for s in status]),
                error_x=dict(type="data", symmetric=False,
                             array=[blk["contrasts"][c]["ci95"][1] - blk["contrasts"][c]["delta_beta"] for c in cs],
                             arrayminus=[blk["contrasts"][c]["delta_beta"] - blk["contrasts"][c]["ci95"][0] for c in cs],
                             thickness=2, width=10, color="#A9BBD6"),
                text=[f"Holm p = {blk['contrasts'][c]['p_holm_surrogate']:.3f}<br>{s}" for c, s in zip(cs, status)],
                textposition="top center", hovertemplate="%{y}: Δβ = %{x:.2f}<br>%{text}<extra></extra>"))
            f2.add_vline(x=0, line_color="#E9F2FF", line_dash="dash")
            xr_lo = min(blk["contrasts"][c]["ci95"][0] for c in cs)
            xr_hi = max(0, max(blk["contrasts"][c]["ci95"][1] for c in cs))
            pad = 0.15 * (xr_hi - xr_lo)
            f2.update_xaxes(range=[xr_lo - pad, xr_hi + pad])
            f2.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                             title=dict(text="Direct contrasts Δβ = β_R3 − β_Rk (95% CI)", font=dict(size=14)),
                             xaxis_title=f"Δβ, {units}  (0 = no difference)", yaxis=dict(range=[-0.6, 1.8]))
            g2.plotly_chart(f2, use_container_width=True, key=f"hyp_contrast_{bk}")
            st.caption("Orange = suggestive pattern (interval excludes 0 but the pre-stated primary test is not "
                       "significant); blue = statistically supported; grey = inconclusive. A difference in "
                       "significance between regions is not itself evidence of a difference — only the contrasts test it.")
            if blk["decision_rule_met"]:
                st.success("Decision: H₀ rejected for both contrasts under the pre-stated rule "
                           "(Holm surrogate p < 0.05 and CIs excluding 0) for this data block.")
            else:
                st.error("Decision: H₀ NOT rejected under the pre-stated rule (both Holm-adjusted surrogate "
                         "p < 0.05 AND both CIs excluding 0). The hypothesis is not supported at α = 0.05 by this test.")
            st.caption("Rule fixed in scripts/run_hypothesis_test.py before running. The surrogate test is primary "
                       "because it preserves ENSO persistence; the effective-sample-size p and bootstrap CI are "
                       "shown so disagreements between methods stay visible.")
            pts = pd.read_csv(RESULTS / "stage_i_djf_points.csv")
            pb = pts[pts.block.str.startswith(bk[0])] if bk[0] in "AB" else pts[pts.block.str.startswith("A")]
            fs = go.Figure()
            for reg, col in [("R1", "#57B9F5"), ("R2", "#8275DA"), ("R3", "#F2A65A")]:
                yv = pb[f"anom_{reg}"]
                fs.add_scatter(x=pb.roni, y=yv, mode="markers", name=reg, marker=dict(color=col, size=7, opacity=.7))
                b = np.polyfit(pb.roni, yv, 1)
                xx = np.linspace(pb.roni.min(), pb.roni.max(), 2)
                fs.add_scatter(x=xx, y=np.polyval(b, xx), mode="lines", line=dict(color=col, width=3),
                               name=f"{reg} fit: {b[0]:+.1f} mm/month per °C")
            fs.add_hline(y=0, line_color="#3A4E6B")
            fs.update_layout(height=340, xaxis_title="RONI (°C), centred on the rainfall month",
                             yaxis_title="DJF rainfall anomaly (mm/month)", margin=dict(l=10, r=10, t=60, b=10),
                             legend=dict(orientation="h", y=1.18, x=0))
            st.plotly_chart(fs, use_container_width=True, key=f"hyp_fig_{bk[0]}")
            Ai, Bh = hyp["A_primary_in_sample"]["contrasts"], hyp["B_held_out"]["contrasts"]
            st.markdown(
                f"**Conclusion.** Discovery data (in-sample): R3−R1 = {Ai['R3-R1']['delta_beta']:+.1f}, "
                f"R3−R2 = {Ai['R3-R2']['delta_beta']:+.1f} mm/month per °C — expected direction, intervals exclude 0, "
                f"but Holm p = {Ai['R3-R1']['p_holm_surrogate']:.4f} and {Ai['R3-R2']['p_holm_surrogate']:.4f}, so "
                f"**H₀ is not rejected**. Held-out 2020–2025: same direction (R3−R1 = {Bh['R3-R1']['delta_beta']:+.1f}, "
                f"R3−R2 = {Bh['R3-R2']['delta_beta']:+.1f}) but not significant (Holm p = "
                f"{Bh['R3-R1']['p_holm_surrogate']:.3f}, {Bh['R3-R2']['p_holm_surrogate']:.3f}; only 17 months). "
                f"**Status: suggestive candidate hypothesis, not confirmed and not independently validated.**")
            st.markdown(f"**Falsification / independent validation plan.** {hh['falsification']}")
    with o2:
        st.divider()
        st.subheader("Mathematical equation — discovered, frozen and tested")
        sel = read_json(RESULTS / "stage_h_selection.json")
        tst = read_json(RESULTS / "stage_h_test.json")
        hyp_eq = read_json(RESULTS / "stage_i_hypothesis.json")
        if not (sel and tst and sel.get("headline") and hyp_eq):
            st.warning("Not yet computed (Stage H).")
        else:
            h = sel["headline"]
            fm = sel["final_models"][h]
            cf = {k: v for k, v in fm["coefficients"].items()}
            ex = tst["worked_example"]
            lin = hyp_eq["equation_panel"]["linear_lag0_coefficients"]
            tr = pd.DataFrame(tst["results"]).set_index("target").loc[h]
            C_m = fm["climatology_mm_month"]
            OBS, EQ, LIN, CLIM = "#E9F2FF", "#57B9F5", "#8275DA", "#7A8799"
            st.markdown(f"**COMPUTATIONAL RESULT** — selected by a pre-stated rule on 2014–2019 validation, frozen "
                        f"(commit 1395389), then tested once on {tst['test_period'][0]} to {tst['test_period'][1]}. "
                        f"Region R3 (eastern Indonesia, training-derived), months Sep–Nov.")
            st.latex(r"\Delta P_{R3}(t) = a + b_{m}\,\mathrm{RONI}(t),\qquad "
                     r"P_{R3}(t) = C_{R3}(m) + \Delta P_{R3}(t),\quad m\in\{\mathrm{Sep,Oct,Nov}\}")
            st.markdown(
                f"- **P_R3(t)** — monthly rainfall total averaged over region R3 (NASA GPM IMERG V07B), mm/month\n"
                f"- **C_R3(m)** — 1998–2019 average rainfall for calendar month m: Sep {C_m['9']:.1f}, Oct "
                f"{C_m['10']:.1f}, Nov {C_m['11']:.1f} mm/month\n"
                f"- **ΔP_R3(t) = P − C** — rainfall anomaly, mm/month\n"
                f"- **RONI(t)** — NOAA CPC Relative Oceanic Niño Index, 3-month mean centred on month t, °C "
                f"(positive = El Niño-like)\n"
                f"- **a** = {cf['a']['value']:.2f} mm/month · **b_Sep** = {cf['b_m9']['value']:.2f}, **b_Oct** = "
                f"{cf['b_m10']['value']:.2f}, **b_Nov** = {cf['b_m11']['value']:.2f} mm/month per °C (fit 1998–2019)")

            # ---- 1. TEST EQUATION + actual vs calculated for one real observation
            ep = pd.read_csv(RESULTS / "stage_i_equation_panel.csv", parse_dates=["date"])
            st.markdown("#### TEST EQUATION — try it on a real held-out month")
            mlabel = {d.strftime("%Y-%m"): d for d in ep.date}
            pick = st.selectbox("Held-out month (R3, Sep–Nov, 2020–2025)", list(mlabel), key="eq_month",
                                index=list(mlabel).index(ex["month"]) if ex["month"] in mlabel else 0)
            row = ep[ep.date == mlabel[pick]].iloc[0]
            mm = int(row.month)
            mname = ["Sep", "Oct", "Nov"][mm - 9]
            bkey = {9: "b_m9", 10: "b_m10", 11: "b_m11"}[mm]
            a_, b_ = cf["a"]["value"], cf[bkey]["value"]
            anom_live = a_ + b_ * row.x
            total_live = row.C + anom_live
            assert abs(total_live - row.pred_frozen) < 1e-6
            c1, c2 = st.columns([1, 1])
            c1.markdown(
                f"1. RONI ({pick}, NOAA CPC) = **{row.x:+.2f} °C**  \n"
                f"2. ΔP = a + b_{mname} × RONI = {a_:.4f} + ({b_:.4f}) × ({row.x:+.2f}) = **{anom_live:+.2f} mm/month**  \n"
                f"3. P̂ = C({mname}) + ΔP = {row.C:.2f} + {anom_live:+.2f} = **{total_live:.2f} mm/month**  \n"
                f"4. Observed (IMERG V07B, R3) = **{row.P:.2f} mm/month** → difference {total_live - row.P:+.2f}")
            bar = go.Figure(go.Bar(
                x=["Observed (IMERG)", "Frozen equation", "One-slope model", "Climatology"],
                y=[row.P, total_live, row.pred_linear_lag0, row.pred_climatology],
                marker_color=[OBS, EQ, LIN, CLIM], text=[f"{v:.0f}" for v in
                                                          [row.P, total_live, row.pred_linear_lag0, row.pred_climatology]],
                textposition="outside", hovertemplate="%{x}: %{y:.1f} mm/month<extra></extra>"))
            bar.update_layout(height=300, yaxis_title="mm/month", margin=dict(l=10, r=10, t=30, b=10),
                              yaxis=dict(range=[0, max(row.P, total_live, row.pred_linear_lag0, row.C) * 1.25]))
            c2.plotly_chart(bar, use_container_width=True, key=f"eq_bar_{pick}")
            cmp_ = pd.DataFrame([
                {"model": "Frozen Stage H equation (month-varying slope)", "estimate (mm/month)": total_live,
                 "estimate − observed (mm/month)": total_live - row.P},
                {"model": "Reference: one-slope model (linear lag 0)", "estimate (mm/month)": row.pred_linear_lag0,
                 "estimate − observed (mm/month)": row.pred_linear_lag0 - row.P},
                {"model": "Reference: climatology (1998–2019 mean)", "estimate (mm/month)": row.pred_climatology,
                 "estimate − observed (mm/month)": row.pred_climatology - row.P},
                {"model": "OBSERVED: IMERG V07B, region R3", "estimate (mm/month)": row.P,
                 "estimate − observed (mm/month)": 0.0}])
            with st.expander("Numbers for this month"):
                st.dataframe(cmp_.round(2), use_container_width=True, hide_index=True, key="eq_compare")
            st.caption("One month illustrates the arithmetic; it is not evidence. The evaluation is the 16-month test below. "
                       "Coefficients are frozen (fit 1998–2019); test months were never used for fitting or selection.")

            # ---- 2. time series over all held-out months
            st.markdown("#### Observed vs calculated rainfall — all 16 held-out months")
            lab = ep.date.dt.strftime("%Y-%m")
            ts = go.Figure()
            ts.add_scatter(x=lab, y=ep.P, mode="lines+markers", name="Observed (IMERG)",
                           line=dict(color=OBS, width=2.5), marker=dict(size=7))
            ts.add_scatter(x=lab, y=ep.pred_frozen, mode="lines+markers", name="Frozen equation",
                           line=dict(color=EQ, width=2.5), marker=dict(size=8, symbol="diamond"))
            ts.add_scatter(x=lab, y=ep.pred_linear_lag0, mode="lines", name="One-slope model",
                           line=dict(color=LIN, width=2, dash="dash"))
            ts.add_scatter(x=lab, y=ep.pred_climatology, mode="lines", name="Climatology",
                           line=dict(color=CLIM, width=1.5, dash="dot"))
            ts.add_scatter(x=lab, y=ep.x, mode="markers", name="RONI (°C, right axis)", yaxis="y2",
                           marker=dict(color="#F2A65A", size=6, symbol="square"), opacity=.75)
            ts.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                             yaxis=dict(title="Rainfall, mm/month"),
                             yaxis2=dict(title="RONI °C", overlaying="y", side="right", range=[-3, 3], showgrid=False,
                                         tickvals=[-2, -1, 0, 1, 2]),
                             xaxis=dict(type="category", title="Held-out month (Sep–Nov of each year)"),
                             legend=dict(orientation="h", y=1.12))
            st.plotly_chart(ts, use_container_width=True, key="eq_ts")
            st.caption("RONI is negative (La Niña-like) in 2020–2022, 2024 and Sep 2025 and positive (El Niño-like) in "
                       "2023. Months are evenly spaced for readability.")

            # ---- 3. monthly coefficients with uncertainty
            st.markdown("#### Monthly coefficients with 95% uncertainty intervals")
            mon = ["September", "October", "November"]
            keys = ["b_m9", "b_m10", "b_m11"]
            val = [cf[k]["value"] for k in keys]
            lo = [cf[k]["ci95"][0] for k in keys]
            hi = [cf[k]["ci95"][1] for k in keys]
            cfig = go.Figure(go.Scatter(
                x=mon, y=val, mode="markers", marker=dict(color=EQ, size=14),
                error_y=dict(type="data", symmetric=False, array=[h_ - v for h_, v in zip(hi, val)],
                             arrayminus=[v - l_ for v, l_ in zip(val, lo)], color=EQ, thickness=2, width=10),
                name="b_m (frozen equation)",
                hovertemplate="%{x}: %{y:.1f} mm/month per °C<extra></extra>"))
            cfig.add_hline(y=lin["b"], line_dash="dash", line_color=LIN,
                           annotation_text=f"one-slope model: {lin['b']:.1f}", annotation_position="top right")
            cfig.add_hline(y=0, line_color="#3A4E6B")
            cfig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                               yaxis_title="mm/month of rain per °C of RONI", showlegend=False)
            st.plotly_chart(cfig, use_container_width=True, key="eq_coef")
            st.caption("Intervals: 2-year block bootstrap (fit 1998–2019). September and October overlap; "
                       "November's interval lies entirely above October's, pointing to a weaker November sensitivity "
                       "in the fit period. Separate intervals are not a formal test, and on held-out data the "
                       "one-slope model did as well, so month-specific slopes are not shown to improve prediction.")

            # ---- 4. comparison with reference models on the test period
            st.markdown("#### Held-out performance against reference models")
            names = ["Frozen equation", "One-slope model", "Persistence", "Climatology"]
            rmse = [tr.rmse_selected, tr["rmse_linear@lag0"], tr.rmse_persistence, tr.rmse_climatology]
            skill = [tr.msess_selected, tr.msess_linear_lag0, tr.msess_persistence, 0.0]
            pf = go.Figure(go.Bar(
                x=names, y=rmse, marker_color=[EQ, LIN, "#4F7CA8", CLIM],
                text=[f"RMSE {r:.1f}<br>skill {s:.2f}" for r, s in zip(rmse, skill)], textposition="outside",
                hovertemplate="%{x}: RMSE %{y:.1f} mm/month<extra></extra>"))
            pf.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10),
                             yaxis=dict(title="Test error, RMSE (mm/month; lower is better)", range=[0, max(rmse) * 1.3]))
            st.plotly_chart(pf, use_container_width=True, key="eq_perf")
            st.caption(f"16 held-out months, identical observations and baseline for every model. Skill = 1 − MSE/MSE(climatology); "
                       f"95% CI for the frozen equation's skill: {tr.msess_ci95[0]:.2f}–{tr.msess_ci95[1]:.2f}.")

            # ---- 5. interpretation
            better = tr.msess_linear_lag0 >= tr.msess_selected
            st.markdown(
                f"**What the equation reveals.** In eastern Indonesia during Sep–Nov, rainfall falls by roughly "
                f"{abs(cf['b_m9']['value']):.0f}–{abs(cf['b_m10']['value']):.0f} mm/month in Sep–Oct and "
                f"{abs(cf['b_m11']['value']):.0f} mm/month in Nov for each +1 °C of RONI. On data it never saw, the "
                f"equation reduced error from {tr.rmse_climatology:.1f} to {tr.rmse_selected:.1f} mm/month (skill "
                f"{tr.msess_selected:.2f}). "
                + (f"The simpler one-slope model did at least as well (skill {tr.msess_linear_lag0:.2f}), so the "
                   f"month-specific slopes are **not shown to add value** beyond a single ENSO sensitivity. "
                   if better else "")
                + "Because RONI is centred on the rainfall month, this is a **concurrent statistical relationship**, "
                  "not a forecast and not a physical law.")
            allt = pd.DataFrame(tst["results"])[["target", "selected", "reliable_on_validation", "n_test",
                                                 "msess_selected", "msess_linear_lag0", "msess_persistence"]]
            with st.expander("All 12 region-season targets (validation choice and test skill)"):
                st.dataframe(allt.round(2), use_container_width=True, hide_index=True)
    with o3:
        st.divider()
        st.subheader("Dynamic relationship network (G-NETS prototype)")
        if not (RESULTS / "network_edges.csv").exists():
            st.warning("Not yet computed (Stage G).")
        else:
            edges = load_edges()
            meta = read_json(RESULTS / "network_nodes.json")
            st.markdown(
                "**COMPUTATIONAL RESULT — exploratory association network (G-NETS, proposed framework).** "
                "Nodes: ENSO (RONI, °C) and three IMERG-derived rainfall regions placed at their "
                "geographic centroids (ENSO's position is schematic). Each edge is one computed Pearson "
                "correlation from Stage F (ENSO→region: RONI vs rainfall anomaly *lag* months later) or "
                "between two regions' same-month rainfall anomalies. Edges show statistical association "
                "only — not causation, and not a topological invariant.")
            st.info("**How to read:** circles are ENSO and three rainfall regions. A solid line is a statistically "
                    "supported correlation (number = r; thicker = stronger). **Amber** = less rain when RONI is high "
                    "(El Niño-like); **blue** = regions whose rainfall rises and falls together; **dashed grey** = "
                    "inconclusive, which is *not* proof of no relationship. Hover any label for the 95% CI, sample "
                    "size and test result.")
            c1, c2, c3 = st.columns([2, 1, 2])
            n_season = c1.radio("Season (rainfall months)", ["DJF", "MAM", "JJA", "SON"], index=3,
                                horizontal=True, key="net_season")
            n_lag = c2.selectbox("Lag: rainfall follows ENSO by (months)", [0, 1, 2, 3], key="net_lag")
            wins = [gnet.FULL] + sorted(w for w in edges.window.unique() if w != gnet.FULL)
            n_win = c3.selectbox("Time window", wins, key="net_window",
                                 help="11-year rolling windows overlap; they are not independent tests.")
            show_rr = st.checkbox("Show region–region rainfall links (lag 0)", value=True, key="net_rr")
            sel_e = edges[(edges.season == n_season) & (edges.window == n_win) &
                          (((edges.kind == "ENSO-region") & (edges.lag == n_lag)) |
                           ((edges.kind == "region-region") & show_rr))]
            pos = {k: tuple(v["pos"]) for k, v in meta["nodes"].items() if k != "ENSO"}
            st.plotly_chart(gnet.figure(sel_e, pos, meta["stage_h_notes"]), use_container_width=True,
                            key=f"net_fig_{n_season}_{n_lag}_{n_win}_{show_rr}")
            st.caption("Edge width ∝ |r|; label = r; hover for 95% CI, n, BH q and pattern. A positive ENSO→region "
                       "r would mean more rain when RONI is high; none is statistically supported in the full period. "
                       "Region–region links share variability that may itself be partly ENSO-driven.")
            if n_win != gnet.FULL:
                st.warning(f"Window {n_win}: about {int(sel_e.n.min())} monthly pairs per edge; status uses "
                           "the bootstrap CI only (no multiple-testing correction). Treat as exploratory.")
            st.markdown("**Link to the Stage H equation (held-out validation status):**")
            for reg in ["R1", "R2", "R3"]:
                note = meta["stage_h_notes"].get(f"{reg}-{n_season}", "")
                flag = " ← headline equation" if f"{reg}-{n_season}" == (sel or {}).get("headline") else ""
                st.markdown(f"- {reg}–{n_season}: {note}{flag}")
            shown = sel_e[["kind", "source", "target", "lag", "window", "r", "ci_lo", "ci_hi", "n",
                           "q_bh", "status", "pattern"]].rename(columns={"q_bh": "BH q (full period)"})
            st.dataframe(shown.round(3), use_container_width=True, hide_index=True, key="net_table")

            st.markdown("**How the ENSO→region edges change across rolling windows** "
                        f"({n_season}, lag {n_lag}; ● = 95% CI excludes 0)")
            roll_e = edges[(edges.kind == "ENSO-region") & (edges.season == n_season) &
                           (edges.lag == n_lag) & (edges.window != gnet.FULL)]
            piv = roll_e.pivot(index="target", columns="window", values="r")
            excl = roll_e.assign(x=(roll_e.ci_lo > 0) | (roll_e.ci_hi < 0)).pivot(
                index="target", columns="window", values="x")
            txt = piv.round(2).astype(str) + excl.map(lambda b: " ●" if b else "")
            hm2 = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, text=txt.values,
                                       texttemplate="%{text}", zmin=-1, zmax=1, colorscale="RdBu",
                                       colorbar=dict(title="r")))
            hm2.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(hm2, use_container_width=True, key=f"net_hm_{n_season}_{n_lag}")
            pats = pd.read_csv(RESULTS / "network_patterns.csv")
            pt = pats[(pats.kind == "ENSO-region") & (pats.season == n_season) & (pats.lag == n_lag)]
            st.dataframe(pt[["target", "pattern", "windows_ci_excludes_0", "n_windows", "r_min", "r_max"]].round(2),
                         use_container_width=True, hide_index=True, key="net_patterns")
            st.caption("Pattern rules (fixed in beyond_prediction/network.py): recurring = same sign in all 12 "
                       "windows and CI excludes 0 in ≥ 9; weak-recurring = same sign, fewer; divergent = CI "
                       "excludes 0 with opposite signs in different windows; sign-variable = sign changes "
                       "without that (inconclusive). An inconclusive or absent edge is not evidence of no "
                       "relationship.")

    # ------------------------------------------------------------ integrated interpretation
    if hyp_i and tst_i and (RESULTS / "network_patterns.csv").exists():
        st.divider()
        st.subheader("Integrated scientific interpretation")
        st.markdown(
            f"**The network** shows that ENSO–rainfall links over Indonesia are organised by season: in Jun–Nov "
            f"every region carries a negative, recurring link (El Niño-like RONI → less rain), while in DJF only "
            f"eastern Indonesia (R3) does, and in MAM no link passes correction. **The equation** quantifies one of "
            f"the strongest recurring links (R3, Sep–Nov) and passed a one-time held-out test (skill "
            f"{r3.msess_selected:.2f}; the simpler one-slope model {r3.msess_linear_lag0:.2f}). **The hypothesis** "
            f"tests the most notable divergence — whether R3's DJF coefficient really differs from R1/R2: the "
            f"contrasts point the expected way ({A['R3-R1']['delta_beta']:+.1f} and {A['R3-R2']['delta_beta']:+.1f} "
            f"mm/month per °C) but are **not significant** under the pre-stated test (Holm p "
            f"{A['R3-R1']['p_holm_surrogate']:.4f} and {A['R3-R2']['p_holm_surrogate']:.4f}), so it remains a "
            f"*suggestive pattern*, not a confirmed difference.")
        st.markdown(
            "**What changes, and what does not:** the relationships change strongly *across seasons and regions*; "
            "over 1998–2019 no change *over time* was detected (with limited power). **Evidence labels:** numbers are "
            "COMPUTATIONAL RESULTS from IMERG V07B and NOAA CPC RONI; agreement with PUBLISHED KNOWLEDGE (El Niño "
            "dries much of Indonesia in Jun–Nov) is noted; INDEPENDENT VALIDATION with other rainfall data (CHIRPS, "
            "BMKG gauges) is the next step and **has not yet been performed**. G-NETS is a proposed investigational "
            "framework; associations are not causation.")

    st.divider()
    with st.expander("Supporting evidence — ENSO record, rainfall regions, full association tables"):
        index_choice = st.selectbox(
            "ENSO index for the record chart", ["RONI (NOAA official)", "ONI (sensitivity check)"],
            help="Per NWS Public Information Statement 26-05, NOAA CPC uses RONI for official ENSO "
                 "monitoring. ONI is kept as a sensitivity check.")
        st.divider()
        st.subheader("Supporting evidence (observed data)")
        if enso_df is not None:
            col = "roni_anom_degC" if index_choice.startswith("RONI") else "oni_anom_degC"
            name = col.split("_")[0].upper()
            fig = go.Figure()
            fig.add_scatter(x=enso_df["date"], y=enso_df[col], mode="lines", name=name,
                            line=dict(width=1.6, color="#57B9F5"))
            other = "oni_anom_degC" if col == "roni_anom_degC" else "roni_anom_degC"
            fig.add_scatter(x=enso_df["date"], y=enso_df[other], mode="lines",
                            name=other.split("_")[0].upper(), line=dict(width=1, color="#7A8799"),
                            opacity=0.6)
            for y in (0.5, -0.5):
                fig.add_hline(y=y, line_dash="dot", line_color="#F2A65A")
            if imerg_v:
                g = imerg_v["granules"]
                fig.add_vrect(x0=g["first"]["time"]["BeginningDateTime"][:10],
                              x1=g["last"]["time"]["EndingDateTime"][:10],
                              fillcolor="#57B9F5", opacity=0.08, line_width=0,
                              annotation_text="IMERG V07 coverage", annotation_position="top left")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10),
                              yaxis_title="Index anomaly (°C)", legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Source: NOAA CPC, {name} (ERSSTv6). Each 3-month value is plotted at its "
                       "centre month. Dotted lines: ±0.5 °C thresholds. Most recent values are "
                       "provisional per CPC.")

            if imerg_v:
                start = pd.Timestamp(imerg_v["granules"]["first"]["time"]["BeginningDateTime"][:10])
                end = pd.Timestamp(imerg_v["granules"]["last"]["time"]["EndingDateTime"][:10])
                sub = enso_df[(enso_df["date"] >= start) & (enso_df["date"] <= end)]
                ep = col.replace("_anom_degC", "_episode")
                m = st.columns(4)
                m[0].metric("Months in IMERG overlap", len(sub))
                m[1].metric(f"Warm-episode months ({name})", int((sub[ep] == 1).sum()))
                m[2].metric(f"Cold-episode months ({name})", int((sub[ep] == -1).sum()))
                m[3].metric(f"{name} range (°C)", f"{sub[col].min():.2f} to {sub[col].max():.2f}")
                st.caption("Episode months use CPC's rule (≥ 5 consecutive overlapping seasons beyond "
                           "±0.5 °C), applied to the file's unrounded values. These are descriptive "
                           "counts only, not results of the ENSO–rainfall analysis.")

        if regions_v and REGION_MAP.exists():
            st.markdown("**COMPUTATIONAL RESULT — IMERG-derived rainfall regions (R1–R3)**")
            st.image(str(REGION_MAP), use_container_width=True)
            rr = regions_v["regions"]
            tbl = pd.DataFrame({k: v["climatology_mm_month"] for k, v in rr.items()}).T
            tbl.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            tbl.insert(0, "area share", [f"{v['area_share']:.0%}" for v in rr.values()])
            st.dataframe(tbl, use_container_width=True)
            rz = regions_v["regionalization"]
            boot = sorted(rz["year_bootstrap_ARI_20"])
            st.caption(
                f"Mean monthly rainfall (mm/month), {regions_v['climatology_years'][0]}–"
                f"{regions_v['climatology_years'][1]}, area-weighted. Stability: year-bootstrap adjusted "
                f"Rand index median {boot[len(boot)//2]:.2f} (range {boot[0]:.2f}–{boot[-1]:.2f}); "
                f"silhouette favours k=2 ({rz['silhouette_by_k_subsample5000']['2']:.2f}) over k=3 "
                f"({rz['silhouette_by_k_subsample5000']['3']:.2f}). Small islands excluded by the cell "
                f"rule: {regions_v['mask']['area_share_of_those_parts']:.1%} of Indonesian land area.")

        if (RESULTS / "associations_primary.csv").exists():
            st.divider()
            st.subheader("Stage F — ENSO–rainfall associations")
            st.markdown("**COMPUTATIONAL RESULT — exploratory.** Discovery period 1998-01 to 2019-12 "
                        "(rainfall months); the 2020-01 to 2025-09 test period was not used. "
                        "Lag L pairs rainfall in month t+L with RONI centred on month t; lags 0–1 "
                        "overlap the 3-month ENSO window. Associations are not evidence of causation.")
            prim = pd.read_csv(RESULTS / "associations_primary.csv")
            season = st.radio("Season (rainfall months)", ["DJF", "MAM", "JJA", "SON"], index=3,
                              horizontal=True)
            sub = prim[prim.season == season].pivot(index="region", columns="lag", values="r")
            qs = prim[prim.season == season].pivot(index="region", columns="lag", values="q_bh_surrogate")
            txt = sub.round(2).astype(str) + qs.map(lambda q: " *" if q < 0.05 else "")
            hm = go.Figure(go.Heatmap(z=sub.values, x=[f"lag {c}" for c in sub.columns], y=sub.index,
                                      text=txt.values, texttemplate="%{text}", zmin=-1, zmax=1,
                                      colorscale="RdBu", colorbar=dict(title="r")))
            hm.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(hm, use_container_width=True)
            st.caption("Pearson r between RONI and rainfall anomaly (mm/month), n = 66 monthly pairs "
                       "per cell (22 season-years). * = Benjamini–Hochberg q < 0.05 within the declared "
                       "48-test family, using phase-randomised surrogate p-values (floor 1/2001). BH "
                       "does not remove temporal dependence or the data-informed choice of regions.")
            show = prim[prim.season == season][["region", "lag", "n", "n_eff", "r", "r_ci_lo", "r_ci_hi",
                                                "slope_mm_per_degC", "slope_ci_lo", "slope_ci_hi",
                                                "p_surrogate", "q_bh_surrogate", "p_ess", "q_bh_ess"]]
            st.dataframe(show.round(4), use_container_width=True, hide_index=True)

            roll = pd.read_csv(RESULTS / "rolling.csv")
            c1, c2 = st.columns(2)
            reg = c1.selectbox("Region", ["R1", "R2", "R3"])
            lag = c2.selectbox("Lag (months)", [0, 1, 2, 3])
            rr = roll[(roll.region == reg) & (roll.season == season) & (roll.lag == lag)]
            fr = go.Figure()
            fr.add_scatter(x=rr.window, y=rr.r_ci_hi, mode="lines", line=dict(width=0), showlegend=False)
            fr.add_scatter(x=rr.window, y=rr.r_ci_lo, mode="lines", line=dict(width=0), fill="tonexty",
                           fillcolor="rgba(87,185,245,0.18)", name="95% block-bootstrap CI")
            fr.add_scatter(x=rr.window, y=rr.r, mode="lines+markers", name="r", line=dict(color="#57B9F5"))
            fr.add_hline(y=0, line_color="#999")
            fr.update_layout(height=300, yaxis=dict(range=[-1, 1], title="r"),
                             margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
            st.plotly_chart(fr, use_container_width=True)
            st.caption(f"EXPLORATORY: 11-year windows stepped by 1 year (n ≈ {int(rr.n.min())} monthly pairs "
                       "each). Overlapping windows are not independent tests and do not by themselves "
                       "show a regime shift.")
            with st.expander("Sensitivity analyses (lag 0)"):
                rows = []
                for f, lab in [("primary", "RONI, R1–R3 (primary)"), ("oni", "ONI, R1–R3"),
                               ("k3train", "RONI, k=3 fitted on 1998–2013")]:
                    d = pd.read_csv(RESULTS / f"associations_{f}.csv")
                    d = d[d.lag == 0].pivot(index="region", columns="season", values="r")
                    d.insert(0, "analysis", lab)
                    rows.append(d.reset_index())
                st.dataframe(pd.concat(rows)[["analysis", "region", "DJF", "MAM", "JJA", "SON"]].round(2),
                             use_container_width=True, hide_index=True)
                st.caption("Each sensitivity family has its own BH correction; region labels in "
                           "different regionalizations are not interchangeable (k=2 is in the CSV "
                           "files and the findings report).")

    # ------------------------------------------------------------ methods etc.
    st.divider()
    t1, t2, t3 = st.tabs(["Methods", "Limitations", "Data provenance"])
    with t1:
        st.markdown(
            "- **ENSO:** CPC ONI and RONI (ERSSTv6), 3-month means aligned to centre month.\n"
            "- **Rainfall:** GPM IMERG Final monthly V07B, 0.1°, native unit mm/hr → mm/month "
            "via days-in-month × 24.\n"
            "- **Territory:** Natural Earth 1:10m Indonesia (v5.1.1) ∩ IMERG land/sea mask V2: a cell "
            "is used if ≥ 50 % of it is Indonesian territory and < 50 % of it is water.\n"
            "- **Regions:** k-means (k = 3, chosen a priori) on each cell's standardised 1998–2024 "
            "climatological annual cycle. Labelled R1–R3. Grouping by annual-cycle similarity follows "
            "the idea of Aldrian & Susanto (2003), but their station-based A/B/C regions are *not* "
            "reproduced and R1–R3 are not claimed to be equivalent.\n"
            "- **Inference:** effective sample size for autocorrelation, phase-randomised "
            "surrogates, block bootstrap CIs, Benjamini–Hochberg FDR across all tests.\n"
            "- **G-NETS:** proposed investigational framework for organising results as a "
            "time-varying association network; not a validated mathematical theory.")
    with t2:
        st.markdown(
            "- About 27 years of satellite rainfall contain few ENSO events; sliding-window "
            "estimates will be noisy.\n"
            "- IMERG 1998 – May 2000 is TRMM-era input; NASA documents specific caveats.\n"
            "- The Indian Ocean Dipole co-varies with ENSO (r ≈ 0.5 in SON). A DMI sensitivity check "
            "(docs/IOD_SENSITIVITY.md) found the JJA, R1/R3 SON and R3 DJF RONI associations persist after "
            "controlling for DMI; R2 SON weakens. DMI is not part of the selected equation.\n"
            "- Correlation and regression results describe association, not causation.\n"
            "- Recent ENSO values are provisional and may be revised by CPC.")
    with t3:
        st.json(regions_v or {"regions": "not built"}, expanded=False)
        st.json(read_json(ENSO_PROV) or {"enso": "not built"}, expanded=False)
        st.json(read_json(IMERG_PROV) or {"imerg": "not verified"}, expanded=False)

# ---------------------------------------------------------------- closing
st.divider()
st.markdown("<div style='text-align:center;padding:24px;border:1px dashed #9aa;border-radius:8px;"
            "opacity:.7'><i>Closing quote — to be decided by Team Hypatia.</i></div>",
            unsafe_allow_html=True)
