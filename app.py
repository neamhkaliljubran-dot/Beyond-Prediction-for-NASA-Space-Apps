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
import streamlit.components.v1 as components

from beyond_prediction import enso
from beyond_prediction import network as gnet
from beyond_prediction.provenance import DATA, read_json
from beyond_prediction.visuals import concept_network_svg, starfield_html

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


REGION_NAMES = {"R1": "south", "R2": "north-west", "R3": "east"}
SEASON_NAMES = {"DJF": "December–February", "MAM": "March–May", "JJA": "June–August", "SON": "September–November"}


def section(kicker: str, title: str) -> None:
    st.markdown(f"<div class='bp-sec'><div class='bp-kicker'>{kicker}</div><h2 class='bp-title'>{title}</h2></div>",
                unsafe_allow_html=True)


def story(items, cls: str = "bp-story") -> None:
    st.markdown(f"<div class='{cls}'>" + "".join(f"<div><h4>{h}</h4><p>{p}</p></div>" for h, p in items) + "</div>",
                unsafe_allow_html=True)


def chart_head(title: str, how: str) -> None:
    st.markdown(f"<div class='bp-chart-h'><h3>{title}</h3><p class='bp-read'>{how}</p></div>", unsafe_allow_html=True)


def see(text: str) -> None:
    st.markdown(f"<p class='bp-see'>{text}</p>", unsafe_allow_html=True)


def pretty(fig, height: int):
    fig.update_layout(height=height, margin=dict(l=12, r=12, t=36, b=12), font=dict(size=14),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      hoverlabel=dict(font_size=13), legend=dict(font=dict(size=13)))
    return fig


# ---------------------------------------------------------------- landing
ran = bool(st.session_state.get("ran"))
st.markdown(starfield_html(), unsafe_allow_html=True)
st.markdown("""<style>
.stApp {background: radial-gradient(1200px 760px at 50% -8%, #10294A 0%, #071426 55%, #050E1C 100%) fixed;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stMainBlockContainer"], .block-container {max-width: 1060px; padding-top: 1.2rem; position: relative; z-index: 1;}
h2, h3 {font-weight: 400 !important; letter-spacing: .03em;}
[data-testid="stPlotlyChart"] {background: rgba(6, 16, 32, .66); border: 1px solid rgba(87, 185, 245, .10);
  border-radius: 16px; padding: 10px 8px;}
[data-testid="stDataFrame"], [data-testid="stExpander"] details {background: rgba(6, 16, 32, .80);
  border: 1px solid rgba(87, 185, 245, .10); border-radius: 14px;}
[data-testid="stExpander"] {margin-top: 2.2rem;}
[data-testid="stExpander"] summary p {color: #8FB3D6; font-size: .92rem; letter-spacing: .03em;}
[data-testid="stMetric"] {text-align: center;}
[data-testid="stMetricLabel"] {justify-content: center; color: #8FB3D6;}
[data-testid="stMetricValue"] {font-weight: 300; font-size: 2.1rem; justify-content: center;}
[data-testid="stMetricDelta"] {justify-content: center;}
.bp-sec {text-align: center; margin: 16vh auto 4vh auto; animation: bp-fade 1.2s ease both;}
.bp-kicker {color: #57B9F5; font-size: .78rem; letter-spacing: .34em; text-transform: uppercase; margin-bottom: .7rem;}
.bp-title {font-size: clamp(2rem, 4.2vw, 3rem) !important; font-weight: 300 !important; letter-spacing: .05em;
  color: #F1F6FF; margin: 0 !important; padding: 0 !important;}
.bp-mnote {text-align: center; color: #8FB3D6 !important; font-size: .9rem !important; margin-top: -.4rem;}
.bp-statement {text-align: center; font-size: clamp(1.5rem, 3vw, 2.2rem) !important; font-weight: 300; line-height: 1.55 !important;
  max-width: 880px; margin: 3vh auto 1.1rem auto; color: #F1F6FF; animation: bp-fade 1.6s ease both;}
.bp-statement b {font-weight: 500; color: #9FD8FF;}
.bp-tag {text-align: center; color: #7F95B5; font-size: .8rem !important; letter-spacing: .18em; text-transform: uppercase; margin: 0 0 8vh 0;}
.bp-story {display: grid; grid-template-columns: 1fr 1fr; gap: 3rem 4.2rem; max-width: 920px; margin: 0 auto 7vh auto;}
.bp-story h4 {color: #9FD8FF; font-weight: 400; font-size: 1.06rem; letter-spacing: .05em; margin: 0 0 .55rem 0; padding: 0;}
.bp-story p {color: #C9D7EA; font-size: 1.05rem !important; line-height: 1.78; margin: 0;}
.bp-story b {color: #E9F2FF; font-weight: 500;}
.bp-answers h4 {font-size: 1.25rem; color: #E9F2FF;}
@media (max-width: 760px) {.bp-story {grid-template-columns: 1fr;}}
.bp-result {max-width: 780px; margin: 0 auto 9vh auto; text-align: center; padding: 1.5rem 1.6rem;
  border-top: 1px solid rgba(233, 242, 255, .22); border-bottom: 1px solid rgba(233, 242, 255, .22);
  color: #DCE8F7; font-size: 1.12rem; line-height: 1.75;}
.bp-result .lbl {display: block; color: #8FB3D6; font-size: .74rem; letter-spacing: .32em; text-transform: uppercase; margin-bottom: .6rem;}
.bp-result b {color: #F1F6FF; font-weight: 500;}
.bp-chart-h {margin: 7vh 0 .3rem 0;}
.bp-chart-h h3 {font-size: 1.32rem !important; font-weight: 400 !important; color: #E9F2FF; margin: 0 !important; padding: 0 !important;}
.bp-read {color: #A9BBD6; font-size: .98rem !important; line-height: 1.65; margin: .45rem 0 .9rem 0;}
.bp-see {color: #DCE8F7; font-size: 1.04rem !important; line-height: 1.72; margin: .9rem 0 0 0; padding-left: .95rem;
  border-left: 2px solid rgba(87, 185, 245, .45);}
.st-key-eq_hero {margin: 3vh auto 0 auto; animation: bp-reveal 1.8s ease both;}
.st-key-eq_hero .katex {font-size: 2.4em; color: #EAF6FF;
  text-shadow: 0 0 24px rgba(87, 185, 245, .55), 0 0 3px rgba(159, 216, 255, .55);}
.bp-coef {text-align: center; color: #9FD8FF; font-size: 1.1rem !important; letter-spacing: .04em; margin: .8rem 0 6vh 0;}
.bp-explain {max-width: 800px; margin: 0 auto 4vh auto;}
.bp-explain p {color: #C9D7EA; font-size: 1.06rem !important; line-height: 1.78; margin: 0 0 1.15rem 0;}
.bp-explain b {color: #E9F2FF; font-weight: 500;}
.bp-subtitle {text-align: center; font-size: 1.45rem !important; font-weight: 300 !important; letter-spacing: .06em;
  color: #E9F2FF; margin: 9vh 0 .2rem 0 !important;}
.bp-arith {text-align: center; color: #8FB3D6; font-size: .95rem; margin: .6rem 0 0 0;}
.bp-question {text-align: center; font-style: italic; font-size: 1.08rem !important; color: #A9BBD6; max-width: 820px; margin: 0 auto 7vh auto; line-height: 1.7;}
@keyframes bp-reveal {from {opacity: 0; transform: translateY(20px) scale(.97)} to {opacity: 1; transform: none}}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {line-height: 1.7;}
.bp-hero {text-align: center; margin: 6vh 0 .2rem 0;}
.bp-hero h1 {font-size: clamp(2.7rem, 6.4vw, 4.6rem); font-weight: 300; letter-spacing: .14em; margin: 0; padding: 0;
  background: linear-gradient(90deg, #E9F2FF 0%, #9FD8FF 55%, #B9B0F0 100%); -webkit-background-clip: text;
  background-clip: text; color: transparent;}
.bp-hero .sub {color: #A9C8E8; font-size: clamp(1rem, 1.9vw, 1.25rem); letter-spacing: .1em; margin: .6rem 0 0 0;}
.bp-caption {text-align: center; color: #6F86A6; font-size: .8rem; letter-spacing: .06em; margin: -.4rem 0 1.4rem 0;}
.bp-credit {text-align: center; color: #7F95B5; font-size: .85rem; letter-spacing: .08em; margin-top: 1.2rem;}
.bp-quote {text-align: center; font-size: clamp(1.4rem, 2.8vw, 2rem); font-weight: 300; line-height: 1.6; color: #E9F2FF;
  letter-spacing: .02em; margin: 7vh auto 2vh auto; max-width: 820px; animation: bp-fade 1.6s ease both;}
.bp-foot {text-align: center; color: #6F86A6; font-size: .78rem; line-height: 1.6; margin: 5vh auto 2vh auto; max-width: 860px;}
.bp-foot a {color: #8FB8DD;}
@keyframes bp-fade {from {opacity: 0; transform: translateY(14px)} to {opacity: 1; transform: none}}
@keyframes bp-float {0%, 100% {transform: translateY(0)} 50% {transform: translateY(-10px)}}
.st-key-question_box {display: flex; justify-content: center;}
.st-key-question_box button {max-width: 780px; min-height: 0; padding: 18px 34px 22px 34px; border-radius: 22px;
  display: flex; flex-direction: column; align-items: center; gap: .55rem;
  background: rgba(120, 132, 150, .30); border: 1px solid rgba(233, 242, 255, .28); color: #E9F2FF;
  box-shadow: 0 14px 44px rgba(0, 0, 0, .40); backdrop-filter: blur(3px);
  animation: bp-float 6.5s ease-in-out infinite; transition: background .9s ease, border-color .9s ease, box-shadow .9s ease;}
.st-key-question_box button p {font-size: 1.12rem; line-height: 1.6; white-space: normal; font-weight: 400;}
.st-key-question_box button:hover {border-color: #57B9F5; color: #FFFFFF; animation-play-state: paused;}
.st-key-question_box button::before {content: "Enter Question"; display: inline-flex; align-items: center; gap: .55rem;
  padding: 0 0 .55rem 30px; width: 100%; justify-content: center; box-sizing: border-box;
  border-bottom: 1px solid rgba(233, 242, 255, .16); color: #BFD5EE; font-size: .82rem; letter-spacing: .26em;
  text-transform: uppercase; background-repeat: no-repeat; background-size: 20px 20px; background-position: calc(50% - 92px) 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%239FD8FF' stroke-width='2.2' stroke-linecap='round'%3E%3Ccircle cx='10.5' cy='10.5' r='6.5'/%3E%3Cline x1='15.4' y1='15.4' x2='21' y2='21'/%3E%3C/svg%3E");}
</style>""", unsafe_allow_html=True)
st.markdown("<div class='bp-hero'><h1>Meta Prediction</h1>"
            "<p class='sub'>An Earth System Hypothesis Discovery Engine</p></div>", unsafe_allow_html=True)
