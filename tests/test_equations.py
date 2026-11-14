"""Code checks on synthetic inputs (not scientific results)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beyond_prediction import equations as E  # noqa: E402

IDX = pd.date_range("1990-01-01", "2019-12-01", freq="MS")


def _series(seed=0):
    rng = np.random.default_rng(seed)
    enso = pd.Series(np.convolve(rng.normal(size=IDX.size), np.ones(6) / 6, "same"), IDX)
    clim = 200 + 100 * np.cos(2 * np.pi * IDX.month / 12)
    return enso, clim


def test_linear_recovers_known_slope_and_lag():
    enso, clim = _series()
    x2 = enso.shift(2).fillna(0)
    x2 = x2 - x2.groupby(IDX.month).transform("mean")      # zero calendar-month mean
    rain = pd.Series(clim - 50 * x2.to_numpy(), IDX)       # rain(t) = clim - 50 * x(t-2)
    enso = x2.shift(-2)                                     # so enso(t-2) == x2(t)
    c = E.climatology(rain, IDX[-1])
    fr = E.frame(rain, enso, c, [9, 10, 11], 2, "1991-01", "2019-12")
    cand = next(x for x in E.candidates([9, 10, 11]) if x.key == "linear@lag2")
    beta = E.fit(fr, cand)
    assert beta[1] == pytest.approx(-50, abs=1e-6)


def test_climatology_uses_only_fit_period():
    rain = pd.Series(np.where(IDX.year < 2010, 100.0, 300.0), IDX)
    c = E.climatology(rain, pd.Timestamp("2009-12-01"))
    assert np.allclose(c.to_numpy(), 100.0)


def test_asymmetric_terms_partition_x():
    enso, clim = _series(1)
    rain = pd.Series(clim, IDX)
    fr = E.frame(rain, enso, E.climatology(rain, IDX[-1]), [6, 7, 8], 0, "1991-01", "2019-12")
    assert np.allclose(fr.x_pos + fr.x_neg, fr.x)
    assert (fr.x_pos >= 0).all() and (fr.x_neg <= 0).all()


def test_month_varying_terms_only_active_in_their_month():
    enso, clim = _series(2)
    rain = pd.Series(clim, IDX)
    fr = E.frame(rain, enso, E.climatology(rain, IDX[-1]), [12, 1, 2], 1, "1991-01", "2019-12")
    assert np.allclose(fr.x_m12 + fr.x_m1 + fr.x_m2, fr.x)
    assert (fr.loc[fr.month != 1, "x_m1"] == 0).all()


def test_every_candidate_has_units_for_every_coefficient():
    for c in E.candidates([9, 10, 11]):
        for n in E.coef_names(c):
            assert n in c.units, (c.key, n)
