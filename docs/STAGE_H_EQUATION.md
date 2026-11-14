# Stage H — equation discovery and held-out evaluation

Produced by `scripts/run_equation_search.py`. The selection phase was committed before the
test phase ran (commit `1395389`, "freeze equation selection before held-out test").
Outputs are in `data/results/stage_h_*`.

## 0. Pre-checks (requested before Stage H)
**How each Stage F test's 66 observations are built**
- One observation per rainfall month in the season, for rainfall months 1998-01..2019-12: 3 months × 22 years.
- SON, MAM and JJA: 22 complete season-years.
- DJF: 23 season-years. That is 21 complete, plus Jan–Feb 1998 (DJF 1998) and Dec 2019 (which belongs to DJF 2020). The Stage F summary said "22 season-years" for every season; for DJF it is 23.
- **Dependence:** the 3 months within a season-year are consecutive, rainfall is autocorrelated, and each RONI value is a 3-month mean that overlaps its neighbours. Stage F handles this with an effective sample size (35–49 of 66) and with bootstrap blocks of whole season-years.

**Data split**, by rainfall month (`config/analysis.json`)
- Training: 1998-01..2013-12.
- Validation: 2014-01..2019-12.
- Test: 2020-01..2025-09 (69 months; 16–18 per season target).

**Leakage audit**

| Source | Status | Treatment in Stage H |
|---|---|---|
| Main regions R1–R3 (`regions.json`) | climatology 1998–2024: **overlaps validation and test** | not used in Stage H |
| Regions refitted on training years (`regions_k3train.json`) | climatology 1998–2013 only | **used**; adjusted Rand index 0.87 against the main regions |
| Stage F climatology | 1998–2019 (includes validation) | not used; Stage H refits the climatology inside every fit |
| Validation folds | climatology and coefficients from months ≤ Dec(Y−1) | strict |
| Final coefficients | fitted on 1998-01..2019-12 | strict with respect to the test period |
| Targets prioritised from Stage F (JJA, SON, R3 DJF) | chosen after seeing 1998–2019 data | **post-hoc**; the test period was not used to choose them |
| CPC index construction | RONI 1991–2020 base, ONI centred bases | index-level dependence, not removable |
| Lag 0 and 1 predictors | the RONI window for month t includes month t+1 | **concurrent association, not a forecast** |
| Regions for validation years before 2013 | k3train uses 1998–2013, so it overlaps early folds | only validation folds 2014–2019 are scored |

## 1. Candidate search (26 candidates per target, all linear in their coefficients)
**Variables**
- **y(t):** rainfall anomaly in mm/month, = P(t) − C(month), where P is the area-weighted IMERG monthly total and C the climatology estimated from the fit's own training months.
- **x_L:** RONI in °C, centred on month t−L.
- **y(t−1):** last month's rainfall anomaly.
- **1[m]:** indicator for calendar month m.

| Family | Equation | Coefficient units |
|---|---|---|
| climatology (baseline) | y = 0 | — |
| persistence (baseline) | y = φ·y(t−1) | φ dimensionless |
| linear (baseline) | y = a + b·x_L | a mm/month; b mm/month per °C |
| asymmetric | y = a + b₊·max(x_L,0) + b₋·min(x_L,0) | b± mm/month per °C |
| quadratic | y = a + b₁·x_L + b₂·x_L² | b₂ mm/month per °C² |
| linear + persistence | y = a + b·x_L + φ·y(t−1) | |
| month-varying slope | y = a + Σ_m b_m·1[m]·x_L | b_m mm/month per °C |
| linear + tendency | y = a + b·x_L + c·(x_L − x_{L+3}) | c mm/month per °C |

Every candidate except the two baselines is tried at lags 0–3. Every term is in mm/month.

**Validation:** expanding window, one validation year at a time for 2014–2019 (18 months per target).

**Selection rule** (fixed in code before running):
1. Find the candidate with the lowest validation mean squared error (MSE).
2. Among candidates within one standard error of that best (computed across the 6 years), take the one with the fewest parameters.
3. Call the target "reliable" only if the chosen model is not climatology or persistence, its skill against climatology (MSESS) exceeds 0.10, and it beats climatology in at least 4 of the 6 validation years.

**Headline rule:** among the priority targets judged reliable, pick the one with the highest validation skill.

## 2. Selection results (validation 2014–2019)

| Target | Selected | Validation MSESS | Years better than climatology | Reliable |
|---|---|---|---|---|
| R1-DJF | climatology | 0 | 0 | no |
| R1-MAM | linear+tendency, lag 0 | 0.19 | 5 | yes (not a priority target) |
| R1-JJA | persistence | 0.53 | 5 | no (baseline won) |
| **R1-SON** | **linear+persistence, lag 0** | **0.52** | **6** | **yes** |
| R2-DJF / R2-MAM | climatology | 0 | 0 | no |
| R2-JJA / R2-SON | persistence | 0.07 / 0.09 | 4 / 3 | no |
| R3-DJF | climatology | 0 | 0 | **no**: the Stage F DJF association did not give validated skill |
| R3-MAM / R3-JJA | persistence | 0.14 / 0.28 | 4 / 3 | no |
| **R3-SON** | **month-varying slope, lag 0** | **0.53** | **6** | **yes → headline** |

