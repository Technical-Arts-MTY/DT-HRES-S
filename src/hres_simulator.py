"""
hres_simulator.py — Integrated Hybrid Renewable Energy System engine
======================================================================
Combines PV + wind + battery + demand to produce a full year of
hourly system operation. This is the "physics-based twin" that the
ML model will learn to emulate.

Pipeline:
    TMY data  →  pv_model + wind_model  →  supply
              ↓
              + demand profile (synthetic or user-provided)
              ↓
              → battery_model dispatch
              ↓
              → KPIs (energy served, LPSP, capacity factors, ...)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field

from . import pv_model, wind_model, battery_model


@dataclass
class HRESConfig:
    """Full HRES system configuration."""
    pv: pv_model.PVSystem = field(default_factory=pv_model.PVSystem)
    wind: wind_model.WindTurbine = field(default_factory=wind_model.WindTurbine)
    battery: battery_model.Battery = field(default_factory=battery_model.Battery)
    has_pv: bool = True
    has_wind: bool = True
    has_battery: bool = True


# -----------------------------------------------------------------------------
# Synthetic demand profile (placeholder until Task 3.2 provides real load data)
# -----------------------------------------------------------------------------
def synthetic_community_load(df: pd.DataFrame,
                              peak_kW: float = 2.0,
                              base_kW: float = 0.2,
                              evening_peak_h: int = 19) -> np.ndarray:
    """Generate an approximate residential community demand profile.

    Characteristics:
      - Base load 24/7 (refrigeration, basic lighting)
      - Morning shoulder (6-9 h) for breakfast/preparation
      - Evening peak (18-22 h) for lighting/cooking/entertainment
      - Seasonal modulation (slightly higher in summer for fans)

    Until Task 1.1 KAP diagnostic delivers real demand data from Ixil,
    this provides a reasonable testbed.
    """
    hour = df['hour'].values
    month = df['month'].values

    # Daily shape (0-1)
    shape = np.full_like(hour, 0.1, dtype=float)
    # Morning shoulder
    morning = np.where((hour >= 6) & (hour <= 9), 0.5, 0)
    # Daytime baseline
    daytime = np.where((hour >= 10) & (hour <= 17), 0.3, 0)
    # Evening peak
    evening_curve = np.exp(-((hour - evening_peak_h) ** 2) / 8)
    shape = np.maximum.reduce([shape, morning, daytime, evening_curve])

    # Seasonal factor (slight summer increase)
    seasonal = 1 + 0.15 * np.sin(np.deg2rad((month - 6) * 30))

    p_demand_kW = base_kW + (peak_kW - base_kW) * shape * seasonal
    return p_demand_kW * 1000  # → W


# -----------------------------------------------------------------------------
# Main simulation entry point
# -----------------------------------------------------------------------------
def run(df: pd.DataFrame,
        config: HRESConfig,
        demand_W: np.ndarray | None = None) -> pd.DataFrame:
    """Run the integrated HRES simulation for one year.

    Parameters
    ----------
    df : DataFrame from data_loader.load_city()
    config : HRESConfig instance with PV, wind, battery specs
    demand_W : optional custom demand profile (W). If None, a synthetic
               community profile is generated.

    Returns
    -------
    DataFrame with all hourly variables:
        - Inputs: datetime, GHI, temperature, wind speed
        - PV: poa_Wm2, t_cell_C, p_pv_W
        - Wind: v_hub_ms, p_wind_W
        - Demand: p_demand_W
        - Battery: soc, p_charge_W, p_discharge_W
        - Balance: p_curtailed_W, p_unserved_W
    """
    out = df.copy()

    # --- PV ---
    if config.has_pv:
        pv_out = pv_model.simulate(out, config.pv)
        out['poa_Wm2'] = pv_out['poa_Wm2']
        out['t_cell_C'] = pv_out['t_cell_C']
        out['p_pv_W'] = pv_out['p_ac_W']
    else:
        out['p_pv_W'] = 0.0

    # --- Wind ---
    if config.has_wind:
        w_out = wind_model.simulate(out, config.wind)
        out['v_hub_ms'] = w_out['v_hub_ms']
        out['p_wind_W'] = w_out['p_wind_W']
    else:
        out['p_wind_W'] = 0.0

    # --- Supply & demand ---
    out['p_supply_W'] = out['p_pv_W'] + out['p_wind_W']
    out['p_demand_W'] = demand_W if demand_W is not None \
                       else synthetic_community_load(out)

    # --- Battery dispatch ---
    if config.has_battery:
        disp = battery_model.simulate_dispatch(
            out['p_supply_W'].values,
            out['p_demand_W'].values,
            config.battery,
        )
        for k, v in disp.items():
            out[k] = v
    else:
        net = out['p_supply_W'].values - out['p_demand_W'].values
        out['p_unserved_W'] = np.maximum(-net, 0)
        out['p_curtailed_W'] = np.maximum(net, 0)
        out['soc'] = np.nan

    return out


# -----------------------------------------------------------------------------
# KPI summary
# -----------------------------------------------------------------------------
def summarize(out: pd.DataFrame, config: HRESConfig) -> dict:
    """Compute headline KPIs from a simulation run."""
    rel = battery_model.reliability_metrics(
        out['p_demand_W'].values, out['p_unserved_W'].values
    )

    pv_kWp = config.pv.p_array_W / 1000 if config.has_pv else 0
    wind_kW = config.wind.rated_power_W / 1000 if config.has_wind else 0

    e_pv_kWh = out['p_pv_W'].sum() / 1000 if config.has_pv else 0
    e_wind_kWh = out['p_wind_W'].sum() / 1000 if config.has_wind else 0
    e_curtailed_kWh = out['p_curtailed_W'].sum() / 1000

    return {
        'pv_kWp': pv_kWp,
        'wind_kW': wind_kW,
        'battery_kWh': config.battery.capacity_kWh if config.has_battery else 0,
        'E_demand_kWh_yr': rel['energy_demand_kWh'],
        'E_pv_kWh_yr': e_pv_kWh,
        'E_wind_kWh_yr': e_wind_kWh,
        'E_curtailed_kWh_yr': e_curtailed_kWh,
        'E_unmet_kWh_yr': rel['energy_unmet_kWh'],
        'CF_pv': e_pv_kWh / (pv_kWp * 8760) if pv_kWp > 0 else 0,
        'CF_wind': e_wind_kWh / (wind_kW * 8760) if wind_kW > 0 else 0,
        'LPSP': rel['LPSP'],
        'LOLE_h': rel['LOLE_h'],
        'coverage_pct': rel['coverage'] * 100,
        'renewable_fraction': (e_pv_kWh + e_wind_kWh - e_curtailed_kWh)
                              / max(rel['energy_demand_kWh'], 1e-9),
    }
