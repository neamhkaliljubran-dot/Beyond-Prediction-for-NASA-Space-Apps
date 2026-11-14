# Implementation status — Beyond Prediction

Persistent record of completed vs pending work. Update on every checkpoint.
Branch: `claude/laughing-knuth-deo1i4` (never merge to `main` without review).

## Labels used throughout
OBSERVED DATA · PUBLISHED KNOWLEDGE · COMPUTATIONAL RESULT · CANDIDATE HYPOTHESIS · INDEPENDENT VALIDATION

## Stages
| Stage | Description | Status |
|---|---|---|
| A | Existing code preserved; ONI/RONI definitions + provenance verified | DONE |
| B | One real IMERG granule → Indonesia box subset, validated | DONE |
| C | 12-month contiguous sample (2024-10..2025-09), resume verified | DONE |
| D | Full period 1998-01..2025-09 (333 granules, 5.80 GiB transfer) | DONE |
| E | Indonesian territory mask + IMERG-derived regions R1–R3 + regional series | DONE |
| F | Anomalies + season/lag/window associations, autocorrelation-aware, FDR | DONE (exploratory; see docs/STAGE_F_FINDINGS.md) |
| G | Dynamic association network from computed metrics | DONE (docs/STAGE_G_NETWORK.md) |
| H | Interpretable equation search, time-blocked validation vs baselines | DONE (docs/STAGE_H_EQUATION.md) |
| I | Candidate hypotheses from computed evidence | pending |
| J | Integrate outputs into Streamlit, end-to-end tests, docs | pending |

## Verified facts
- **ENSO** (`data/processed/enso_monthly.csv`, 1950-01..2026-09): CPC `oni.ascii.txt` matches
  the ERSSTv6 ONI table; RONI is NOAA's official index per NWS PNS 26-05. Both retained;
  app defaults to RONI, ONI is a sensitivity check. Seasons mapped to centre month.
- **IMERG** `GPM_3IMERGM` V07B (CMR `C2723754851-GES_DISC`): 333 monthly granules,
  1998-01..2025-09, no missing months. `Grid/precipitation` dims (time, lon, lat),
  units mm/hr, fill −9999.9, 0.1° grid, lon −179.95..179.95 (no wrap needed).
  mm/month = rate × hours from `time_bnds` (Feb 2025 = 672 h, Sep 2025 = 720 h).
- **Land/sea mask**: GES DISC `GPM_IMERG_LandSeaMask` V2 (DOI 10.5067/6P5EM1HPR3VD), percent
  water, same grid. Spot checks: Borneo/Sumatra/Papua 1–2 %, Banda/Java Sea 100 %.
  Current land threshold: water < 50 % (to be confirmed in Stage E).
- **Access**: Earthdata token on `data.gesdisc.earthdata.nasa.gov`, account has authorised
  "NASA GESDISC DATA ARCHIVE"; downloads redirect to `d2b3c3wh8s6en5.cloudfront.net`.
  CMR publishes no checksums → byte size checked against CMR, SHA-256 recorded.

## Pipeline (Stage B/C)
`scripts/fetch_imerg_subset.py --start YYYY-MM --end YYYY-MM`
- Box: cell centres 94.05–141.95 °E, 11.95 °S–6.95 °N (480 × 190 cells). The box also
  contains parts of Malaysia, Brunei, Timor-Leste, PNG, Singapore, the southern Philippines.
- Per month: download → size check → SHA-256 → subset + grid/units/time checks → atomic
  `.npz` write → delete global file → manifest row. Skips months already cached.
- Outputs: `data/interim/imerg_box/YYYY-MM.npz` (local, gitignored, ~230 KB each),
  `data/interim/imerg_landsea_box.npz`, `data/provenance/imerg_manifest.csv`,
  `data/provenance/imerg_granules.csv`.

