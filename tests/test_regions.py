import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beyond_prediction import regions as rg  # noqa: E402

shapely = pytest.importorskip("shapely")


def test_cell_fraction_half_covered_cell():
    geom = shapely.box(0.0, 0.0, 0.05, 0.1)          # left half of the cell centred at (0.05, 0.05)
    f = rg.cell_fraction(geom, np.array([0.05]), np.array([0.05]))
    assert f[0, 0] == pytest.approx(0.5)


def test_include_rule_needs_both_masks():
    frac = np.array([0.9, 0.9, 0.3])
    water = np.array([10.0, 80.0, 10.0])
    assert rg.include_mask(frac, water).tolist() == [True, False, False]


def test_standardized_cycle_is_shape_only():
    clim = np.array([np.arange(12.0), 10 * np.arange(12.0) + 100]).T  # (12, 2)
    z = rg.standardized_cycle(clim)
    assert np.allclose(z[0], z[1])
    assert np.allclose(z.mean(axis=1), 0) and np.allclose(z.std(axis=1), 1)


def test_area_weighted_mean_ignores_nan_and_reports_coverage():
    v, frac = rg.area_weighted_mean(np.array([1.0, np.nan, 3.0]), np.array([1.0, 1.0, 3.0]),
                                    np.array([True, True, True]))
    assert v == pytest.approx(2.5) and frac == pytest.approx(0.8)
