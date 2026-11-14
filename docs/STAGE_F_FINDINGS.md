# Stage F findings — ENSO–Indonesian rainfall associations

Status: **exploratory**. Every number below comes from `scripts/run_associations.py`
(outputs in `data/results/`, settings in `config/analysis.json`). Nothing here is a
hypothesis, a fitted equation or a validated result.

## Setup
| Item | Choice |
|---|---|
| Discovery period | Rainfall months 1998-01..2019-12 (264 months). The test period 2020-01..2025-09 was **not read**. |
| Split for later stages | Training 1998-01..2013-12 · validation 2014-01..2019-12 · test 2020-01..2025-09 (69 months) |
| Rainfall | Area-weighted IMERG V07B, regions R1–R3. Anomaly = mm/month minus the 1998–2019 calendar-month mean. Standardised and percent anomalies are also reported. |
| ENSO | RONI (primary), ONI (sensitivity). Lag L means rainfall in month t+L is paired with ENSO centred on month t. Lags 0–1 overlap the 3-month ENSO window. |
| Seasons | Assigned by rainfall month: 66 monthly pairs per cell (22 season-years) |
| Inference | Persistence-preserving surrogates of ENSO with the seasonal subsetting kept (2000 surrogates; smallest possible p = 0.0005) · effective sample size from the ACF of both series · moving-block (2-year) bootstrap 95% CIs · BH within the declared 48-test family |
| Persistence | Lag-1 autocorrelation (ACF): RONI 0.95, ONI 0.95, rainfall anomalies R1 0.49, R2 0.17, R3 0.42 → n_eff ≈ 35 (R1, R3) and 49 (R2) out of 66 |

## OBSERVATIONS (computational results)
**O1. June–November: negative associations in every region.** Lag 0, RONI:

| Region | JJA r [95% CI] | JJA slope, mm/month per °C | SON r [95% CI] | SON slope |
|---|---|---|---|---|
| R1 | −0.72 [−0.82, −0.52] | −55 [−72, −38] | −0.67 [−0.78, −0.51] | −46 [−56, −34] |
| R2 | −0.60 [−0.73, −0.39] | −59 [−78, −35] | −0.38 [−0.53, −0.18] | −22 [−30, −11] |
| R3 | −0.60 [−0.71, −0.40] | −86 [−118, −63] | −0.65 [−0.74, −0.49] | −47 [−56, −36] |

All six have BH q < 0.05, and both inference methods agree.

**O2. December–February: only the eastern region R3 shows an association.**
- R3 DJF: r between −0.43 and −0.36 across lags 0–3; q ≤ 0.036 with surrogates.
- R1 and R2 in DJF: |r| ≤ 0.10 with CIs that include 0.

**O3. March–May: no association survives correction** in any region (largest |r| = 0.25, R3 lag 0, q = 0.37).

**O4. Lag structure.**
- In SON, |r| changes little from lag 0 to lag 3, while the slope grows (R1: −46 to −65 mm/month per °C), because ENSO values earlier in the year are smaller.
- In JJA, the association fades by lag 3 in R1 and R2.
- RONI's lag-1 ACF is 0.95, so the lags are **not independent** pieces of evidence.

**O5. Primary family totals:** 20 of 48 tests have q < 0.05 with surrogates, and 22 of 48 with the effective-sample-size method. The methods agree on 44 of 48. The four disagreements are borderline: R2 SON lags 1–3 and R3 DJF lag 3, with q between 0.035 and 0.081.

**O6. Change over time (exploratory).**
- **Rolling windows:** across the twelve 11-year windows (about 33 pairs each), every lag-0 r keeps a negative sign for JJA and SON in all regions and for R3 DJF. The CI excludes zero in every window for R1 JJA, R1 SON, R2 JJA, R3 DJF and R3 SON, and in 11 of 12 windows for R2 SON and R3 JJA.
- **R3 MAM:** negative in all 12 windows, with the CI excluding 0 in 6, even though the full-period test is not significant (O3).
- **Sign flips:** R1 and R2 DJF change sign between windows (r from −0.25 to +0.29), but their CIs always include 0.
- **Non-overlapping halves (1998–2008 vs 2009–2019):** none of the 48 bootstrap CIs for the change in r excludes 0. The CIs are about ±0.3 to ±0.6 wide, so **only large changes would be detectable**.

