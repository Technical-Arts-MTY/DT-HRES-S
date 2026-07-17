"""
wind_model.py — Small wind turbine physical model
==================================================
Power-curve based simulation for small (<10 kW) wind turbines suitable
for off-grid community systems. Includes air-density correction for
altitude (important for high-elevation sites like Mexico City) and
wind-speed extrapolation from 10 m measurement height to hub height.

References
----------
- Manwell, McGowan, Rogers, "Wind Energy Explained" (2nd ed.)
- IEC 61400-12-1 — Power performance measurement of electricity-producing wind turbines
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass

R_AIR = 287.05      # J/(kg·K), specific gas constant of dry air
RHO_STD = 1.225     # kg/m³, standard air density at sea level, 15 °C
G_GRAVITY = 9.80665
LAPSE_RATE = 0.0065  # K/m, standard atmosphere


@dataclass
class WindTurbine:
    """Small wind turbine specification.

    Default values approximate a typical 3 kW community wind turbine.
    """
    name: str = "Generic 3 kW"
    rated_power_W: float = 3000.0
    rotor_diameter_m: float = 4.0
    hub_height_m: float = 12.0
    cut_in_ms: float = 2.5
    rated_ms: float = 11.0
    cut_out_ms: float = 25.0
    # Power curve: list of (wind_speed_ms, power_W) tuples
    # Default = simplified cubic up to rated, flat after
    power_curve: list[tuple[float, float]] | None = None

    def default_curve(self) -> np.ndarray:
        """Synthetic curve if none provided: cubic between cut-in and rated."""
        v = np.arange(0, 31, 0.5)
        p = np.zeros_like(v)
        mask_cubic = (v >= self.cut_in_ms) & (v < self.rated_ms)
        p[mask_cubic] = self.rated_power_W * (
            (v[mask_cubic] - self.cut_in_ms)
            / (self.rated_ms - self.cut_in_ms)
        ) ** 3
        mask_rated = (v >= self.rated_ms) & (v <= self.cut_out_ms)
        p[mask_rated] = self.rated_power_W
        return np.column_stack([v, p])


def air_density(t_amb_C: np.ndarray, elevation_m: float,
                p_atm_atm: np.ndarray | None = None) -> np.ndarray:
    """Air density (kg/m³).

    If measured atmospheric pressure is available, uses ideal-gas law.
    Otherwise, applies ISA pressure altitude correction.
    """
    t_amb_K = t_amb_C + 273.15
    if p_atm_atm is not None:
        p_Pa = p_atm_atm * 101325.0
    else:
        # International Standard Atmosphere pressure at elevation
        t0_K = 288.15  # 15 °C reference
        p_Pa = 101325.0 * (1 - LAPSE_RATE * elevation_m / t0_K) ** 5.255
    return p_Pa / (R_AIR * t_amb_K)


def extrapolate_wind(v_measured_ms: np.ndarray,
                     h_measured_m: float = 10.0,
                     h_hub_m: float = 12.0,
                     alpha: float = 0.143) -> np.ndarray:
    """Wind shear power law (Hellmann exponent).

    v(h) = v_ref × (h / h_ref)^α

    α = 1/7 ≈ 0.143 is the open-terrain default.
    Use 0.20-0.30 for rougher terrain (trees, buildings).
    """
    if h_measured_m == h_hub_m:
        return v_measured_ms
    return v_measured_ms * (h_hub_m / h_measured_m) ** alpha


def power_from_curve(v_ms: np.ndarray, turbine: WindTurbine,
                     rho_correction: np.ndarray | None = None) -> np.ndarray:
    """Interpolate the power curve and apply optional density correction.

    Density correction follows IEC 61400-12-1 simplified formula:
        v_eq = v × (ρ / ρ_std)^(1/3)
    """
    curve = np.array(turbine.power_curve) if turbine.power_curve else turbine.default_curve()

    if rho_correction is not None:
        v_eq = v_ms * (rho_correction / RHO_STD) ** (1 / 3)
    else:
        v_eq = v_ms

    # Vectorized linear interpolation, zero outside [cut-in, cut-out]
    p = np.interp(v_eq, curve[:, 0], curve[:, 1], left=0, right=0)
    # Force cut-out
    p = np.where(v_eq > turbine.cut_out_ms, 0.0, p)
    return p


def simulate(df: pd.DataFrame, turbine: WindTurbine,
             elevation_m: float | None = None,
             measurement_height_m: float = 10.0) -> pd.DataFrame:
    """Run a full annual hourly wind simulation on a TMY DataFrame.

    Parameters
    ----------
    df : DataFrame from data_loader.load_city()
    turbine : WindTurbine instance
    elevation_m : site elevation (default = from df)
    measurement_height_m : anemometer height in the TMY data (typ. 10 m)

    Returns
    -------
    DataFrame with added columns:
        air_density_kgm3, v_hub_ms, p_wind_W
    """
    if elevation_m is None:
        elevation_m = df['elevation_m'].iloc[0]

    out = df.copy()
    out['air_density_kgm3'] = air_density(
        out['dry_bulb_C'].values, elevation_m, out['atm_pressure_atm'].values
    )
    out['v_hub_ms'] = extrapolate_wind(
        out['wind_speed_ms'].values, measurement_height_m, turbine.hub_height_m
    )
    out['p_wind_W'] = power_from_curve(
        out['v_hub_ms'].values, turbine, out['air_density_kgm3'].values
    )
    return out


if __name__ == '__main__':
    from data_loader import load_city
    df = load_city('Monterrey')
    turbine = WindTurbine(rated_power_W=3000, rotor_diameter_m=4.0, hub_height_m=12.0)
    out = simulate(df, turbine)
    annual_kWh = out['p_wind_W'].sum() / 1000
    cf = annual_kWh / (turbine.rated_power_W / 1000 * 8760)
    print(f"Wind turbine: {turbine.rated_power_W/1000:.1f} kW in Monterrey")
    print(f"Annual energy: {annual_kWh:.0f} kWh")
    print(f"Capacity factor: {cf:.1%}")
