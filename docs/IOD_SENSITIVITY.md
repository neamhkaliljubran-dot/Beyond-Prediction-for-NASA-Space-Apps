# IOD (DMI) sensitivity check

Script: `scripts/run_iod_sensitivity.py`. Outputs: `data/results/iod_sensitivity.csv` and `data/provenance/iod.json`.
Status: **sensitivity analysis on the discovery period (1998-01..2019-12) only. The test period was not used.**

## Data
- **Source:** NOAA PSL `dmi.had.long.data` (https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data); SHA-256 in `iod.json`.
- **Definition** (from the file header): HadISST1.1 SST anomaly averaged over 10°S–10°N, 50–70°E, minus the average over 10°S–0°, 90–110°E. Monthly, 1870 to May 2026; the file marks itself "Preliminary".
- **Base period:** not stated, and the landing page named in the file returns HTTP 404. We therefore re-anomalise DMI against its own 1998–2019 calendar-month means.
- **Alignment:** a centred 3-month mean (t−1..t+1), built the same way as RONI, paired with rainfall at lag 0.
- **Permissions:** public data; the only change was adding `psl.noaa.gov` to the environment's network allowlist.

## OBSERVATIONS (lag 0; partial correlations; BH within this 12-cell family)
- **RONI and DMI are correlated:** r = 0.53 in SON, 0.47 in DJF, 0.29 in JJA and 0.08 in MAM.
- **JJA:** the RONI association hardly changes once DMI is controlled for. Partial r = −0.70 (R1), −0.57 (R2), −0.64 (R3), all q < 0.001. DMI adds nothing significant.
- **SON:**
  - The RONI association remains in R1 (partial r −0.51, q 0.005) and R3 (−0.56, q 0.001).
  - In R2 it weakens from −0.38 to −0.23 (q 0.17), so part of R2's SON association is shared with the IOD.
  - In R1, DMI has its own partial association with rainfall: −0.43 (p 0.009, q 0.11 after correction).
- **R3 DJF:** the RONI association remains (partial r −0.40, q 0.037).
- **Headline equation (R3-SON):** adding a DMI term *raises* the 2014–2019 validation RMSE from 55.09 to 55.94 mm/month, so DMI did not help. The model was not re-selected.

## INTERPRETATION (qualified)
The main ENSO associations are not explained away by the IOD in this sample. R2 in SON is the exception, where ENSO and IOD effects can't be separated well. With n_eff ≈ 35–52 and correlated predictors, the partial correlations are imprecise.
