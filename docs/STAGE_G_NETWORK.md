# Stage G — dynamic association network (G-NETS prototype)

Built by `scripts/build_network.py` from the Stage F results. Rules are in `beyond_prediction/network.py`. Cached outputs: `data/results/network_edges.csv`, `network_patterns.csv` and `network_nodes.json`.
G-NETS is a **proposed investigational framework**. This network is a set of computed statistical associations, not a causal graph and not a topological invariant.

## Definitions
- **Nodes:** ENSO (RONI, °C; drawn at a schematic Pacific position) and the rainfall regions R1–R3 (main k = 3 regions, anomaly in mm/month), drawn at their area-weighted centroids.
- **ENSO→region edges** (copied, not recomputed): Pearson r between RONI centred on month t and the rainfall anomaly in month t+lag, for rainfall months in the selected season.
  - Full discovery period 1998–2019: 48 edges from `associations_primary.csv`, with block-bootstrap CI, n = 66, effective n and BH q.
  - Rolling windows: 576 edges from `rolling.csv` (12 overlapping 11-year windows, about 33 pairs each).
- **Region–region edges** (computed in Stage G, exploratory): same-month rainfall anomaly correlations, with the same 2-year block-bootstrap CI, on the discovery period only.
- **Edge status:**
  - Full-period ENSO edges are *supported* if BH q < 0.05 within the 48-test family, and *inconclusive* otherwise.
  - Window edges and region–region edges show *CI excludes 0* or *inconclusive*. Windows overlap and get no multiple-testing correction.
- **Pattern labels across windows** (fixed rules):
  - *recurring:* same sign in all 12 windows, and the CI excludes 0 in at least 9.
  - *weak-recurring:* same sign throughout, but the CI excludes 0 in fewer windows.
  - *divergent:* the CI excludes 0 with opposite signs in different windows.
  - *sign-variable:* the sign changes, but never with significance on both sides. This is inconclusive.
- **Link to Stage H:** every edge's hover text and the panel under the graph show the Stage H validation choice and held-out skill for that region and season.

## What the network shows (COMPUTATIONAL RESULTS, discovery period 1998–2019)

**1. Supported ENSO edges** (full period, BH q < 0.05):

| | lag 0 | lag 1 | lag 2 | lag 3 |
|---|---|---|---|---|
| DJF | 1 (R3) | 1 | 1 | 1 |
| MAM | 0 | 0 | 0 | 0 |
| JJA | 3 | 3 | 1 | 0 |
| SON | 3 | 2 | 2 | 2 |

All supported ENSO edges are negative: less rain when RONI is high.

**2. Recurring over time.** At lag 0, R1–JJA, R1–SON, R2–JJA, R3–DJF and R3–SON have CIs excluding 0 in all 12 windows; R2–SON and R3–JJA in 11 of 12. All of these are *recurring*. Across all 48 ENSO edges: 24 recurring, 7 weak-recurring, 17 sign-variable and **0 divergent**.

**3. Divergence across space, not time.** In DJF, ENSO→R3 recurs while ENSO→R1 and ENSO→R2 are sign-variable. The region–region links tell the same story:
- R2–R3 DJF: r = 0.04 [−0.29, 0.39], inconclusive (sign-variable across windows).
- R1–R2 DJF: r = 0.54; R1–R3 DJF: r = 0.42.
- In JJA and SON all three region pairs are strongly linked (r = 0.59–0.84, recurring).

So in the wet season the eastern region decouples from the north-west, both in its rainfall and in its ENSO link.

**4. The only hint of change over time is inconclusive.** For ENSO→R2 in DJF at lag 0:
- r is −0.11 in 1998–2008 and between +0.25 and +0.29 in the four latest windows (2006–2016 to 2009–2019), where the CI excludes 0.
- The non-overlapping halves comparison (Stage F) gives Δr = +0.36, 95% CI [−0.15, 0.76]: no detectable change.
- The full-period edge is inconclusive (r = 0.10, q = 0.66).

**5. Link to the equation.**
- **R3–SON** is a supported, recurring edge (r = −0.65 at lag 0) and is the target of the frozen Stage H headline equation. Held-out skill against climatology is 0.59, and the simpler linear lag-0 model scored 0.64.
- **R1–SON:** supported and recurring; validated equation with test skill 0.69.
- **R3–DJF:** supported and recurring, but **no validated equation** (Stage H validation chose climatology). Association and predictive skill came apart here.

## Uncertainty and limits
- **Short record:** 22 years, about 33 pairs per window, overlapping windows. Recurrence means "no detected change", not proven stability.
- **Weak or absent edges** show missing statistical support, not missing physical connection.
- **Region–region links** may share ENSO-driven variability, so they are not independent pathways.
- **Regions came from the data** (1998–2024 climatology). Stage H used training-only regions, which give nearly identical Stage F results.
- **Lags are not independent evidence,** because RONI's lag-1 autocorrelation is 0.95.
- **Some SON association is shared with the IOD,** especially in R2 (see `IOD_SENSITIVITY.md`).
