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
| D | Full period 1998-01..2025-09 (333 granules, 5.80 GiB transfer) | NEXT — awaiting approval |
| E | Regional series (derived clusters or labelled geographic fallback) | pending |
| F | Anomalies + season/lag/window associations, autocorrelation-aware, FDR | pending |
| G | Dynamic association network from computed metrics | pending |
| H | Interpretable equation search, time-blocked validation vs baselines | pending |
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

## Full-run estimate (Stage D)
333 granules, 5.80 GiB total transfer (CMR sizes), ≈ 13 min at measured speed, local cache
≈ 75 MB; global files deleted after each subset. Server-side OPeNDAP subsetting
(`opendap.earthdata.nasa.gov`) would need a new host + credential scope — not used.

## Open issues
- Region definitions restricted to Indonesia need a country boundary; no boundary dataset
  is available yet in this environment (decision needed in Stage E).
- IMERG 1998-01..2000-05 is TRMM-era input; NASA documents caveats.
- The `gpm1.gesdisc.eosdis.nasa.gov` credential is unused (files are served elsewhere).
