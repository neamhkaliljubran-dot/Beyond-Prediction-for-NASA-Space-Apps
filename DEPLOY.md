# Deploying the live demo

The app (`app.py`) reads only cached files committed in this repository (`data/processed`,
`data/provenance`, `data/results`, `docs/figures`). It never downloads NASA or NOAA data while it runs.
`requirements.txt` lists only the 4 runtime packages (pinned to the tested versions). The full
data pipeline uses `requirements-pipeline.txt`.

## Streamlit Community Cloud (public URL)
1. Go to https://share.streamlit.io and sign in with the GitHub account that can see this repository.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `neamhkaliljubran-dot/Beyond-Prediction-for-NASA-Space-Apps`
   - Branch: `claude/laughing-knuth-deo1i4` (or `main` after the branch is merged)
   - Main file path: `app.py`
   - Optional App URL: e.g. `beyond-prediction`
4. **Advanced settings** → Python version **3.13** (the tested version). No secrets are needed.
5. Click **Deploy**. The first build takes a few minutes; the URL looks like `https://<name>.streamlit.app`.

If the repository is private, Streamlit asks for permission to read private repositories during
sign-in. The deployed app itself is public unless you restrict viewers in the app settings.

## Local fallback (for example, if the venue Wi-Fi fails)
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Then open http://localhost:8501 and press **Run Analysis**.

## Pre-demo check
```bash
pip install -r requirements-pipeline.txt
python -m pytest -q
```
