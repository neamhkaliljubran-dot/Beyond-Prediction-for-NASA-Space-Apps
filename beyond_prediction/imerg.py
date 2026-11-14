"""GPM IMERG Final monthly V07 (GPM_3IMERGM): granule listing and box subsetting.

Verified facts this module relies on (see data/provenance/imerg_verification.json):
- Variable ``Grid/precipitation`` has dims (time, lon, lat) = (1, 3600, 1800),
  units mm/hr (monthly mean rate), fill value -9999.9.
- Grid cell centres: lon -179.95..179.95, lat -89.95..89.95, step 0.1 degree
  (longitude convention -180..180, so Indonesia needs no wrap-around).
- ``Grid/time_bnds`` gives the averaging period in seconds; its length is used
  for the mm/hr -> mm/month conversion instead of an assumed month length.

The land/sea mask is NASA GES DISC ``GPM_IMERG_LandSeaMask`` V2
(DOI 10.5067/6P5EM1HPR3VD), variable ``landseamask`` (lon, lat) on the same
grid, expressed as percent water (0 = all land, 100 = all water).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

COLLECTION_ID = "C2723754851-GES_DISC"
LSM_URL = ("https://data.gesdisc.earthdata.nasa.gov/data/AUXILIARY/"
           "GPM_IMERG_LandSeaMask.2/GPM_IMERG_LandSeaMask.2.nc4")
FILL = -9999.9
STEP = 0.1
LON0, LAT0 = -179.95, -89.95
NLON, NLAT = 3600, 1800


@dataclass(frozen=True)
class Box:
    """Inclusive bounds on grid-cell centres, in degrees."""
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    def slices(self) -> tuple[slice, slice]:
        """Return (lon_slice, lat_slice) indices into the global IMERG grid."""
        i0 = int(np.ceil((self.lon_min - LON0) / STEP - 1e-6))
        i1 = int(np.floor((self.lon_max - LON0) / STEP + 1e-6))
        j0 = int(np.ceil((self.lat_min - LAT0) / STEP - 1e-6))
        j1 = int(np.floor((self.lat_max - LAT0) / STEP + 1e-6))
        if not (0 <= i0 <= i1 < NLON and 0 <= j0 <= j1 < NLAT):
            raise ValueError(f"Box outside grid: {self}")
        return slice(i0, i1 + 1), slice(j0, j1 + 1)


# Analysis domain: a rectangle enclosing Indonesia (it also contains parts of
# Malaysia, Brunei, Timor-Leste, Papua New Guinea, Singapore, southern Philippines
# and ocean). Region definitions inside it are made later and documented separately.
INDONESIA_BOX = Box(lon_min=94.05, lon_max=141.95, lat_min=-11.95, lat_max=6.95)


def check_grid(lon: np.ndarray, lat: np.ndarray) -> None:
    """Fail loudly if a file's grid differs from the verified IMERG grid."""
    exp_lon = LON0 + STEP * np.arange(NLON)
    exp_lat = LAT0 + STEP * np.arange(NLAT)
    if lon.shape != exp_lon.shape or not np.allclose(lon, exp_lon, atol=1e-3):
        raise ValueError("Unexpected IMERG longitude grid")
    if lat.shape != exp_lat.shape or not np.allclose(lat, exp_lat, atol=1e-3):
        raise ValueError("Unexpected IMERG latitude grid")


def mask_fill(a: np.ndarray) -> np.ndarray:
    """Replace fill / negative values with NaN (float32 copy)."""
    a = np.asarray(a, dtype=np.float32).copy()
    a[(a <= FILL + 0.05) | (a < 0)] = np.nan
    return a


def rate_to_monthly_total(rate_mm_hr: np.ndarray, hours: float) -> np.ndarray:
    """Monthly mean rate (mm/hr) x hours in the averaging period -> mm/month."""
    if not 24 * 28 <= hours <= 24 * 31:
        raise ValueError(f"Implausible month length: {hours} h")
    return rate_mm_hr * np.float32(hours)


def read_granule_subset(path, box: Box = INDONESIA_BOX) -> dict:
    """Read a box from one IMERG monthly HDF5 granule. Arrays are (lat, lon)."""
    import h5py

    lon_s, lat_s = box.slices()
    with h5py.File(path, "r") as f:
        lon, lat = f["Grid/lon"][:], f["Grid/lat"][:]
        check_grid(lon, lat)
        var = f["Grid/precipitation"]
        units = var.attrs.get("units", b"")
        units = units.decode() if isinstance(units, bytes) else str(units)
        if units != "mm/hr":
            raise ValueError(f"Unexpected precipitation units: {units!r}")
        if var.attrs.get("DimensionNames", b"").decode() != "time,lon,lat":
            raise ValueError("Unexpected precipitation dimension order")
        precip = mask_fill(var[0, lon_s, lat_s].T)
        err = mask_fill(f["Grid/randomError"][0, lon_s, lat_s].T)
        tb = f["Grid/time_bnds"][0]
        hours = float(tb[1] - tb[0]) / 3600.0
        t0 = float(tb[0])
    start = np.datetime64("1980-01-06T00:00:00") + np.timedelta64(int(t0), "s")
    return {
        "lon": lon[lon_s].astype(np.float32), "lat": lat[lat_s].astype(np.float32),
        "precip_rate_mm_hr": precip, "random_error_mm_hr": err,
        "hours": hours, "period_start": str(start)[:10],
        "n_fill": int(np.isnan(precip).sum()),
    }


def read_landsea_subset(path, box: Box = INDONESIA_BOX) -> dict:
    """Read the IMERG land/sea mask (percent water) for the box, as (lat, lon)."""
    import h5py

    lon_s, lat_s = box.slices()
    with h5py.File(path, "r") as f:
        lon, lat = f["lon"][:], f["lat"][:]
        check_grid(lon, lat)
        water = np.asarray(f["landseamask"][lon_s, lat_s].T, dtype=np.float32)
    water[(water < 0) | (water > 100)] = np.nan
    return {"lon": lon[lon_s].astype(np.float32), "lat": lat[lat_s].astype(np.float32),
            "water_pct": water}
