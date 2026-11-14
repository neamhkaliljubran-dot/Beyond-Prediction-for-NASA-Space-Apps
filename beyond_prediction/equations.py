"""Stage H: small, interpretable, dimensionally consistent candidate equations.

Variables (target region r, target season s; t = rainfall month):
  y(t)      rainfall anomaly, mm/month = P(t) - C(month of t), where P is the
            area-weighted IMERG monthly total and C the calendar-month climatology
            estimated ONLY from the fit's training months.
  x_L(t)    RONI (degC) centred on month t-L (3-month mean over t-L-1..t-L+1).
  y(t-1)    previous month's rainfall anomaly (mm/month), same climatology.
  1[m]      indicator of calendar month m (dimensionless).

Every candidate is linear in its coefficients, so ordinary least squares fits it.
Coefficient units are listed per term so each term has units of mm/month.
Lags 0 and 1 use RONI windows that include month t or later (concurrent
"nowcast" associations); only lags >= 2 use ENSO information that would be
available before month t starts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Candidate:
    name: str
    lag: int | None
    formula: str
    terms: list[str] = field(default_factory=list)          # column names (no intercept)
    units: dict[str, str] = field(default_factory=dict)
    intercept: bool = True

    @property
    def k(self) -> int:
        return len(self.terms) + int(self.intercept)

    @property
    def key(self) -> str:
        return self.name if self.lag is None else f"{self.name}@lag{self.lag}"


def candidates(season_months: list[int]) -> list[Candidate]:
    c = [Candidate("climatology", None, "y = 0", [], {}, intercept=False),
         Candidate("persistence", None, "y = phi * y(t-1)", ["y_prev"],
                   {"phi": "dimensionless"}, intercept=False)]
    for L in range(4):
        x = "x"
        c += [
            Candidate("linear", L, f"y = a + b * x_{L}", [x],
                      {"a": "mm/month", "b": "mm/month per degC"}),
            Candidate("asymmetric", L, f"y = a + b_pos * max(x_{L}, 0) + b_neg * min(x_{L}, 0)",
                      ["x_pos", "x_neg"],
                      {"a": "mm/month", "b_pos": "mm/month per degC", "b_neg": "mm/month per degC"}),
            Candidate("quadratic", L, f"y = a + b1 * x_{L} + b2 * x_{L}^2", [x, "x_sq"],
                      {"a": "mm/month", "b1": "mm/month per degC", "b2": "mm/month per degC^2"}),
            Candidate("linear+persistence", L, f"y = a + b * x_{L} + phi * y(t-1)", [x, "y_prev"],
                      {"a": "mm/month", "b": "mm/month per degC", "phi": "dimensionless"}),
            Candidate("month-varying slope", L,
                      f"y = a + sum_m b_m * 1[m] * x_{L}  (m in {season_months})",
                      [f"x_m{m}" for m in season_months],
                      {"a": "mm/month", **{f"b_m{m}": "mm/month per degC" for m in season_months}}),
            Candidate("linear+tendency", L, f"y = a + b * x_{L} + c * (x_{L} - x_{L + 3})",
                      [x, "x_tend"],
                      {"a": "mm/month", "b": "mm/month per degC", "c": "mm/month per degC"}),
        ]
    return c


def climatology(rain: pd.Series, end: pd.Timestamp) -> pd.Series:
    """Calendar-month means from rain months <= end (fit-period only)."""
    r = rain.loc[:end]
    return r.groupby(r.index.month).mean()


def frame(rain: pd.Series, enso: pd.Series, clim: pd.Series, months: list[int], lag: int,
          start, end) -> pd.DataFrame:
    """Design frame for target months in [start, end] whose calendar month is in ``months``."""
    t = rain.loc[start:end].index
    t = t[t.month.isin(months)]
    anom = rain - clim.reindex(rain.index.month).to_numpy()
    x = enso.reindex(t - pd.DateOffset(months=lag)).to_numpy()
    x3 = enso.reindex(t - pd.DateOffset(months=lag + 3)).to_numpy()
    df = pd.DataFrame({"y": anom.reindex(t).to_numpy(),
                       "y_prev": anom.reindex(t - pd.DateOffset(months=1)).to_numpy(),
                       "x": x, "x_pos": np.maximum(x, 0), "x_neg": np.minimum(x, 0),
                       "x_sq": x * x, "x_tend": x - x3,
                       "month": t.month, "P": rain.reindex(t).to_numpy(),
                       "C": clim.reindex(t.month).to_numpy()}, index=t)
    for m in months:
        df[f"x_m{m}"] = np.where(df["month"] == m, df["x"], 0.0)
    return df


def design(df: pd.DataFrame, c: Candidate) -> np.ndarray:
    cols = [df[t].to_numpy() for t in c.terms]
    if c.intercept:
        cols = [np.ones(len(df))] + cols
    return np.column_stack(cols) if cols else np.zeros((len(df), 0))


def fit(df: pd.DataFrame, c: Candidate) -> np.ndarray:
    X = design(df, c)
    if X.shape[1] == 0:
        return np.zeros(0)
    beta, *_ = np.linalg.lstsq(X, df["y"].to_numpy(), rcond=None)
    return beta


def predict(df: pd.DataFrame, c: Candidate, beta: np.ndarray) -> np.ndarray:
    X = design(df, c)
    return X @ beta if X.shape[1] else np.zeros(len(df))


def coef_names(c: Candidate) -> list[str]:
    names = {"x": "b", "x_pos": "b_pos", "x_neg": "b_neg", "x_sq": "b2", "y_prev": "phi",
             "x_tend": "c"}
    if c.name == "quadratic":
        names["x"] = "b1"
    out = (["a"] if c.intercept else []) + [names.get(t, t.replace("x_m", "b_m")) for t in c.terms]
    return out
