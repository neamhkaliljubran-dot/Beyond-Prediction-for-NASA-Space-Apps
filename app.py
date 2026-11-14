"""Beyond Prediction — Streamlit entry point.

Run:  streamlit run app.py

Everything displayed as a result is computed from files in data/. Steps whose
inputs do not exist yet are shown as PENDING; nothing is filled in by hand.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from beyond_prediction import enso
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
def load_enso() -> pd.DataFrame:
    df = pd.read_csv(ENSO_CSV, parse_dates=["date"])
    for col in ("oni_anom_degC", "roni_anom_degC"):
        df[col.replace("_anom_degC", "_episode")] = enso.episode_flags(df[col]).to_numpy()
    return df


# ---------------------------------------------------------------- header
st.markdown("<h1 style='text-align:center;letter-spacing:.08em'>PYRAMID PRODUCTION</h1>",
            unsafe_allow_html=True)
st.markdown("<p style='text-align:center;font-size:1.1rem'><b>Beyond Prediction</b> — an "
            "evidence-grounded hypothesis discovery engine for Earth & space data · Team Hypatia · "
            "NASA Space Apps 2026: <i>Be An Earth System Trend Detective</i></p>",
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

# ---------------------------------------------------------------- question
st.divider()
st.subheader("Scientific question")
question = st.text_area("Question", QUESTION, height=90, label_visibility="collapsed")
index_choice = st.selectbox(
    "Primary ENSO index", ["RONI (NOAA official)", "ONI (sensitivity check)"],
    help="Per NWS Public Information Statement 26-05, NOAA CPC uses RONI for official ENSO "
         "monitoring. ONI is kept as a sensitivity check.")
run = st.button("Run Analysis", type="primary")
if run:
    st.session_state["ran"] = True
if question.strip() != QUESTION:
    st.info("This prototype's pipeline is built for the fixed demonstration question above; "
            "edited questions are not parsed.")

# ---------------------------------------------------------------- workflow
if st.session_state.get("ran"):
    st.divider()
    st.subheader("Analysis workflow")
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
        ("Dynamic association network across seasons and time windows", False),
        ("Candidate hypotheses with pre-stated selection criteria and validation plan", False),
    ]
    for i, (label, done) in enumerate(steps, 1):
        st.markdown(f"{'✅' if done else '⏳'} **Step {i}.** {label} — "
                    f"{'complete' if done else '*pending: not yet computed*'}")

    # ------------------------------------------------------------ outputs
    st.divider()
    st.subheader("Scientific outputs")
    o1, o2, o3 = st.tabs(["1 · Candidate hypothesis", "2 · Discovered relationship",
                          "3 · Dynamic network"])
    pending = ("**Not yet computed.** This output requires the IMERG regional rainfall series "
               "(step 3) and the association analysis (step 5). No placeholder values are shown.")
    with o1:
        st.warning(pending)
        st.markdown("*Planned selection criteria (fixed before seeing results):* FDR-adjusted "
                    "q < 0.05 using autocorrelation-adjusted inference, |r| ≥ 0.3, and a "
                    "consistent sign in ≥ 70 % of time windows. If no relationship qualifies, "
                    "the null result is reported.")
    with o2:
        sel = read_json(RESULTS / "stage_h_selection.json")
        tst = read_json(RESULTS / "stage_h_test.json")
        if not (sel and tst and sel.get("headline")):
            st.warning("Not yet computed (Stage H).")
        else:
            h = sel["headline"]
            fm = sel["final_models"][h]
            cf = {k: v for k, v in fm["coefficients"].items()}
            ex = tst["worked_example"]
            st.markdown(f"**COMPUTATIONAL RESULT — selected by a pre-stated rule on 2014–2019 "
                        f"validation, then tested once on {tst['test_period'][0]}…{tst['test_period'][1]}.** "
                        f"Target: region {h.split('-')[0]} (training-derived regions), "
                        f"{h.split('-')[1]} months.")
            st.latex(r"\Delta P_{R3}(t) = a + b_{m}\,\mathrm{RONI}(t),\qquad "
                     r"P_{R3}(t) = C_{R3}(m) + \Delta P_{R3}(t),\quad m\in\{\mathrm{Sep,Oct,Nov}\}")
            ct = pd.DataFrame([{"coefficient": k, "value": v["value"], "95% CI": f"[{v['ci95'][0]:.1f}, {v['ci95'][1]:.1f}]",
                                "fit 1998–2013 only": v["value_fit_1998_2013"], "units": v["units"]}
                               for k, v in cf.items()])
            st.dataframe(ct.round(2), use_container_width=True, hide_index=True)
            tr = pd.DataFrame(tst["results"]).set_index("target").loc[h]
            m = st.columns(4)
            m[0].metric("Test RMSE (mm/month)", f"{tr.rmse_selected:.1f}", f"climatology {tr.rmse_climatology:.1f}",
                        delta_color="off")
            m[1].metric("Test skill vs climatology", f"{tr.msess_selected:.2f}",
                        f"95% CI {tr.msess_ci95[0]:.2f}–{tr.msess_ci95[1]:.2f}", delta_color="off")
            m[2].metric("Linear lag-0 baseline skill", f"{tr.msess_linear_lag0:.2f}")
            m[3].metric("Persistence baseline skill", f"{tr.msess_persistence:.2f}")
            better = tr.msess_linear_lag0 >= tr.msess_selected
            st.info(("On the test period the simpler linear lag-0 model scored at least as well "
                     if better else "On the test period the selected model outscored the linear lag-0 model ")
                    + f"(skill {tr.msess_linear_lag0:.2f} vs {tr.msess_selected:.2f})"
                    + (": separate monthly slopes show no demonstrated out-of-sample benefit. " if better else ". ")
                    + "Lag 0 means RONI centred on the rainfall month (window includes the next "
                    "month), so this is a concurrent association, not a forecast or a physical law.")
            mon = int(ex["month"][5:7])
            bm = {9: "b_m9", 10: "b_m10", 11: "b_m11"}[mon]
            x = ex["inputs"]["x (RONI, degC)"]
            st.markdown(f"**Worked example — {ex['month']}** (test month with largest |RONI|):  \n"
                        f"ΔP = a + b × RONI = {cf['a']['value']:.4f} + ({cf[bm]['value']:.4f}) × ({x:.2f}) "
                        f"= **{ex['predicted_anomaly_mm_month']:+.2f} mm/month**  \n"
                        f"P̂ = C + ΔP = {ex['climatology_mm_month']:.2f} + {ex['predicted_anomaly_mm_month']:.2f} "
                        f"= **{ex['predicted_total_mm_month']:.2f} mm/month**; observed "
                        f"**{ex['observed_total_mm_month']:.2f}** (error {ex['error_mm_month']:+.2f}).")
            pr = pd.read_csv(RESULTS / "stage_h_test_predictions.csv", parse_dates=["date"])
            pr = pr[(pr.region + "-" + pr.season) == h]
            fp = go.Figure()
            fp.add_scatter(x=pr.date, y=pr.P, mode="markers+lines", name="observed (IMERG)",
                           line=dict(color="#26415e"))
            fp.add_scatter(x=pr.date, y=pr.pred_total, mode="markers", name="equation",
                           marker=dict(color="#b5542f", size=9, symbol="diamond"))
            fp.add_scatter(x=pr.date, y=pr.C, mode="markers", name="climatology",
                           marker=dict(color="#999", size=7))
            fp.update_layout(height=300, yaxis_title="mm/month", margin=dict(l=10, r=10, t=10, b=10),
                             legend=dict(orientation="h"))
            st.plotly_chart(fp, use_container_width=True)
            st.caption("Held-out test months only. Full selection table, all 12 region-season targets "
                       "and limitations: docs/STAGE_H_EQUATION.md.")
            allt = pd.DataFrame(tst["results"])[["target", "selected", "reliable_on_validation", "n_test",
                                                 "msess_selected", "msess_linear_lag0", "msess_persistence"]]
            with st.expander("All 12 targets (validation choice and test skill)"):
                st.dataframe(allt.round(2), use_container_width=True, hide_index=True)
    with o3:
        st.warning(pending)
        st.markdown("*Planned encoding:* edge colour = sign, width = |r|, hover = confidence "
                    "interval, style = significance; sliders over season and time window. "
                    "It is an association network — not a causal graph or topological proof.")

    # ------------------------------------------------------------ evidence
    st.divider()
    st.subheader("Supporting evidence (observed data)")
    if enso_df is not None:
        col = "roni_anom_degC" if index_choice.startswith("RONI") else "oni_anom_degC"
        name = col.split("_")[0].upper()
        fig = go.Figure()
        fig.add_scatter(x=enso_df["date"], y=enso_df[col], mode="lines", name=name,
                        line=dict(width=1.4, color="#2f6f8f"))
        other = "oni_anom_degC" if col == "roni_anom_degC" else "roni_anom_degC"
        fig.add_scatter(x=enso_df["date"], y=enso_df[other], mode="lines",
                        name=other.split("_")[0].upper(), line=dict(width=1, color="#999"),
                        opacity=0.6)
        for y in (0.5, -0.5):
            fig.add_hline(y=y, line_dash="dot", line_color="#b5542f")
        if imerg_v:
            g = imerg_v["granules"]
            fig.add_vrect(x0=g["first"]["time"]["BeginningDateTime"][:10],
                          x1=g["last"]["time"]["EndingDateTime"][:10],
                          fillcolor="#2f6f8f", opacity=0.07, line_width=0,
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
                       fillcolor="rgba(47,111,143,0.2)", name="95% block-bootstrap CI")
        fr.add_scatter(x=rr.window, y=rr.r, mode="lines+markers", name="r", line=dict(color="#2f6f8f"))
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
            "- The Indian Ocean Dipole co-varies with ENSO and strongly affects Indonesian rainfall "
            "in Sep–Nov; until it is included, associations may partly reflect the IOD.\n"
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