st.markdown(concept_network_svg(), unsafe_allow_html=True)
st.markdown("<p class='bp-caption'>Conceptual illustration of an interconnected Earth system — not data</p>",
            unsafe_allow_html=True)
if st.button(QUESTION, key="question_box"):
    st.session_state["ran"] = True
    ran = True
if ran:
    st.markdown("""<style>.st-key-question_box button {background: #000000 !important; animation: none !important;
      border-color: rgba(87, 185, 245, .55) !important; box-shadow: 0 0 0 1px rgba(87,185,245,.15), 0 18px 50px rgba(0,0,0,.6) !important;}
      [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"] {animation: bp-fadeo .9s ease both;}
      @keyframes bp-fadeo {from {opacity: 0} to {opacity: 1}}</style>""",
                unsafe_allow_html=True)
st.markdown("<p class='bp-credit'>" + ("Scroll down to follow the discovery" if ran else "Click the question to begin the discovery")
            + "<br>Team Hypatia · NASA Space Apps 2026</p>", unsafe_allow_html=True)

# Music (approach B): one <audio> element attached once to the page outside Streamlit's re-rendered tree,
# so reruns never recreate or restart it. Started right after the question click where browsers allow.
SWAN_JS = """<script>
const w = window.parent, d = w.document;
if (!d.getElementById('bp-swan')) {
  const a = d.createElement('audio');
  a.id = 'bp-swan'; a.loop = false; a.preload = 'auto'; a.controls = true;
  a.src = w.location.origin + w.location.pathname.replace(/\\/$/, '') + '/app/static/swan.mp3';
  a.setAttribute('aria-label', 'Music: The Swan (Saint-Saëns) — use the controls to pause or mute');
  a.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:9999;height:30px;width:190px;opacity:.55;' +
                    'color-scheme:dark;transition:opacity .4s';
  a.onmouseenter = () => a.style.opacity = '1'; a.onmouseleave = () => a.style.opacity = '.55';
  d.body.appendChild(a);
  a.play().catch(err => { a.dataset.blocked = String(err); a.style.opacity = '1'; });
}
if (!w.__bpScrolled) {
  w.__bpScrolled = true;
  setTimeout(() => { const t = d.getElementById('bp-hypothesis'); if (t) t.scrollIntoView({behavior: 'smooth', block: 'start'}); }, 900);
}
</script>"""

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
    components.html(SWAN_JS, height=0)

    # ------------------------------------------------------------ outputs
    o1, o2, o3 = st.container(), st.container(), st.container()
    pending = ("**Not yet computed.** This output requires the IMERG regional rainfall series "
               "(step 3) and the association analysis (step 5). No placeholder values are shown.")
    with o1:
        st.markdown("<div id='bp-hypothesis'></div>", unsafe_allow_html=True)
        hyp = read_json(RESULTS / "stage_i_hypothesis.json")
        if not hyp:
            st.warning("Not yet computed (Stage I).")
        else:
            hh = hyp["hypothesis"]
            A0 = hyp["A_primary_in_sample"]
            sA, cA = A0["slopes"], A0["contrasts"]
            section("The discovery", "The hypothesis")
            st.markdown(
                "<p class='bp-statement'>In the December–February wet season, rainfall in <b>eastern Indonesia</b> may "
                "respond more strongly to the Pacific's El Niño–La Niña cycle than rainfall in the rest of the country.</p>"
                "<p class='bp-tag'>Candidate hypothesis · discovered in our data · not yet confirmed</p>",
                unsafe_allow_html=True)
            story([
                ("What we investigated",
                 "How Indonesia's monthly rainfall, measured by NASA satellites since 1998, rises and falls with ENSO — "
                 "the El Niño–La Niña cycle of the tropical Pacific Ocean."),
                ("What pointed to it",
                 f"In December–February only eastern Indonesia showed a clear link: about {abs(sA['R3']['beta']):.0f} mm "
                 f"less rain per month for each 1 °C of El Niño-like warming. The south and north-west (R1, R2) showed almost none "
                 f"({sA['R1']['beta']:+.1f} and {sA['R2']['beta']:+.1f} mm)."),
                ("What we tested",
                 "Whether that east–west difference is real. We measured the difference itself and compared it with "
                 "thousands of simulated ENSO histories that keep ENSO's natural rhythm, using a pass mark we fixed "
                 "before looking at the answer."),
                ("What the test concluded",
                 f"The difference points the expected way, in 1998–2019 and again in the later 2020–2025 months, but it "
                 f"does not reach our strict 5% pass mark (p ≈ {cA['R3-R1']['p_holm_surrogate']:.2f} and "
                 f"{cA['R3-R2']['p_holm_surrogate']:.2f}). It remains a promising, testable idea."),
            ])
            st.markdown(
                "<div class='bp-result'><span class='lbl'>Result</span>"
                + ("Supported — the east–west difference passes our pre-set test." if A0["decision_rule_met"] else
                   "<b>Suggestive, not yet confirmed.</b> The pattern is consistent in our data but not strong enough "
                   "to be called proven. The next step is to test it with independent rain-gauge records.")
                + "</div>", unsafe_allow_html=True)

            blocks = {"A — discovery data 1998–2019 (in-sample; generated the hypothesis)": hyp["A_primary_in_sample"],
                      "B — held-out months 2020–2025 (temporal check; low power)": hyp["B_held_out"],
                      **{f"Sensitivity — {k}": v for k, v in hyp["C_sensitivity"].items()}}
            bk = st.selectbox("Data shown in the charts below", list(blocks), key="hyp_block")
            blk = blocks[bk]
            units = "SD per °C" if "standardised" in bk else "mm/month per °C"
            regc = {"R1": "#57B9F5", "R2": "#8275DA", "R3": "#F2A65A"}
            rs = list(blk["slopes"])
            below = [r for r in rs if blk["slopes"][r]["ci95"][1] < 0]
            around = [r for r in rs if blk["slopes"][r]["ci95"][0] <= 0 <= blk["slopes"][r]["ci95"][1]]
            g1, g2 = st.columns(2, gap="large")
            with g1:
                chart_head("How strongly does each region respond?",
                           f"Each dot is a region's rainfall change ({units}) for every +1 °C of RONI in "
                           "December–February; the bar shows the range of plausible values. Below zero means drier "
                           "in El Niño-like months.")
                f1 = go.Figure(go.Scatter(
                    x=rs, y=[blk["slopes"][r]["beta"] for r in rs], mode="markers",
                    marker=dict(size=16, color=[regc[r] for r in rs]),
                    error_y=dict(type="data", symmetric=False,
                                 array=[blk["slopes"][r]["ci95"][1] - blk["slopes"][r]["beta"] for r in rs],
                                 arrayminus=[blk["slopes"][r]["beta"] - blk["slopes"][r]["ci95"][0] for r in rs],
                                 thickness=2, width=10, color="#A9BBD6"),
                    hovertemplate="%{x}: %{y:.2f}<extra></extra>"))
                f1.add_hline(y=0, line_color="#3A4E6B")
                f1.update_layout(showlegend=False, yaxis_title=units,
                                 xaxis=dict(ticktext=[f"{r}<br>{REGION_NAMES[r]}" for r in rs], tickvals=rs))
                st.plotly_chart(pretty(f1, 330), use_container_width=True, key=f"hyp_beta_{bk}")
                see(f"{' and '.join(below) or 'No region'} sits clearly below zero"
                    + (f"; {' and '.join(around)} {'straddle' if len(around) > 1 else 'straddles'} zero." if around else "."))
            cs = list(blk["contrasts"])
            status = []
            for c in cs:
                v = blk["contrasts"][c]
                excl = v["ci95"][0] > 0 or v["ci95"][1] < 0
                status.append("supported" if (excl and v["p_holm_surrogate"] < 0.05) else
                              "suggestive" if excl else "inconclusive")
            with g2:
                chart_head("Is the east really different?",
                           "Each dot is how much more eastern Indonesia's rain responds than R1's or R2's; the bar is "
                           "its plausible range. The dashed line at 0 means “no difference”.")
                f2 = go.Figure(go.Scatter(
                    y=cs, x=[blk["contrasts"][c]["delta_beta"] for c in cs], mode="markers+text",
                    marker=dict(size=16, color=["#57B9F5" if s == "supported" else "#D9C3A5" if s == "suggestive"
                                                else "#7A8799" for s in status]),
                    error_x=dict(type="data", symmetric=False,
                                 array=[blk["contrasts"][c]["ci95"][1] - blk["contrasts"][c]["delta_beta"] for c in cs],
                                 arrayminus=[blk["contrasts"][c]["delta_beta"] - blk["contrasts"][c]["ci95"][0] for c in cs],
                                 thickness=2, width=10, color="#A9BBD6"),
                    text=[f"{s} (p = {blk['contrasts'][c]['p_holm_surrogate']:.2f})" for c, s in zip(cs, status)],
                    textposition="top center", hovertemplate="%{y}: %{x:.2f}<br>%{text}<extra></extra>"))
                f2.add_vline(x=0, line_color="#E9F2FF", line_dash="dash")
                xr_lo = min(blk["contrasts"][c]["ci95"][0] for c in cs)
                xr_hi = max(0, max(blk["contrasts"][c]["ci95"][1] for c in cs))
                pad = 0.15 * (xr_hi - xr_lo)
                f2.update_xaxes(range=[xr_lo - pad, xr_hi + pad])
                f2.update_layout(showlegend=False, xaxis_title=f"difference, {units}", yaxis=dict(range=[-0.6, 1.8]))
                st.plotly_chart(pretty(f2, 330), use_container_width=True, key=f"hyp_contrast_{bk}")
                if all(s == "supported" for s in status):
                    see("Both differences pass the pre-set test: statistically supported.")
                elif all(s != "inconclusive" for s in status):
                    see("Both differences lie on the expected side of zero, but neither passes the strict pre-set "
                        "test — a suggestive pattern, not a confirmed one.")
                else:
                    see("At least one plausible range includes zero, so these data cannot tell the regions apart.")
            pts = pd.read_csv(RESULTS / "stage_i_djf_points.csv")
            pb = pts[pts.block.str.startswith(bk[0])] if bk[0] in "AB" else pts[pts.block.str.startswith("A")]
            chart_head("Every December–February month, side by side",
                       "Each dot is one month: further right = more El Niño-like (RONI), higher = more rain than normal. "
                       "Each line is that region's average trend.")
            fs = go.Figure()
            trends = {}
            for reg, col in [("R1", "#57B9F5"), ("R2", "#8275DA"), ("R3", "#F2A65A")]:
                yv = pb[f"anom_{reg}"]
                fs.add_scatter(x=pb.roni, y=yv, mode="markers", name=reg, marker=dict(color=col, size=7, opacity=.7))
                b = np.polyfit(pb.roni, yv, 1)
                trends[reg] = b[0]
                xx = np.linspace(pb.roni.min(), pb.roni.max(), 2)
                fs.add_scatter(x=xx, y=np.polyval(b, xx), mode="lines", line=dict(color=col, width=3),
                               name=f"{reg} trend: {b[0]:+.1f} mm per °C")
            fs.add_hline(y=0, line_color="#3A4E6B")
            fs.update_layout(xaxis_title="RONI (°C) — El Niño-like to the right",
                             yaxis_title="rain above / below normal (mm/month)", legend=dict(orientation="h", y=1.16, x=0))
            st.plotly_chart(pretty(fs, 380), use_container_width=True, key=f"hyp_fig_{bk[0]}")
            steep = min(trends, key=trends.get)
            see(f"The steepest downward trend is {steep} ({trends[steep]:+.1f} mm per °C); "
                + ", ".join(f"{r} {v:+.1f}" for r, v in trends.items() if r != steep) + ". "
                + ("Data block shown: " + ("discovery 1998–2019." if bk[0] == "A" else "held-out 2020–2025." if bk[0] == "B"
                                          else "discovery 1998–2019 (sensitivity choices change the test, not these points).")))

            with st.expander("Technical details — hypotheses, test method and exact numbers"):
                st.markdown(f"**Formal statement (pre-registered in scripts/run_hypothesis_test.py).** {hh['statement']}")
                st.markdown(f"- **H₀:** {hh['H0']}  \n- **H₁:** {hh['H1']}")
                st.markdown("**Method.** β_R3 − β_Rk equals the slope of the rainfall difference (R3 − Rk) on RONI, "
                            "tested with persistence-preserving RONI surrogates (primary), an effective-sample-size "
                            "t-test and a joint season-year block bootstrap; Holm correction across the two contrasts. "
                            "Decision rule: reject H₀ only if both Holm-adjusted surrogate p < 0.05 and both 95% "
                            "intervals exclude 0.")
                sl = pd.DataFrame([{"region": r, "β (mm/month per °C)" if "standardised" not in bk else "β (SD per °C)": v["beta"],
                                    "95% CI": f"[{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]", "r": v["r"]}
                                   for r, v in blk["slopes"].items()])
                st.markdown(f"**Regional effects** — DJF, lag {blk['lag']}, {blk['n_months']} months "
                            f"({blk['n_season_years']} season-years)")
                st.dataframe(sl.round(3), use_container_width=True, hide_index=True, key="hyp_slopes")
                ct = pd.DataFrame([{"contrast": c, "Δβ = β_R3 − β_Rk": v["delta_beta"],
                                    "95% CI (block bootstrap)": f"[{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]",
                                    "p (surrogate)": v["p_surrogate"], "p Holm (surrogate)": v["p_holm_surrogate"],
                                    "p (eff. sample size)": v["p_ess"], "n_eff": v["n_eff"]}
                                   for c, v in blk["contrasts"].items()])
                st.markdown("**Between-region contrasts (the actual hypothesis test)**")
                st.dataframe(ct.round(4), use_container_width=True, hide_index=True, key="hyp_contrasts")
                st.markdown("**Decision for this data block:** "
                            + ("H₀ rejected under the pre-stated rule." if blk["decision_rule_met"] else
                               "H₀ not rejected under the pre-stated rule — not supported at α = 0.05."))
                Ai, Bh = hyp["A_primary_in_sample"]["contrasts"], hyp["B_held_out"]["contrasts"]
                st.markdown(
                    f"**Conclusion.** Discovery data (in-sample): R3−R1 = {Ai['R3-R1']['delta_beta']:+.1f}, "
                    f"R3−R2 = {Ai['R3-R2']['delta_beta']:+.1f} mm/month per °C — expected direction, intervals exclude 0, "
                    f"but Holm p = {Ai['R3-R1']['p_holm_surrogate']:.4f} and {Ai['R3-R2']['p_holm_surrogate']:.4f}, so "
                    f"H₀ is not rejected. Held-out 2020–2025: same direction (R3−R1 = {Bh['R3-R1']['delta_beta']:+.1f}, "
                    f"R3−R2 = {Bh['R3-R2']['delta_beta']:+.1f}) but not significant (Holm p = "
                    f"{Bh['R3-R1']['p_holm_surrogate']:.3f}, {Bh['R3-R2']['p_holm_surrogate']:.3f}; only 17 months). "
                    f"Status: suggestive candidate hypothesis, not confirmed and not independently validated.")
                st.markdown(f"**Falsification / independent validation plan.** {hh['falsification']}")
    with o2:
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
            section("The centerpiece", "The equation")
            with st.container(key="eq_hero"):
                st.latex(r"P_{R3}(t) \;=\; C_{R3}(m) \;+\; a \;+\; b_{m}\cdot\mathrm{RONI}(t)")
                st.markdown(
                    f"<p class='bp-coef'>a = {cf['a']['value']:.1f} mm/month &nbsp;·&nbsp; b<sub>Sep</sub> = "
                    f"{cf['b_m9']['value']:.1f} &nbsp;·&nbsp; b<sub>Oct</sub> = {cf['b_m10']['value']:.1f} &nbsp;·&nbsp; "
                    f"b<sub>Nov</sub> = {cf['b_m11']['value']:.1f} &nbsp;mm/month per °C</p>", unsafe_allow_html=True)
            st.markdown(f"""<div class='bp-explain'>
<p><b>What it calculates.</b> The expected rainfall over eastern Indonesia (region R3) for a month of September, October
or November.</p>
<p><b>The symbols.</b> <i>P</i> is that month's rainfall and <i>C(m)</i> its normal amount (September
{C_m['9']:.0f}, October {C_m['10']:.0f}, November {C_m['11']:.0f} mm). <i>RONI</i> is NOAA's ENSO index: positive
for El Niño-like, negative for La Niña-like conditions. <i>b<sub>m</sub></i> says how many millimetres of rain change
for each 1 °C of RONI in that month.</p>
<p><b>How ENSO enters.</b> Each +1 °C of RONI lowers the calculated rain by about
{abs(cf['b_m9']['value']):.0f}–{abs(cf['b_m10']['value']):.0f} mm in September–October and about
{abs(cf['b_m11']['value']):.0f} mm in November; La Niña-like (negative) values raise it instead.</p>
<p><b>What it can and cannot show.</b> Tested once on {int(tr.n_test)} months it had never seen (2020–2025), it cut
the typical error from {tr.rmse_climatology:.1f} to {tr.rmse_selected:.1f} mm/month. It describes a statistical
relationship within the same month — not a weather forecast and not a physical law. A simpler one-slope version
(b = {lin['b']:.1f} for all three months) did {'just as well' if tr.msess_linear_lag0 >= tr.msess_selected else 'slightly worse'}
on those months.</p></div>""", unsafe_allow_html=True)

            # ---- TEST EQUATION
            ep = pd.read_csv(RESULTS / "stage_i_equation_panel.csv", parse_dates=["date"])
            st.markdown("<h3 class='bp-subtitle'>TEST EQUATION — try it on a real month</h3>"
                        "<p class='bp-read' style='text-align:center'>Pick one of the test months. The equation uses only "
                        "that month's RONI value; then compare its answer with what NASA satellites actually measured.</p>",
                        unsafe_allow_html=True)
            mlabel = {d.strftime("%Y-%m"): d for d in ep.date}
            pick = st.selectbox("Test month (eastern Indonesia, Sep–Nov, 2020–2025)", list(mlabel), key="eq_month",
                                index=list(mlabel).index(ex["month"]) if ex["month"] in mlabel else 0)
            row = ep[ep.date == mlabel[pick]].iloc[0]
            mm = int(row.month)
            mname = ["Sep", "Oct", "Nov"][mm - 9]
            bkey = {9: "b_m9", 10: "b_m10", 11: "b_m11"}[mm]
            a_, b_ = cf["a"]["value"], cf[bkey]["value"]
            anom_live = a_ + b_ * row.x
            total_live = row.C + anom_live
            assert abs(total_live - row.pred_frozen) < 1e-6
            m1, m2, m3 = st.columns(3)
            m1.metric("RONI that month", f"{row.x:+.2f} °C")
            m2.metric("Calculated by the equation", f"{total_live:.0f} mm")
            m3.metric("Measured by NASA satellites", f"{row.P:.0f} mm")
            m1.markdown("<p class='bp-mnote'>" + ("El Niño-like" if row.x > 0.5 else "La Niña-like" if row.x < -0.5
                                                   else "near neutral") + "</p>", unsafe_allow_html=True)
            m2.markdown(f"<p class='bp-mnote'>normal {mname}: {row.C:.0f} mm</p>", unsafe_allow_html=True)
            m3.markdown(f"<p class='bp-mnote'>equation − measured: {total_live - row.P:+.0f} mm</p>",
                        unsafe_allow_html=True)
            st.markdown(
                f"<p class='bp-arith'>{row.C:.1f} (normal {mname}) + ({a_:.2f}) + ({b_:.2f} × {row.x:+.2f}) "
                f"= <b>{total_live:.1f} mm</b> &nbsp;·&nbsp; measured {row.P:.1f} mm</p>", unsafe_allow_html=True)
            chart_head("This month at a glance",
                       "Bar height is rainfall in mm. White = measured; blue = our equation; violet = the simpler "
                       "one-slope model; grey = a normal month.")
            bar = go.Figure(go.Bar(
                x=["Measured (NASA IMERG)", "Our equation", "One-slope model", "Normal month"],
                y=[row.P, total_live, row.pred_linear_lag0, row.pred_climatology],
                marker_color=[OBS, EQ, LIN, CLIM], text=[f"{v:.0f} mm" for v in
                                                          [row.P, total_live, row.pred_linear_lag0, row.pred_climatology]],
                textposition="outside", hovertemplate="%{x}: %{y:.1f} mm/month<extra></extra>"))
            bar.update_layout(yaxis_title="mm/month",
                              yaxis=dict(range=[0, max(row.P, total_live, row.pred_linear_lag0, row.C) * 1.25]))
            st.plotly_chart(pretty(bar, 320), use_container_width=True, key=f"eq_bar_{pick}")
            see("One month illustrates the arithmetic; it is not proof. The 16-month test below is the real evaluation.")
            cmp_ = pd.DataFrame([
                {"model": "Frozen Stage H equation (month-varying slope)", "estimate (mm/month)": total_live,
                 "estimate − observed (mm/month)": total_live - row.P},
                {"model": "Reference: one-slope model (linear lag 0)", "estimate (mm/month)": row.pred_linear_lag0,
                 "estimate − observed (mm/month)": row.pred_linear_lag0 - row.P},
                {"model": "Reference: climatology (1998–2019 mean)", "estimate (mm/month)": row.pred_climatology,
                 "estimate − observed (mm/month)": row.pred_climatology - row.P},
                {"model": "OBSERVED: IMERG V07B, region R3", "estimate (mm/month)": row.P,
                 "estimate − observed (mm/month)": 0.0}])
            with st.expander("Exact numbers for this month"):
                st.dataframe(cmp_.round(2), use_container_width=True, hide_index=True, key="eq_compare")

            # ---- charts
            section("Evidence", "What the real data show")
            lab = ep.date.dt.strftime("%Y-%m")
            chart_head("Measured and calculated rain, month by month",
                       "Sixteen test months (Sep–Nov, 2020–2025) the equation never saw. White = measured by NASA "
                       "satellites; blue = our equation; dashed violet = the simpler one-slope model; dotted grey = a "
                       "normal month; orange squares = RONI (right-hand scale).")
            ts = go.Figure()
            ts.add_scatter(x=lab, y=ep.P, mode="lines+markers", name="Measured (NASA IMERG)",
                           line=dict(color=OBS, width=2.5), marker=dict(size=7))
            ts.add_scatter(x=lab, y=ep.pred_frozen, mode="lines+markers", name="Our equation",
                           line=dict(color=EQ, width=2.5), marker=dict(size=8, symbol="diamond"))
            ts.add_scatter(x=lab, y=ep.pred_linear_lag0, mode="lines", name="One-slope model",
                           line=dict(color=LIN, width=2, dash="dash"))
            ts.add_scatter(x=lab, y=ep.pred_climatology, mode="lines", name="Normal month",
                           line=dict(color=CLIM, width=1.5, dash="dot"))
            ts.add_scatter(x=lab, y=ep.x, mode="markers", name="RONI (°C, right)", yaxis="y2",
                           marker=dict(color="#F2A65A", size=7, symbol="square"), opacity=.8)
            ts.update_layout(hovermode="x unified", yaxis=dict(title="rainfall (mm/month)"),
                             yaxis2=dict(title="RONI (°C)", overlaying="y", side="right", range=[-3, 3], showgrid=False,
                                         tickvals=[-2, -1, 0, 1, 2]),
                             xaxis=dict(type="category"), legend=dict(orientation="h", y=1.16))
            st.plotly_chart(pretty(ts, 400), use_container_width=True, key="eq_ts")
            see("The equation follows the big swings: wetter-than-normal La Niña autumns in 2020–2022 and the dry "
                "El Niño autumn of 2023. It misses some single months, especially the very wet Septembers of 2021 and 2025.")

            chart_head("How sensitive is each month to ENSO?",
                       "Each dot is the rainfall change (mm/month) for every +1 °C of RONI; the bar is its plausible "
                       "range. The dashed line is the simpler one-slope model, which uses one value for all three months.")
            mon = ["September", "October", "November"]
            keys = ["b_m9", "b_m10", "b_m11"]
            val = [cf[k]["value"] for k in keys]
            lo = [cf[k]["ci95"][0] for k in keys]
            hi = [cf[k]["ci95"][1] for k in keys]
            cfig = go.Figure(go.Scatter(
                x=mon, y=val, mode="markers", marker=dict(color=EQ, size=15),
                error_y=dict(type="data", symmetric=False, array=[h_ - v for h_, v in zip(hi, val)],
                             arrayminus=[v - l_ for v, l_ in zip(val, lo)], color=EQ, thickness=2, width=10),
                name="b_m (frozen equation)",
                hovertemplate="%{x}: %{y:.1f} mm/month per °C<extra></extra>"))
            cfig.add_hline(y=lin["b"], line_dash="dash", line_color=LIN,
                           annotation_text=f"one-slope model: {lin['b']:.1f}", annotation_position="top right")
            cfig.add_hline(y=0, line_color="#3A4E6B")
            cfig.update_layout(yaxis_title="mm/month per °C of RONI", showlegend=False)
            st.plotly_chart(pretty(cfig, 340), use_container_width=True, key="eq_coef")
            see(f"September and October respond strongly ({val[0]:.0f} and {val[1]:.0f}); November about a third as much "
                f"({val[2]:.0f}). Because the one-slope model predicted the unseen months just as well, these monthly "
                "differences are not shown to improve prediction.")

            chart_head("How good is it on months it never saw?",
                       "Bar height is the typical error in mm/month over the 16 test months — lower is better. Every "
                       "model is scored on exactly the same months.")
            names = ["Our equation", "One-slope model", "Repeat last month", "Normal month"]
            rmse = [tr.rmse_selected, tr["rmse_linear@lag0"], tr.rmse_persistence, tr.rmse_climatology]
            skill = [tr.msess_selected, tr.msess_linear_lag0, tr.msess_persistence, 0.0]
            pf = go.Figure(go.Bar(
                x=names, y=rmse, marker_color=[EQ, LIN, "#4F7CA8", CLIM],
                text=[f"{r:.1f} mm" for r in rmse], textposition="outside",
                customdata=skill, hovertemplate="%{x}: %{y:.1f} mm/month (skill %{customdata:.2f})<extra></extra>"))
            pf.update_layout(yaxis=dict(title="typical error (mm/month)", range=[0, max(rmse) * 1.3]))
            st.plotly_chart(pretty(pf, 340), use_container_width=True, key="eq_perf")
            see(f"Both ENSO equations clearly beat a normal-month guess ({tr.rmse_climatology:.1f} mm) and simply "
                f"repeating last month ({tr.rmse_persistence:.1f} mm). Our equation: {tr.rmse_selected:.1f} mm; the "
                f"one-slope model: {tr['rmse_linear@lag0']:.1f} mm.")

            with st.expander("Technical details — how the equation was chosen and tested"):
                st.markdown(
                    f"Selected by a pre-stated rule on 2014–2019 validation data, frozen (commit 1395389), then tested "
                    f"once on {tst['test_period'][0]} to {tst['test_period'][1]}. Region R3 uses regions derived from "
                    f"training years only. Lag 0 means RONI is centred on the rainfall month (its 3-month window includes "
                    f"the next month), so this is a concurrent association, not a forecast.")
                st.markdown(
                    f"Equivalent form: ΔP = a + b_m·RONI with P = C(m) + ΔP. Coefficients (95% block-bootstrap CI): "
                    + "; ".join(f"{k} = {v['value']:.2f} [{v['ci95'][0]:.1f}, {v['ci95'][1]:.1f}] {v['units']}"
                                for k, v in cf.items())
                    + f". Skill = 1 − MSE/MSE(climatology): equation {tr.msess_selected:.2f} (95% CI "
                    f"{tr.msess_ci95[0]:.2f}–{tr.msess_ci95[1]:.2f}), one-slope {tr.msess_linear_lag0:.2f}, persistence "
                    f"{tr.msess_persistence:.2f}.")
                allt = pd.DataFrame(tst["results"])[["target", "selected", "reliable_on_validation", "n_test",
                                                     "msess_selected", "msess_linear_lag0", "msess_persistence"]]
                st.markdown("**All 12 region-season targets (validation choice and test skill)**")
                st.dataframe(allt.round(2), use_container_width=True, hide_index=True)
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    with st.expander("More technical details — data, regions, full statistics, methods and provenance"):
        index_choice = st.selectbox(
            "ENSO index for the record chart", ["RONI (NOAA official)", "ONI (sensitivity check)"],
            help="Per NWS Public Information Statement 26-05, NOAA CPC uses RONI for official ENSO "
                 "monitoring. ONI is kept as a sensitivity check.")
        st.divider()
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

        st.markdown("#### Analysis workflow")
        for i, (label, done) in enumerate(steps, 1):
            st.markdown(f"{'✅' if done else '⏳'} **Step {i}.** {label} — "
                        f"{'complete' if done else '*pending: not yet computed*'}")
        # ------------------------------------------------------------ methods etc.
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
    with o3:
        if not (RESULTS / "network_edges.csv").exists():
            st.warning("Not yet computed (Stage G).")
        else:
            edges = load_edges()
            meta = read_json(RESULTS / "network_nodes.json")
            section("The connections", "The dynamic scientific network")
            st.markdown("""<div class='bp-explain'>
<p><b>What you are looking at.</b> Each circle is something we measured: the ENSO index and three rainfall regions of
Indonesia, placed where they are on the map. Each line is a correlation computed from real 1998–2019 data. Unlike the
illustration at the top of the page, every line here comes from a calculation.</p>
<p><b>How to read it.</b> An <span style='color:#F2A65A'>amber</span> line means that region gets less rain when RONI is
high (El Niño-like). A <span style='color:#57B9F5'>blue</span> line means two regions' rainfall rises and falls together.
A dashed grey line means no clear link in this data — which is not proof that none exists. Thicker lines are stronger;
the number is the correlation, from −1 to +1.</p>
<p><b>What the controls do.</b> <i>Season</i> chooses which three months of rainfall to use. <i>Lag</i> looks at rain
0–3 months after the ENSO reading. <i>Time window</i> shows an 11-year slice, so you can see whether links change over the
years.</p></div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 1, 2])
            n_season = c1.radio("Season (rainfall months)", ["DJF", "MAM", "JJA", "SON"], index=3,
                                horizontal=True, key="net_season",
                                help="DJF = Dec–Feb, MAM = Mar–May, JJA = Jun–Aug, SON = Sep–Nov")
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
            enso_e = sel_e[sel_e.kind == "ENSO-region"]
            clear = [f"{r.target} ({r.r:+.2f})" for r in enso_e.itertuples() if r.status in ("supported", "CI excludes 0")]
            see(f"{SEASON_NAMES[n_season]}, lag {n_lag}, {n_win}: "
                + (f"clear ENSO links with {', '.join(clear)}." if clear else "no clear ENSO link in this view.")
                + (" Short windows hold only about 33 months each, so treat them as exploratory." if n_win != gnet.FULL else ""))
            note = meta["stage_h_notes"].get(f"R3-{n_season}", "")
            if f"R3-{n_season}" == (sel or {}).get("headline"):
                st.markdown(f"<p class='bp-read' style='text-align:center'>The eastern link (R3, {SEASON_NAMES[n_season]}) "
                            f"is the one our equation describes — {note}.</p>", unsafe_allow_html=True)

            chart_head("Do the links change over the years?",
                       f"Each square is one 11-year window ({SEASON_NAMES[n_season]}, lag {n_lag}). Red = less rain "
                       "with El Niño-like conditions, blue = more; ● = clear in that window.")
            roll_e = edges[(edges.kind == "ENSO-region") & (edges.season == n_season) &
                           (edges.lag == n_lag) & (edges.window != gnet.FULL)]
            piv = roll_e.pivot(index="target", columns="window", values="r")
            excl = roll_e.assign(x=(roll_e.ci_lo > 0) | (roll_e.ci_hi < 0)).pivot(
                index="target", columns="window", values="x")
            txt = piv.round(2).astype(str) + excl.map(lambda b: " ●" if b else "")
            hm2 = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, text=txt.values,
                                       texttemplate="%{text}", zmin=-1, zmax=1, colorscale="RdBu",
                                       colorbar=dict(title="r")))
            st.plotly_chart(pretty(hm2, 260), use_container_width=True, key=f"net_hm_{n_season}_{n_lag}")
            pats = pd.read_csv(RESULTS / "network_patterns.csv")
            pt = pats[(pats.kind == "ENSO-region") & (pats.season == n_season) & (pats.lag == n_lag)]
            rec = list(pt[pt.pattern == "recurring"].target)
            see((f"{' and '.join(rec)} keep the same clear link in almost every window — a recurring pattern. "
                 if rec else "No region keeps a clear link in most windows for this choice. ")
                + "With only 22 years, small changes over time cannot be detected.")
            with st.expander("Technical details — network statistics and definitions"):
                st.caption("Edge width ∝ |r|; label = r; hover for 95% CI, n, BH q and pattern. Full-period ENSO edges are "
                           "'supported' if BH q < 0.05 within the 48-test family; window edges use the bootstrap CI "
                           "only. Region–region links may share ENSO-driven variability. G-NETS is a proposed "
                           "investigational framework; links show association, not causation.")
                for reg in ["R1", "R2", "R3"]:
                    st.markdown(f"- Stage H, {reg}–{n_season}: {meta['stage_h_notes'].get(f'{reg}-{n_season}', '')}")
                shown = sel_e[["kind", "source", "target", "lag", "window", "r", "ci_lo", "ci_hi", "n",
                               "q_bh", "status", "pattern"]].rename(columns={"q_bh": "BH q (full period)"})
                st.dataframe(shown.round(3), use_container_width=True, hide_index=True, key="net_table")
                st.dataframe(pt[["target", "pattern", "windows_ci_excludes_0", "n_windows", "r_min", "r_max"]].round(2),
                             use_container_width=True, hide_index=True, key="net_patterns")
                st.caption("Pattern rules (beyond_prediction/network.py): recurring = same sign in all 12 windows and CI "
                           "excludes 0 in ≥ 9; weak-recurring = same sign, fewer; divergent = CI excludes 0 with opposite "
                           "signs in different windows; sign-variable = sign changes without that (inconclusive).")

    # ------------------------------------------------------------ four answers
    hyp_i = read_json(RESULTS / "stage_i_hypothesis.json")
    tst_i = read_json(RESULTS / "stage_h_test.json")
    if hyp_i and tst_i and (RESULTS / "network_patterns.csv").exists():
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
        all_jjason = sup["JJA"] == sup["SON"] == "R1, R2, R3"
        section("The answers", "Four scientific answers")
        st.markdown(f"<p class='bp-question'>{QUESTION}</p>", unsafe_allow_html=True)
        story([
            ("1 · How does the link change?",
             "Mainly with the <b>season</b>, not over the years. It is clear from June to November, appears only in the "
             f"east in December–February{', and is not detected in March–May' if sup['MAM'] == 'none' else ''}. Across "
             f"1998–2019 we found {'no' if n_change == 0 else 'some'} clear change over time — though a 22-year record can "
             "only detect large changes."),
            ("2 · Where does it change?",
             ("From June to November, in all three regions. " if all_jjason else "")
             + "In December–February, only <b>eastern Indonesia</b> shows a clear link. Whether the east truly differs "
               "from the rest is suggestive but not yet confirmed."),
            ("3 · In which direction?",
             f"Always the same way: El Niño-like conditions bring <b>less</b> rain, La Niña-like conditions bring more. "
             f"All {n_sup} clear links point this way; {'none' if sup_pos == 0 else sup_pos} point the other."),
            ("4 · By how much?",
             f"About <b>{abs(js.slope_mm_per_degC.max()):.0f}–{abs(js.slope_mm_per_degC.min()):.0f} mm less rain per month</b> "
             f"for each 1 °C of El Niño-like warming in June–November, and about {abs(r3d.slope_mm_per_degC):.0f} mm in the "
             f"east in December–February. Our equation reduces the monthly error for eastern Indonesia from "
             f"{r3.rmse_climatology:.0f} to {r3.rmse_selected:.0f} mm."),
        ], cls="bp-story bp-answers")
        with st.expander("Evidence and uncertainty behind the four answers"):
            st.markdown(f"""
**Nature of change.** Associations that pass correction (lag 0, BH q < 0.05): DJF {sup['DJF']} · MAM {sup['MAM']} ·
JJA {sup['JJA']} · SON {sup['SON']}. Over 1998–2019, {pc.get('recurring', 0)} of 48 ENSO→region edges are *recurring*
(same sign in all twelve 11-year windows, CI excluding 0 in ≥ 9) and {pc.get('divergent', 0)} are divergent;
{n_change} of 48 early-vs-late comparisons show a detectable change. No detectable change ≠ proof of stability.

**Location of change.** In DJF only R3 has a supported association; R1 and R2 are inconclusive (not evidence of no
relationship). The direct test of whether R3's DJF coefficient differs from R1/R2 is not significant (Holm p =
{A['R3-R1']['p_holm_surrogate']:.4f} and {A['R3-R2']['p_holm_surrogate']:.4f}): an observed pattern, not a confirmed difference.

