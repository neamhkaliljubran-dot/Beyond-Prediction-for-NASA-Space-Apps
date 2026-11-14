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
        ("Seasonal & lagged associations with autocorrelation-aware inference and FDR control", False),
        ("Equation discovery with leakage-free time-blocked validation vs baselines", False),
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
        st.warning(pending)
        st.markdown("*Planned method:* sparse regression over a small, dimensionally consistent "
                    "library of ENSO terms (°C, °C², lagged °C), evaluated with rolling-origin "
                    "blocked cross-validation against climatology, persistence and linear-ENSO "
                    "baselines.")
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