**O7. Sensitivity checks.**
- **ONI instead of RONI:** r differs by at most 0.14 (R1 JJA lag 1: −0.63 RONI vs −0.48 ONI). Significance agrees on 44 of 48 cells. ONI makes R2 SON lags 1–3 significant and R3 JJA lag 2 not significant.
- **k = 3 regions fitted on 1998–2013 only:** r differs by at most 0.05, and significance agrees on 47 of 48 cells. These regions match the main ones closely (adjusted Rand index 0.87).
- **k = 2 regions** (a large western/southern region plus an eastern one; adjusted Rand index 0.39 against k = 3): JJA and SON stay negative in both. The DJF association appears only in the eastern region (r = −0.48), the same pattern as R3.
- **Indonesia as a whole:** JJA r = −0.71 and SON r = −0.65; DJF and MAM are not significant. The national average hides the eastern DJF signal.
- **Seasonal means (one value per season-year, n = 21–22):** lag-0 r = −0.85 / −0.78 (R1 JJA / SON), −0.81 / −0.64 (R2), −0.73 / −0.84 (R3), and −0.72 for R3 DJF. All have q ≤ 0.003. DJF and MAM in R1 and R2 are not significant.

**O8. Illustrative test family (SON, RONI, lag 0, R1–R3; Holm correction).** Holm-adjusted p = 0.0015 (R1), 0.015 (R2) and 0.0015 (R3) with surrogates; ≤ 0.008 with the effective-sample-size method. This family was set in advance, but the regions came from the data and the same years were analysed, so **it is not confirmatory**.

## INTERPRETATIONS (qualified, not tested here)
- **I1. Agreement with published work.** O1–O3 agree with **published knowledge** that El Niño is associated with reduced Indonesian rainfall mainly in the dry and transition seasons (Jun–Nov), and weakly in the wet season. Our analysis doesn't test the physical mechanism; published explanations involve a shifted Walker circulation and regional sea-surface temperatures.
- **I2. Possible "divergent pattern" in DJF.** The east (R3, or the eastern k = 2 region) keeps a wet-season association that the west and south lack. It holds across lags, regionalizations, aggregation choices and every rolling window, which makes it a **candidate for hypothesis generation in Stage I**. It is not yet a hypothesis.
- **I3. No detectable change over time in 1998–2019.** With 22 years and wide intervals, this means "no change large enough to detect", **not** "proven stable". The fixed question asks whether relationships change over time; on this evidence the answer so far is that the main relationships recur in every window, and change is not shown.
- **I4. Lags.** Lagged associations largely reflect ENSO's own persistence. The lag pattern alone can't separate a delayed rainfall response from simple persistence of ENSO.

## Limitations
- **Regions were defined from the 1998–2024 annual cycle,** which overlaps the test period. The training-only regions give nearly identical results (O7), but strict independence is not claimed.
- **The surrogate p floor is 0.0005** (2000 surrogates), so the smallest BH q is about 0.004.
- **The surrogates destroy ENSO's tendency to peak in particular seasons.** Results are checked against the effective-sample-size method, and the block bootstrap keeps whole years.
- **The Indian Ocean Dipole has not been included.** It co-varies with ENSO in SON and could account for part of the SON association.
- **Interpreting single lags:** monthly pairs within a season are not independent (handled through n_eff), and 3-month ENSO values overlap in time.
- **The CPC base periods overlap later years.** That is a property of how the indices are built and cannot be removed.
- **IMERG before June 2000 is TRMM-era input.** Regions with few rain gauges carry larger retrieval uncertainty, which is not propagated here.