## 3. Headline equation (R3, Sep–Nov; regions fitted on training years)
```
ΔP_R3(t) = a + b_m · RONI(t)          for t in Sep, Oct, Nov
P_R3(t)  = C_R3(m) + ΔP_R3(t)
```

| Coefficient | Value (fit 1998–2019) | 95% CI, 2-year block bootstrap | Fit on 1998–2013 only | Units |
|---|---|---|---|---|
| a | −5.72 | [−15.03, 6.51] | −10.79 | mm/month |
| b_Sep | −59.64 | [−80.50, −28.68] | −43.85 | mm/month per °C |
| b_Oct | −65.47 | [−86.81, −49.89] | −65.02 | mm/month per °C |
| b_Nov | −21.68 | [−31.78, −12.15] | −25.55 | mm/month per °C |

- **Climatology C_R3** (1998–2019): Sep 237.65, Oct 218.16, Nov 222.48 mm/month.
- **In-sample fit:** n = 66, R² = 0.51, RMSE = 44.6 mm/month, residual lag-1 autocorrelation −0.16.

**Held-out test, 2020-01..2025-09** (16 months, 6 season-years; run once):

| Model | RMSE (mm/month) | Skill vs climatology (MSESS) |
|---|---|---|
| Selected equation | 44.1 | **0.59** (95% bootstrap CI [0.46, 0.64]) |
| Climatology | 69.0 | 0 |
| Persistence | — | 0.47 |
| Linear, lag 0 | — | **0.64** |

**The simpler linear lag-0 model did at least as well on the test period,** so the three separate monthly slopes show no out-of-sample benefit. Other test-period details:
- Correlation between predicted and observed anomalies: 0.70.
- Mean residual (observed − predicted): +12.1 mm/month; residual SD 43.8; largest |residual| 71.4 (Nov 2021).
- The test period contains three La Niña SON seasons (2020–2022), one El Niño (2023) and weak La Niña conditions in 2024–2025, so the skill rests on a handful of ENSO events.

**Other test results** (each MSESS against climatology):
- R1-SON: 0.69 [0.60, 0.78].
- R1-JJA (persistence): 0.46, where the linear lag-0 model scored 0.60.
- R3-JJA: 0.23.
- R2-SON: 0.20.
- **R3-DJF:** the linear lag-0 model scored 0.33 on test, but validation chose climatology. We report the validation decision and treat the test score as an observation, not as a reason to re-select.

## 4. Worked example (real data, test period; chosen as the test month with the largest |RONI|)
Month: **November 2020**, region R3 (training-derived k = 3 regions).

1. RONI for OND 2020, centred on November, from `data/raw/enso/RONI.ascii.txt`: **x = −1.46 °C**.
2. Anomaly: ΔP = a + b_Nov·x = −5.7247 + (−21.6756)(−1.46) = −5.7247 + 31.6464 = **+25.92 mm/month**.
3. Total: P̂ = C_R3(Nov) + ΔP = 222.48 + 25.92 = **248.41 mm/month**. C_R3(Nov) is the mean of the 22 Novembers 1998–2019 in `imerg_regional_monthly_k3train.csv`.
4. Observed: P = **252.59 mm/month** (row `2020-11,R3`), so the observed anomaly is +30.11 and the error is +4.18 mm/month.

All 16 test months are listed in `data/results/stage_h_test_predictions.csv`. For example, October 2023 (RONI +1.30): predicted 127.3, observed 144.1 mm/month.

## 5. Domain of applicability and limitations
- **Scope:** IMERG V07B monthly totals, area-averaged over region R3 as defined by `regions_k3train`, months Sep–Nov only.
- **Range:** RONI between −1.63 and +2.18 °C (the fitted range). Extrapolating outside it is unsupported.
- **Not a forecast:** lag 0 means RONI centred on month t, which includes SST from month t+1. It describes a **concurrent statistical association**.
- **Not a physical law:** it is a linear association fitted to 22 years. Coefficients are only meaningful relative to this climatology, these regions and this dataset.
- **Small sample:** 18 validation months and 16 test months. The bootstrap CIs rest on about 6 season-years and are optimistic about how general the result is.
- **Post-hoc targets:** priority targets were chosen after Stage F, and the one-standard-error rule involves judgement. Only the single test run is out of sample.
- **Leftover pattern:** in the La Niña SON seasons of the test period (2020–2022), residuals are positive in September and November (up to +71 mm/month) but negative in October (−17 to −49 mm/month). The equation does not capture these month-specific La Niña departures. No pattern was tested.
- **The Indian Ocean Dipole is not included.**
