import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beyond_prediction import imerg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "interim"


def test_box_slices_match_cell_centres():
    lon_s, lat_s = imerg.INDONESIA_BOX.slices()
    lon = imerg.LON0 + imerg.STEP * np.arange(imerg.NLON)
    lat = imerg.LAT0 + imerg.STEP * np.arange(imerg.NLAT)
    assert np.isclose(lon[lon_s][0], 94.05) and np.isclose(lon[lon_s][-1], 141.95)
    assert np.isclose(lat[lat_s][0], -11.95) and np.isclose(lat[lat_s][-1], 6.95)
    assert (lon_s.stop - lon_s.start, lat_s.stop - lat_s.start) == (480, 190)


def test_box_outside_grid_rejected():
    with pytest.raises(ValueError):
        imerg.Box(170, 190, 0, 1).slices()


def test_fill_and_negative_become_nan():
    a = imerg.mask_fill(np.array([0.2, -9999.9, -0.1, 0.0]))
    assert np.isnan(a[1]) and np.isnan(a[2]) and a[0] == np.float32(0.2) and a[3] == 0


def test_rate_conversion_uses_actual_hours():
    assert imerg.rate_to_monthly_total(np.float32(1.0), 24 * 29) == pytest.approx(696)
    with pytest.raises(ValueError):
        imerg.rate_to_monthly_total(np.float32(1.0), 24 * 40)


def test_grid_check_rejects_shifted_grid():
    lon = imerg.LON0 + imerg.STEP * np.arange(imerg.NLON)
    lat = imerg.LAT0 + imerg.STEP * np.arange(imerg.NLAT)
    imerg.check_grid(lon, lat)
    with pytest.raises(ValueError):
        imerg.check_grid(lon + 0.05, lat)


@pytest.mark.skipif(not (CACHE / "imerg_box").exists(), reason="no cached IMERG subsets")
def test_cached_subsets_are_consistent():
    m = np.load(CACHE / "imerg_landsea_box.npz")
    for f in sorted((CACHE / "imerg_box").glob("[0-9]*.npz")):
        d = np.load(f)
        assert d["precip_rate_mm_hr"].shape == (190, 480)
        assert np.allclose(d["lon"], m["lon"], atol=1e-4)
        assert np.allclose(d["lat"], m["lat"], atol=1e-4)
        assert 24 * 28 <= float(d["hours"]) <= 24 * 31
        p = d["precip_rate_mm_hr"]
        assert np.nanmin(p) >= 0 and np.nanmax(p) < 10  # monthly mean rate, mm/hr