**Direction of change.** All {n_sup} statistically supported ENSO→rainfall associations are negative; {sup_pos} are
positive. The only positive hint (R2 in DJF in recent windows) is inconclusive.

**Magnitude of change.** Jun–Nov, lag 0: {js.slope_mm_per_degC.max():.0f} to {js.slope_mm_per_degC.min():.0f} mm/month
per °C (r {js.r.max():.2f} to {js.r.min():.2f}); R3 in DJF: {r3d.slope_mm_per_degC:.0f} mm/month per °C. Held-out R3
Sep–Nov equation: error {r3.rmse_climatology:.1f} → {r3.rmse_selected:.1f} mm/month (skill {r3.msess_selected:.2f};
one-slope model {r3.msess_linear_lag0:.2f}). The 95% CIs for early-vs-late changes in r span about ±{hw.min():.2f} to
±{hw.max():.2f}.

**Evidence labels.** All numbers are COMPUTATIONAL RESULTS from NASA GPM IMERG V07B and NOAA CPC RONI; agreement with
PUBLISHED KNOWLEDGE (El Niño dries much of Indonesia in Jun–Nov) is noted; INDEPENDENT VALIDATION with other rainfall
data (CHIRPS, BMKG gauges) has not yet been performed. Associations are not causation.
""")

    # ------------------------------------------------------------ closing
    st.markdown("<div class='bp-quote'>“The universe whispers in patterns. Discovery begins when we learn to listen.”</div>",
                unsafe_allow_html=True)
    st.markdown(
        "<div class='bp-foot'>Music: Camille Saint-Saëns, <i>Le Cygne</i> (The Swan, No. 13), performed by Matilda "
        "Colliard (cello) and Stefano Ligoratti (piano), Classica Viva, Milan — licensed under "
        "<a href='https://creativecommons.org/licenses/by/4.0/' target='_blank'>CC BY 4.0</a>; source: "
        "<a href='https://commons.wikimedia.org/wiki/File:Camille_Saint-Sa%C3%ABns_-_Le_Cygne_(No._13)_-_Matilda_Colliard_and_Stefano_Ligoratti.ogg' "
        "target='_blank'>Wikimedia Commons</a> (MP3 version of the original Ogg file, as provided by Wikimedia). "
        "<br>Data: NASA GPM IMERG V07B · NOAA CPC RONI/ONI · Natural Earth. Team Hypatia · NASA Space Apps 2026.</div>",
        unsafe_allow_html=True)

