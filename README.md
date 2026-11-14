# Beyond Prediction — NASA Space Apps 2026 (Team Hypatia)

An evidence-grounded hypothesis discovery prototype for the challenge
*Be An Earth System Trend Detective*. It analyses real observations of ENSO and
Indonesian rainfall to find how their relationships change across seasons and
time, and turns computed results into candidate, testable hypotheses.
G-NETS (Global Non-linear Earth Topology Systems) is a **proposed
investigational framework**, not an established theory.

## Status
| Component | State |
|---|---|
| NOAA CPC ONI + RONI (ERSSTv6) download, parsing, centre-month alignment | done (`data/processed/enso_monthly.csv`) |
| GPM IMERG V07B monthly: collection, coverage, units, access verified | done (`data/provenance/imerg_verification.json`) |
| IMERG Indonesia box subset pipeline (resumable), tested on 12 months | done (`scripts/fetch_imerg_subset.py`) |
| Full 1998–2025 IMERG subset → regional monthly rainfall | pending |
| Clusters, associations, equation discovery, network, hypotheses | pending |
| Streamlit app shell with workflow, outputs, evidence, provenance | done (`app.py`) |

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Rebuild data
```bash
python scripts/build_enso.py            # fetch ONI/RONI from NOAA CPC
python scripts/build_enso.py --offline  # rebuild from data/raw/enso
python scripts/verify_imerg.py --granule <one IMERG V07B HDF5 file>
```
IMERG downloads need a NASA Earthdata Login account that has authorised the
"NASA GESDISC DATA ARCHIVE" application.

See `IMPLEMENTATION_STATUS.md` for the detailed stage log.

## Data sources
- NOAA CPC ONI: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- NOAA CPC RONI: https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt
- NASA GPM IMERG Final monthly V07 (`GPM_3IMERGM`), DOI 10.5067/GPM/IMERG/3B-MONTH/07

## Tests
```bash
python -m pytest -q
```
