"""
pv_model.py — Photovoltaic system physical model
==================================================
First-principles PV simulation used as the "physics anchor" for the
DT-HRES-S digital twin. Provides ground-truth labels for ML training
and serves as a validation reference for ML predictions.

Implements:
  - Solar geometry (zenith, azimuth, air mass)
  - Cell temperature (NOCT method)
  - DC power output (single-diode simplified)
  - Inverter conversion (simple efficiency curve)

References
----------
- Duffie & Beckman, "Solar Engineering of Thermal Processes" (4th ed.)
- King, D. L., "Photovoltaic Array Performance Model", Sandia SAND2004-3535
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field

# Standard Test Conditions
G_STC = 1000.0   # W/m²
T_STC = 25.0     # °C


@dataclass
class PVSystem:
    """Container for PV system specifications.

    Attributes
    ----------
    p_rated_W : nameplate DC power per panel (W)
    n_panels : number of panels in the array
    eta_inverter : DC→AC conversion efficiency (0-1)
    gamma_pmpp : temperature coefficient of P_mpp (%/°C, typically -0.35 to -0.45)
    noct_C : Nominal Operating Cell Temperature (°C, typically 43-48)
    derate : combined loss factor (soiling, wiring, mismatch) — typical 0.85
    tilt_deg : array tilt from horizontal
    azimuth_deg : array azimuth (180 = south in N hemisphere)
    """
    p_rated_W: float = 400.0
    n_panels: int = 10
    eta_inverter: float = 0.96
    gamma_pmpp: float = -0.0040
    noct_C: float = 45.0
    derate: float = 0.85
    tilt_deg: float = 20.0
    azimuth_deg: float = 180.0

    @property
    def p_array_W(self) -> float:
        return self.p_rated_W * self.n_panels


def solar_position(day_of_year: np.ndarray,
                   hour: np.ndarray,
                   latitude: float,
                   longitude: float,
                   tz_offset_h: float = -6) -> tuple[np.ndarray, np.ndarray]:
    """Compute solar zenith and azimuth angles.

    Returns
    -------
    zenith_deg, azimuth_deg : same shape as inputs
    """
    # Equation of time (minutes)
    B = np.deg2rad((day_of_year - 81) * (360 / 365))
    eot_min = 9.87 * np.sin(2 * B) - 7.53 * np.cos(B) - 1.5 * np.sin(B)

    # Solar time (hours)
    lstm = 15 * tz_offset_h  # local std time meridian
    time_correction = 4 * (longitude - lstm) + eot_min  # minutes
    solar_time_h = hour + time_correction / 60

    # Hour angle (degrees, 0 = solar noon, +15°/h afternoon)
    hra_deg = 15 * (solar_time_h - 12)

    # Declination
    decl_deg = 23.45 * np.sin(np.deg2rad(360 / 365 * (284 + day_of_year)))

    # Zenith angle
    lat_rad = np.deg2rad(latitude)
    decl_rad = np.deg2rad(decl_deg)
    hra_rad = np.deg2rad(hra_deg)
    cos_zenith = (np.sin(lat_rad) * np.sin(decl_rad)
                  + np.cos(lat_rad) * np.cos(decl_rad) * np.cos(hra_rad))
    cos_zenith = np.clip(cos_zenith, -1, 1)
    zenith_deg = np.rad2deg(np.arccos(cos_zenith))

    # Azimuth (relative to south, signed)
    sin_az = np.cos(decl_rad) * np.sin(hra_rad) / np.sin(np.deg2rad(zenith_deg) + 1e-9)
    sin_az = np.clip(sin_az, -1, 1)
    azimuth_deg = 180 + np.rad2deg(np.arcsin(sin_az))

    return zenith_deg, azimuth_deg


def poa_irradiance(ghi: np.ndarray, dhi: np.ndarray, dni_proj: np.ndarray,
                   zenith_deg: np.ndarray, tilt_deg: float,
                   azimuth_surface_deg: float = 180.0,
                   solar_azimuth_deg: np.ndarray | None = None,
                   albedo: float = 0.2) -> np.ndarray:
    """Plane-of-Array (POA) irradiance using simple isotropic sky model.

    POA = beam_on_tilt + diffuse_isotropic + ground_reflected

    For more accuracy, swap for Hay-Davies or Perez model.
    """
    cos_zen = np.cos(np.deg2rad(zenith_deg))
    cos_zen = np.where(cos_zen > 0.01, cos_zen, np.nan)  # daytime only

    # DNI from horizontal projection
    dni = np.where(cos_zen > 0.01, dni_proj / cos_zen, 0.0)
    dni = np.clip(dni, 0, 1200)  # physical limit

    # Angle of incidence on tilted surface (simplified: assume aligned with solar azimuth)
    tilt_rad = np.deg2rad(tilt_deg)
    if solar_azimuth_deg is None:
        # Approximation: assume aligned (worst case underestimate at off-noon)
        cos_aoi = np.cos(tilt_rad) * cos_zen + np.sin(tilt_rad) * np.sqrt(1 - cos_zen**2)
    else:
        zen_rad = np.deg2rad(zenith_deg)
        surf_az_rad = np.deg2rad(azimuth_surface_deg)
        sun_az_rad = np.deg2rad(solar_azimuth_deg)
        cos_aoi = (np.cos(zen_rad) * np.cos(tilt_rad)
                   + np.sin(zen_rad) * np.sin(tilt_rad)
                   * np.cos(sun_az_rad - surf_az_rad))
    cos_aoi = np.clip(cos_aoi, 0, 1)

    # POA components
    poa_beam = dni * cos_aoi
    poa_diffuse = dhi * (1 + np.cos(tilt_rad)) / 2
    poa_ground = ghi * albedo * (1 - np.cos(tilt_rad)) / 2
    poa = np.nan_to_num(poa_beam + poa_diffuse + poa_ground, nan=0.0)
    return np.clip(poa, 0, 1500)


def cell_temperature(poa_Wm2: np.ndarray, t_ambient_C: np.ndarray,
                     wind_speed_ms: np.ndarray, noct_C: float = 45.0) -> np.ndarray:
    """Cell temperature using NOCT method with wind correction.

    T_cell = T_amb + (NOCT - 20) / 800 × POA × wind_factor

    where wind_factor = 1 / (1 + 0.05·v) (very approximate)
    """
    wind_factor = 1 / (1 + 0.05 * np.maximum(wind_speed_ms, 0))
    return t_ambient_C + (noct_C - 20) / 800 * poa_Wm2 * wind_factor


def pv_dc_power(poa_Wm2: np.ndarray, t_cell_C: np.ndarray, system: PVSystem) -> np.ndarray:
    """DC power output of the PV array (W).

    P_dc = P_array × (POA / G_STC) × [1 + γ·(T_cell - T_STC)] × derate
    """
    p = (system.p_array_W
         * (poa_Wm2 / G_STC)
         * (1 + system.gamma_pmpp * (t_cell_C - T_STC))
         * system.derate)
    return np.clip(p, 0, system.p_array_W * 1.1)  # cap at 110% nameplate


def pv_ac_power(p_dc_W: np.ndarray, system: PVSystem) -> np.ndarray:
    """AC power after inverter (W)."""
    return p_dc_W * system.eta_inverter


def simulate(df: pd.DataFrame, system: PVSystem,
             latitude: float | None = None, longitude: float | None = None) -> pd.DataFrame:
    """Run a full year hourly PV simulation on a TMY DataFrame.

    Parameters
    ----------
    df : DataFrame from data_loader.load_city()
    system : PVSystem instance
    latitude, longitude : optional override (default = pulled from df)

    Returns
    -------
    DataFrame with new columns:
        zenith_deg, poa_Wm2, t_cell_C, p_dc_W, p_ac_W
    """
    if latitude is None:
        latitude = df['latitude'].iloc[0]
    if longitude is None:
        longitude = df['longitude'].iloc[0]

    out = df.copy()
    zenith, sun_az = solar_position(out['day_of_year'].values,
                                     out['hour'].values,
                                     latitude, longitude)
    out['zenith_deg'] = zenith
    out['solar_azimuth_deg'] = sun_az
    out['poa_Wm2'] = poa_irradiance(out['ghi_Wm2'].values,
                                     out['dhi_Wm2'].values,
                                     out['dni_proj_Wm2'].values,
                                     zenith, system.tilt_deg,
                                     system.azimuth_deg, sun_az)
    out['t_cell_C'] = cell_temperature(out['poa_Wm2'].values,
                                        out['dry_bulb_C'].values,
                                        out['wind_speed_ms'].values,
                                        system.noct_C)
    out['p_dc_W'] = pv_dc_power(out['poa_Wm2'].values, out['t_cell_C'].values, system)
    out['p_ac_W'] = pv_ac_power(out['p_dc_W'].values, system)
    return out


if __name__ == '__main__':
    # Quick smoke test
    from data_loader import load_city
    df = load_city('Monterrey')
    sys = PVSystem(p_rated_W=400, n_panels=10, tilt_deg=25)
    out = simulate(df, sys)
    annual_kWh = out['p_ac_W'].sum() / 1000
    capacity_factor = annual_kWh / (sys.p_array_W / 1000 * 8760)
    print(f"PV array: {sys.p_array_W/1000:.1f} kW in Monterrey")
    print(f"Annual energy: {annual_kWh:.0f} kWh")
    print(f"Capacity factor: {capacity_factor:.1%}")
    print(f"Specific yield: {annual_kWh / (sys.p_array_W/1000):.0f} kWh/kWp/yr")
