# Stage I — candidate hypothesis, direct test, and the integrated answer

Script: `scripts/run_hypothesis_test.py`. The specification and decision rule are in its docstring and were written before it was run. Results: `data/results/stage_i_hypothesis.json`, `stage_i_djf_points.csv` and `stage_i_equation_panel.csv`.

## 1. Primary candidate hypothesis (CANDIDATE HYPOTHESIS)
> During DJF, the association between RONI and monthly rainfall anomalies in eastern Indonesia (R3) differs from that in R1 and R2: R3 rainfall decreases more per °C of RONI.

- **Coefficient:** β_k is the OLS slope of rainfall anomaly (mm/month) on RONI (°C) for region k, using DJF rainfall months at lag 0.
- **H₀:** β_R3 = β_R1 and β_R3 = β_R2. **H₁:** each pair differs (two-sided; the expected direction is β_R3 < β_Rk).
- **Direct test of the difference:**
  - All regions share the same months and RONI values, so β_R3 − β_Rk is *exactly* the slope of d(t) = y_R3(t) − y_Rk(t) on RONI(t). This identity is asserted in the code and in the tests.
  - Testing that single slope keeps the shared ENSO observations and the correlation between regions' rainfall.
  - Different significance levels in separate regions are **not** used as evidence of a difference.
- **Inference:**
  1. **Primary:** 2000 persistence-preserving RONI surrogates, with Holm correction across the 2 contrasts.
  2. Effective-sample-size t-test, using the ACFs of RONI and d.
  3. Joint 2-year moving-block bootstrap of season-years, resampling all regions together.
- **Decision rule:** reject H₀ only if both Holm-adjusted surrogate p < 0.05 **and** both bootstrap CIs exclude 0.

## 2. Results

**A. Discovery data, 1998-01..2019-12** (main regions; 66 months, 23 season-years). This is the data that generated the hypothesis, so the test is **in-sample**.

| Region | β (mm/month per °C) | 95% CI |
|---|---|---|
| R1 | −2.59 | [−9.82, 6.94] |
| R2 | +3.77 | [−4.86, 12.89] |
| R3 | −15.89 | [−24.79, −11.02] |

| Contrast | Δβ | 95% CI | p (surrogate) | Holm p | p (eff. sample size) | n_eff |
|---|---|---|---|---|---|---|
| R3 − R1 | −13.30 | [−29.23, −3.41] | 0.0975 | **0.0975** | 0.0164 | 43.0 |
| R3 − R2 | −19.67 | [−34.58, −8.46] | 0.0440 | **0.0880** | 0.0078 | 50.2 |

**Decision: H₀ is not rejected. The hypothesis is not supported at α = 0.05 under the pre-stated rule.**
- The direction matches the hypothesis, and both bootstrap CIs exclude 0.
- The effective-sample-size test gives p < 0.05 for both contrasts.
- The primary persistence-preserving test does not reach p < 0.05 after Holm correction.
- **Why the methods disagree:** they treat dependence differently. The surrogates scramble ENSO's tendency to peak in particular seasons, which matters in DJF, its peak season, while the effective-sample-size method assumes stationarity. We follow the pre-stated primary method.

**B. Held-out months, 2020-01..2025-09** (regions fitted on training years; 1998–2019 climatology; 17 DJF months, 6 season-years). This is a temporal check, not independent validation.
- R3 − R1 = −18.1 (Holm p 0.37). R3 − R2 = −46.3 (Holm p 0.37).
- Same sign as the discovery data; **not significant**.
- With 6 season-years the bootstrap CIs are unstable; for example, R1's CI is [−76, 4].
- These months were already used in the Stage H evaluation, though no selection was based on them.

**C. Sensitivity checks** (discovery data). Every variant keeps the same sign, and none meets the rule. Holm surrogate p values:

| Variant | R3 − R1 | R3 − R2 |
|---|---|---|
| Regions fitted on training years | 0.17 | 0.12 |
| Standardised anomalies | 0.155 | 0.069 |
| Lags 1–3 | 0.125–0.133 | 0.125–0.133 |

**Falsification and independent validation plan:** reject the hypothesis if the R3 − Rk slope contrasts are not negative with 95% CIs excluding 0 in an independent rainfall product or gauge network (CHIRPS, BMKG stations), over the same or later years. **Not yet performed.**

## 3. Verification panels (in the app)
**TEST EQUATION** (Output 2)
- **Method:** pick any of the 16 held-out R3 Sep–Nov months. The app substitutes the real RONI value into the frozen equation and shows the arithmetic, then compares the result with the IMERG observation, the linear lag-0 reference and climatology.
- **Checks:** the live calculation is asserted to equal the stored Stage H prediction. The tests confirm that changing the month changes the result, and October 2023 shows the IMERG value 144.07 mm/month.
- **Example, Nov 2020:** RONI −1.46 °C → frozen equation 248.41, linear lag-0 282.94, climatology 222.48. Observed 252.59 mm/month.
- **Overall test skill** (16 months): frozen equation 0.59, linear lag-0 0.64.

**TEST HYPOTHESIS** (Output 1)
- Shows H₀ and H₁, the regional β values with CIs, the direct contrasts with all three inference methods, the decision against the rule, and a scatter plot with fitted lines.
- A selector switches between the discovery data, the held-out months and the sensitivity checks; the tests confirm it changes the displayed contrasts.

## 4. Integrated answer to the fixed question
*How do relationships between ENSO variability in the Pacific Ocean and rainfall across different regions of Indonesia change over time and across seasons, and do these changes reveal recurring or divergent patterns in a dynamic network?*

- **Across seasons** (COMPUTATIONAL RESULT, 1998–2019): the relationships are strongly seasonal.
  - Supported lag-0 associations: DJF in R3 only; none in MAM; R1, R2 and R3 in JJA and SON.
  - All are negative: less rain under El Niño-like RONI.
  - This agrees with PUBLISHED KNOWLEDGE.
- **Over time** (exploratory): 24 of 48 ENSO edges recur across the 12 overlapping 11-year windows, and 0 are divergent.
  - No change was detectable between 1998–2008 and 2009–2019, but the record is short and only large changes could be seen.
  - R2 in DJF turns positive in recent windows; that is inconclusive.
- **Recurring and divergent patterns:**
  - June–November recurs in every region.
  - The clearest divergence is spatial: in DJF the east (R3) carries the ENSO link and decouples from the north-west.
  - The direct test of that DJF difference is suggestive but **not significant** under the pre-stated rule.
- **Mathematical relationship:** for R3 in Sep–Nov, ΔP = a + b_m·RONI has held-out skill of 0.59 against climatology. A simpler one-slope model scored 0.64. It is a concurrent statistical relationship, not a forecast or a physical law.
- **Network:** G-NETS, a proposed framework, organises these associations as a network that changes with season, lag and window. It describes association only; it shows neither causation nor topological invariants.

## 5. Remaining limitations
- **No independent validation yet.** Everything uses IMERG V07B; the held-out months are a temporal check within the same product.
- **Short record** (22 + 6 years), with few ENSO events in the held-out period.
- **Regions came from the data** (training-only regions were checked). The IOD is only partly examined.
- **The inference methods disagree** for the DJF contrast. The decision follows the pre-stated primary method.
