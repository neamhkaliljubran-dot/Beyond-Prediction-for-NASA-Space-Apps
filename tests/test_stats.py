"""Unit tests on synthetic inputs (these are code checks, not scientific results)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beyond_prediction import stats as S  # noqa: E402

IDX = pd.date_range("1990-01-01", "2019-12-01", freq="MS")


def test_lag_convention_rain_follows_enso():
    rng = np.random.default_rng(0)
    e = pd.Series(rng.normal(size=IDX.size), IDX)
    rain = e.shift(2)                                   # rain(t) = enso(t-2)
    p = S.lagged_pairs(e, rain, list(range(1, 13)), lag=2, start="1991-01", end="2019-12")
    assert S.pearson(p.enso.to_numpy(), p.rain.to_numpy()) == pytest.approx(1.0)
    assert (p.t_rain - p.t_enso).dt.days.between(59, 62).all()
    p0 = S.lagged_pairs(e, rain, list(range(1, 13)), lag=0, start="1991-01", end="2019-12")
    assert abs(S.pearson(p0.enso.to_numpy(), p0.rain.to_numpy())) < 0.2


def test_season_filter_and_season_year():
    e = pd.Series(np.arange(IDX.size, dtype=float), IDX)
    p = S.lagged_pairs(e, e, [12, 1, 2], 0, "2000-01", "2001-12")
    assert sorted(set(p.t_rain.dt.month)) == [1, 2, 12]
    sy = S.season_year(pd.DatetimeIndex(p.t_rain))
    assert sy[list(p.t_rain.dt.month).index(12)] == 2001


def test_anomalies_remove_calendar_cycle():
    x = pd.Series(100 + 50 * np.sin(2 * np.pi * IDX.month / 12) + np.random.default_rng(3).normal(size=IDX.size), IDX)
    a = S.anomalies(x, S.monthly_climatology(x))
    assert np.allclose(a.groupby(IDX.month)["anom_mm"].mean(), 0, atol=1e-9)
    assert np.allclose(a.groupby(IDX.month)["anom_std"].std(ddof=1), 1)


def test_effective_n_white_noise_and_persistent():
    t = IDX[:240]
    white = np.r_[1.0, np.zeros(24)]
    assert S.effective_n(t, white, white) == pytest.approx(240)
    ar = 0.9 ** np.arange(25)
    assert S.effective_n(t, ar, ar) < 60


def test_phase_surrogates_keep_spectrum():
    rng = np.random.default_rng(1)
    x = np.cumsum(rng.normal(size=256)) * 0.1
    s = S.phase_surrogates(x, 5, rng)
    assert np.allclose(np.abs(np.fft.rfft(s - x.mean(), axis=1)), np.abs(np.fft.rfft(x - x.mean())), atol=1e-8)
    assert not np.allclose(s[0], x)


def test_block_bootstrap_keeps_years_whole():
    years = np.repeat(np.arange(2000, 2010), 3)
    for rows in S.block_bootstrap_years(years, 20, 2, np.random.default_rng(2)):
        assert len(rows) == 30
        assert all(np.bincount(years[rows] - 2000, minlength=10) % 3 == 0)


def test_bh_and_holm_known_values():
    p = np.array([0.01, 0.04, 0.03, 0.5])
    assert np.allclose(S.benjamini_hochberg(p), [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.5])
    assert np.allclose(S.holm(p), [0.04, 0.09, 0.09, 0.5])
