import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beyond_prediction import enso  # noqa: E402

ONI = """ SEAS  YR   TOTAL   ANOM
  NDJ 1999  24.00  -1.60
  DJF 2000  24.20  -1.70
  JFM 2000  24.90  -1.40
"""
RONI = """SEAS   YR  ANOM
NDJ  1999 -1.50
DJF  2000 -1.60
JFM  2000 -1.30
"""


def test_centre_month_alignment():
    df = enso.parse_cpc_index(ONI)
    # NDJ 1999 -> Dec 1999, DJF 2000 -> Jan 2000, JFM 2000 -> Feb 2000
    assert list(df["date"]) == list(pd.to_datetime(["1999-12-01", "2000-01-01", "2000-02-01"]))


def test_merge_keeps_both_indices():
    df = enso.build_monthly(ONI, RONI)
    assert list(df.columns) == ["date", "year", "season", "oni_total_degC",
                                "oni_anom_degC", "roni_anom_degC"]
    assert df["roni_anom_degC"].tolist() == [-1.5, -1.6, -1.3]


def test_gap_is_rejected():
    with pytest.raises(ValueError, match="Gaps"):
        enso.parse_cpc_index("SEAS YR ANOM\nDJF 2000 1.0\nFMA 2000 1.0\n")


def test_episode_rule_needs_five_seasons():
    s = pd.Series([0.6, 0.6, 0.6, 0.6, 0.1, 0.5, 0.7, 0.8, 0.9, 0.5, -0.2])
    assert enso.episode_flags(s).tolist() == [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0]