## Stage C measured results (12-month SAMPLE only — no scientific conclusions)
- 11 downloads, 17.3–18.3 MiB each, 1.9–5.3 s each (27 s total); peak RSS ≈ 173 MiB.
- 0 fill values in the box in all 12 months; re-run fetched 0 (resume works).
- OBSERVED DATA, descriptive only: area-weighted mean over box land cells (water < 50 %),
  mm/month: Oct 244.0, Nov 299.7, Dec 336.4, Jan 395.0, Feb 249.6, Mar 336.6, Apr 302.5,
  May 268.0, Jun 231.1, Jul 183.8, Aug 265.4, Sep 274.2 (2024-10..2025-09). Box land includes
  non-Indonesian territory; not a regional result.

## Stage D — full run (measured)
- 321 new + 12 cached = **333/333 months**, 1998-01..2025-09; 667 s; 0 retries, 0 failures.
- Manifest: 333 unique months, 333 unique SHA-256, 0 byte-size mismatches vs CMR, 5.80 GiB.
- 0 fill/NaN values in the box in any month; temp dir empty (no global files retained).
- `time_bnds` hours == calendar days × 24 for every month (leap Februaries = 696 h).
- Local cache `data/interim/imerg_box/` = 73 MB (gitignored, reproducible from the script).

## Stage E — Indonesian territory and regions (`scripts/build_regions.py`)
- Territory: Natural Earth 1:10m Admin-0 v5.1.1 (`ADM0_A3 == IDN`, public domain), zip SHA-256
  in `data/provenance/regions.json`. Grid area estimate 153.08 deg² vs polygon 153.08 deg².
- Cell rule: Indonesian fraction ≥ 0.5 (10×10 sub-points) AND IMERG water < 50 %.
  17 842 cells touch Indonesia; **14 443 included**; 2 566 excluded as mostly non-Indonesian or
  sea; 833 excluded only by the IMERG water criterion (coasts, large lakes, e.g. Lake Toba).
  Included cells hold 92.6 % of Indonesian land area. 190 of 264 Natural Earth polygons (small
  islands) contain no included cell centre: 1.27 % of Indonesian land area.
- Regions: k-means (k = 3, a priori) on standardised 1998–2024 climatological annual cycles.
  Labels R1–R3 — **not** Aldrian & Susanto A/B/C. Seed ARI = 1.00 (5 seeds);
  year-bootstrap ARI median 0.82 (min 0.60, max 0.90, n = 20); silhouette k=2 0.40,
  k=3 0.33, k=4 0.31 → k = 3 is not the silhouette optimum.
- COMPUTATIONAL RESULT (climatology descriptors, 1998–2024):
  R1 54 % of area, centroid 118.2 °E 3.8 °S, wettest Mar, driest Aug, single broad
  Nov–Apr wet season. R2 28 %, 106.2 °E 1.1 °N, maxima Apr and Nov, driest Jul.
  R3 19 %, 130.9 °E 2.6 °S, wettest Jun, driest Oct.
  These shapes *qualitatively resemble* the published monsoonal / semi-monsoonal /
  anti-monsoonal types; no boundary equivalence is claimed or tested.
- Series: `data/processed/imerg_regional_monthly.csv`, R1–R3 + ALL, 333 months each,
  mm/month, cos-latitude area weights, valid-area fraction 1.0 every month, no gap filling.
- Map: `docs/figures/regions_map.png`. Regions are not forced to be contiguous; a few
  outlying cells exist (e.g. R2 cells east of 127 °E).

## Stage F — associations (`scripts/run_associations.py`, `config/analysis.json`)
- Split fixed before any ENSO–rainfall statistic: training 1998-01..2013-12, validation
  2014-01..2019-12, **test 2020-01..2025-09 (69 months), not read so far**. Stage F used the discovery
  period 1998-01..2019-12 only (asserted in code).
- Anomalies: mm/month (primary), standardised and percent (supplementary), climatology
  1998–2019. Stage H must re-estimate climatology inside each training fit.
