"""Statistics for Stage F: anomalies, lagged seasonal pairs, persistence-aware inference.

Conventions
- Monthly series are pandas Series indexed by month-start Timestamps.
- Lag L pairs rainfall at month t+L with ENSO centred on month t.
- Seasons are assigned by the rainfall (target) month.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------------------------------------------- anomalies
def monthly_climatology(x: pd.Series) -> pd.DataFrame:
    """Calendar-month mean and SD (ddof=1) of a monthly series."""
    g = x.groupby(x.index.month)
    return pd.DataFrame({"mean": g.mean(), "sd": g.std(ddof=1), "n": g.size()})


def anomalies(x: pd.Series, clim: pd.DataFrame) -> pd.DataFrame:
    """mm anomaly, standardised anomaly and percent anomaly w.r.t. ``clim``."""
    m = x.index.month
    mean = clim["mean"].reindex(m).to_numpy()
    sd = clim["sd"].reindex(m).to_numpy()
    a = x.to_numpy() - mean
    return pd.DataFrame({"anom_mm": a, "anom_std": a / sd, "anom_pct": 100 * a / mean},
                        index=x.index)


# ----------------------------------------------------------------- pairing
def lagged_pairs(enso: pd.Series, rain: pd.Series, months: list[int], lag: int,
                 start: str, end: str) -> pd.DataFrame:
    """Pairs (enso[t], rain[t+lag]) for rainfall months in [start, end] whose
    calendar month is in ``months``. Returns columns enso, rain, t_rain, t_enso."""
    t_rain = rain.loc[start:end].index
    t_rain = t_rain[t_rain.month.isin(months)]
    t_enso = t_rain - pd.DateOffset(months=lag)
    e = enso.reindex(t_enso).to_numpy()
    r = rain.reindex(t_rain).to_numpy()
    ok = ~(np.isnan(e) | np.isnan(r))
    return pd.DataFrame({"enso": e[ok], "rain": r[ok], "t_rain": t_rain[ok], "t_enso": t_enso[ok]})


def season_year(t: pd.DatetimeIndex) -> np.ndarray:
    """Season year: December belongs to the following year's DJF."""
    return np.where(t.month == 12, t.year + 1, t.year)


# ----------------------------------------------------------------- effect sizes
def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    y = y - y.mean()
    return float((x @ y) / np.sqrt((x @ x) * (y @ y)))


def ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    return float((x @ (y - y.mean())) / (x @ x))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return pearson(pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy())


# ----------------------------------------------------------------- autocorrelation
def acf(x: np.ndarray, max_lag: int) -> np.ndarray:
    x = np.asarray(x, dtype=float) - np.nanmean(x)
    n = len(x)
    d = x @ x
    return np.array([1.0] + [float(x[:-k] @ x[k:]) / d for k in range(1, max_lag + 1)])


def effective_n(t_index: pd.DatetimeIndex, acf_x: np.ndarray, acf_y: np.ndarray) -> float:
    """n_eff for a correlation from irregularly spaced monthly pairs.

    Var(r) ~ (1/n^2) sum_ij rho_x(d_ij) rho_y(d_ij) under the null; d_ij is the
    separation in months between pairs (identical for x and y, since the lag is fixed).
    ACF values beyond the supplied length are taken as zero.
    """
    m = t_index.year.to_numpy() * 12 + t_index.month.to_numpy()
    d = np.abs(m[:, None] - m[None, :])
    L = min(len(acf_x), len(acf_y))
    prod = np.zeros(d.max() + 1)
    prod[:L] = acf_x[:L] * acf_y[:L]
    s = prod[d].sum()
    n = len(m)
    return float(min(n, n * n / s)) if s > 0 else float(n)


def t_test_p(r: float, n_eff: float) -> float:
    from scipy import stats

    df = max(n_eff - 2, 1.0)
    t = r * np.sqrt(df / max(1 - r * r, 1e-12))
    return float(2 * stats.t.sf(abs(t), df))


# ----------------------------------------------------------------- surrogates / bootstrap
def phase_surrogates(x: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Fourier phase-randomised surrogates preserving the power spectrum (and mean)."""
    x = np.asarray(x, dtype=float)
    mu = x.mean()
    f = np.fft.rfft(x - mu)
    ph = rng.uniform(0, 2 * np.pi, size=(n, f.size))
    ph[:, 0] = 0
    if x.size % 2 == 0:
        ph[:, -1] = 0                      # Nyquist term must stay real
    return np.fft.irfft(f * np.exp(1j * ph), n=x.size) + mu


def block_bootstrap_years(years: np.ndarray, n_boot: int, block: int,
                          rng: np.random.Generator) -> list[np.ndarray]:
    """Moving-block bootstrap over distinct season-years. Returns row-index arrays."""
    uy = np.unique(years)
    rows = {y: np.flatnonzero(years == y) for y in uy}
    starts = np.arange(len(uy) - block + 1)
    nb = int(np.ceil(len(uy) / block))
    out = []
    for _ in range(n_boot):
        chosen = np.concatenate([uy[s:s + block] for s in rng.choice(starts, nb)])[:len(uy)]
        out.append(np.concatenate([rows[y] for y in chosen]))
    return out


# ----------------------------------------------------------------- multiple testing
def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    n = p.size
    order = np.argsort(p)
    q = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(q, 1.0)
    return out


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    n = p.size
    order = np.argsort(p)
    adj = np.maximum.accumulate(p[order] * (n - np.arange(n)))
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    return out
