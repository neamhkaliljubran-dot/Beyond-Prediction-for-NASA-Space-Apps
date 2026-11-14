"""Stage G: dynamic association network built only from computed Stage F metrics.

Nodes
  ENSO   RONI (degC), NOAA CPC, Nino-3.4 based, relative to the tropical mean.
  R1-R3  IMERG-derived Indonesian rainfall regions (main k=3 regions), anomaly mm/month.

Edges (each row of data/results/network_edges.csv is one computed statistic)
  ENSO->Ri  Pearson r between RONI centred on month t and rainfall anomaly in month t+lag,
            for rainfall months in the season and time window.
  Ri--Rj    Pearson r between same-month rainfall anomalies of two regions (season, window).

Edge status (rules fixed in this module):
  full discovery period (1998-2019), ENSO edges: "supported" if BH q < 0.05 within the
      48-test family (surrogate p); otherwise "inconclusive".
  region-region edges and rolling windows: "CI excludes 0" if the 95% block-bootstrap CI
      excludes zero, otherwise "inconclusive". Windows overlap and are NOT independent tests.

Pattern labels across the 12 rolling windows (per edge, season, lag):
  recurring      same sign in all windows AND CI excludes 0 in >= 9 of 12 windows
  weak-recurring same sign in all windows, CI excludes 0 in fewer than 9 windows
  divergent      CI excludes 0 with a positive r in some window and a negative r in another
  sign-variable  sign changes, but never with CI excluding 0 on both sides (inconclusive)
None of these labels is a causal or topological statement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FULL = "1998-2019 (full discovery period)"
RECUR_MIN = 9


def edge_status(row: pd.Series) -> str:
    if row["window"] == FULL and row["kind"] == "ENSO-region":
        return "supported" if row["q_bh"] < 0.05 else "inconclusive"
    return "CI excludes 0" if (row["ci_lo"] > 0 or row["ci_hi"] < 0) else "inconclusive"


def pattern(group: pd.DataFrame) -> str:
    g = group[group["window"] != FULL]
    excl = (g["ci_lo"] > 0) | (g["ci_hi"] < 0)
    pos_sig = ((g["ci_lo"] > 0)).any()
    neg_sig = ((g["ci_hi"] < 0)).any()
    same_sign = (np.sign(g["r"]).nunique() == 1)
    if pos_sig and neg_sig:
        return "divergent"
    if same_sign and excl.sum() >= RECUR_MIN:
        return "recurring"
    if same_sign:
        return "weak-recurring"
    return "sign-variable"


def patterns(edges: pd.DataFrame) -> pd.DataFrame:
    keys = ["kind", "source", "target", "season", "lag"]
    rows = []
    for k, g in edges.groupby(keys):
        w = g[g["window"] != FULL]
        rows.append({**dict(zip(keys, k)), "pattern": pattern(g),
                     "n_windows": len(w),
                     "windows_ci_excludes_0": int(((w.ci_lo > 0) | (w.ci_hi < 0)).sum()),
                     "r_min": float(w["r"].min()), "r_max": float(w["r"].max())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- figure
NODE_POS = {"ENSO": (146.0, 7.0)}          # schematic position toward the Pacific
NEG, POS, INC = "#F2A65A", "#57B9F5", "#7A8799"


def figure(edges: pd.DataFrame, node_pos: dict, equation_note: dict | None = None):
    import plotly.graph_objects as go

    fig = go.Figure()
    pos = {**NODE_POS, **node_pos}
    for _, e in edges.iterrows():
        (x0, y0), (x1, y1) = pos[e["source"]], pos[e["target"]]
        sig = e["status"] in ("supported", "CI excludes 0")
        color = INC if not sig else (NEG if e["r"] < 0 else POS)
        width = 1.5 + 12 * abs(e["r"])
        if e["kind"] == "region-region":                       # curve region-region edges
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2 - 2.5
            xs = [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t ** 2 * x1 for t in np.linspace(0, 1, 15)]
            ys = [(1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t ** 2 * y1 for t in np.linspace(0, 1, 15)]
        else:
            xs, ys = list(np.linspace(x0, x1, 15)), list(np.linspace(y0, y1, 15))
        hover = (f"<b>{e['source']} → {e['target']}</b><br>{e['kind']}, {e['season']}, lag {e['lag']} mo"
                 f"<br>window {e['window']}<br>r = {e['r']:.2f}  [95% CI {e['ci_lo']:.2f}, {e['ci_hi']:.2f}]"
                 f"<br>n = {int(e['n'])} monthly pairs<br>status: {e['status']}"
                 + (f"<br>BH q = {e['q_bh']:.3f}" if pd.notna(e.get("q_bh")) else "")
                 + (f"<br>pattern across windows: {e['pattern']}" if "pattern" in e and pd.notna(e["pattern"]) else ""))
        if equation_note and e["kind"] == "ENSO-region":
            note = equation_note.get(f"{e['target']}-{e['season']}")
            if note:
                hover += f"<br><i>Stage H: {note}</i>"
        fig.add_scatter(x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                        line=dict(color=color, width=width, dash="solid" if sig else "dash"))
        mid = len(xs) // 2
        fig.add_scatter(x=[xs[mid]], y=[ys[mid]], mode="markers+text", text=[f"{e['r']:+.2f}"],
                        textposition="top center", marker=dict(size=14, color=color, opacity=0.25),
                        hovertext=hover, hoverinfo="text", showlegend=False,
                        textfont=dict(size=13, color=color))
    labels = {"ENSO": "ENSO<br>(RONI)"}
    for n, (x, y) in pos.items():
        fig.add_scatter(x=[x], y=[y], mode="markers+text", text=[labels.get(n, n)],
                        textposition="middle center",
                        marker=dict(size=48, color="#12304F" if n != "ENSO" else "#8275DA",
                                    line=dict(color="#57B9F5" if n != "ENSO" else "#E9F2FF", width=2)),
                        textfont=dict(color="#E9F2FF", size=13), hoverinfo="text",
                        hovertext=n, showlegend=False)
    for name, col, dash in [("negative r (supported): less rain when RONI is high — El Niño-like", NEG, "solid"),
                            ("positive r (supported): rainfall anomalies vary together (region–region)", POS, "solid"),
                            ("dashed grey: inconclusive — not proof of no relationship", INC, "dash")]:
        fig.add_scatter(x=[None], y=[None], mode="lines", name=name, line=dict(color=col, width=4, dash=dash))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False, range=[100, 152]), yaxis=dict(visible=False, range=[-9, 9.5],
                                                                             scaleanchor="x"),
                      legend=dict(orientation="h", y=-0.02, font=dict(size=12)))
    return fig