- Primary family: RONI × R1–R3 × DJF/MAM/JJA/SON × lags 0–3 = 48 tests. Surrogate p (2000 surrogates),
  ESS t-test, 2-year block bootstrap CIs, BH within family. 20/48 (surrogate) and 22/48 (ESS)
  have q < 0.05; the methods agree on 44/48.
- Sensitivity (each with its own BH): ONI, k=2, k=3 fitted on 1998–2013, Indonesia-wide, seasonal means.
  Exploratory: 11-yr rolling windows, non-overlapping halves. Illustrative family: SON/RONI/lag 0, Holm.
- Key observations: negative associations in JJA and SON in all regions; DJF only in R3 (east);
  MAM none after correction; 0/48 changes between halves detectable. Full report: `docs/STAGE_F_FINDINGS.md`.
- Region variants: `regions_k2.json` (ARI vs main 0.39), `regions_k3train.json` (ARI 0.87).
- App: Stage F section (heatmap, table, rolling chart, sensitivity) — step 5 marked complete.

## Stage H — equation discovery (`scripts/run_equation_search.py`)
- Regions refitted on training years (k3train), climatology refitted inside every fit, 26 candidates per target
  (baselines, linear, asymmetric, quadratic, persistence, month-varying slope, tendency; lags 0–3),
  expanding-window validation 2014–2019, one-standard-error parsimony rule fixed in code.
- Selection frozen and committed (`1395389`) before the single test run on 2020-01..2025-09.
  One reporting bug (pandas column-name clash) crashed the first test run before any metric
  was computed; it was fixed without touching the selection.
- Reliable on validation: R1-SON (linear+persistence lag 0), R3-SON (month-varying slope lag 0, headline),
  R1-MAM. R3-DJF → climatology (Stage F's DJF signal gave no validated skill).
- Headline test result: skill vs climatology (MSESS) 0.59 [0.46, 0.64], RMSE 44.1 vs 69.0 mm/month; linear lag 0
  scored 0.64 → no demonstrated benefit from the month-specific slopes. Worked example Nov 2020 reproduced
  from raw files. App Output 2 tab is live.

## IOD sensitivity (optional, `scripts/run_iod_sensitivity.py`)
- NOAA PSL HadISST1.1 DMI; host psl.noaa.gov added; re-anomalised 1998–2019; 3-month centred mean.
- RONI associations persist after controlling for DMI except R2 SON (weakens). Adding DMI to the headline
  equation did not improve validation RMSE. See docs/IOD_SENSITIVITY.md.

## Stage G — network (`scripts/build_network.py`)
- Skill metric defined and verified (`scripts/verify_stage_h_metrics.py`): R3-SON 0.5922 vs linear lag 0
  0.6420 on identical 16 test months and baseline; frozen selection unchanged.
- Edges copied from Stage F (48 full-period + 576 window ENSO edges) plus exploratory region–region
  edges; status and pattern rules fixed in code. Tests confirm every ENSO edge matches Stage F output and
  that the app's season/lag/window/region-link controls change the displayed edges (Streamlit AppTest).
- Findings: supported ENSO edges at lag 0: DJF 1 (R3), MAM 0, JJA 3, SON 3; 0 divergent patterns;
  DJF spatial decoupling of R3; R2-DJF positive in recent windows but no detectable change.

## NEXT: Stage I (hypotheses) + integrated answer — paused for review with the team.

## Open issues
- Main regions use the 1998–2024 climatology (overlaps test). Training-only regions (1998–2013) give
  nearly identical associations. Regions use the full period's climatology (annual cycle only, not ENSO); a held-out period
  for Stage H/I validation is therefore not fully independent of the region definition.
- Natural Earth boundaries are generalised; land/sea thresholds (50 %) are untested choices —
  sensitivity analysis pending.
- IMERG 1998-01..2000-05 is TRMM-era input; NASA documents caveats.
- The `gpm1.gesdisc.eosdis.nasa.gov` credential is unused (files are served elsewhere).
