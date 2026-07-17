"""
battery_model.py — Li-ion battery dynamics for HRES storage
============================================================
Simple but useful state-of-charge (SoC) model with charge/discharge
efficiency, depth-of-discharge constraints and capacity fade.

Designed to plug into the HRES dispatch simulator.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class Battery:
    """Lithium-ion battery bank specification.

    Defaults reflect a typical community-scale Li-ion pack.
    """
    capacity_kWh: float = 10.0
    p_max_charge_kW: float = 3.0
    p_max_discharge_kW: float = 3.0
    eta_charge: float = 0.95
    eta_discharge: float = 0.95
    soc_min: float = 0.20       # 20% DoD floor (preserves lifetime)
    soc_max: float = 0.95       # 95% upper limit
    soc_initial: float = 0.50
    self_discharge_per_h: float = 0.00002  # ~0.5% per day


def simulate_dispatch(p_supply_W: np.ndarray,
                      p_demand_W: np.ndarray,
                      battery: Battery,
                      dt_h: float = 1.0) -> dict[str, np.ndarray]:
    """Greedy dispatch: battery absorbs excess supply, covers deficit.

    Parameters
    ----------
    p_supply_W : net renewable generation per timestep (W)
    p_demand_W : load demand per timestep (W)
    battery : Battery specification
    dt_h : time step in hours (default 1)

    Returns
    -------
    dict with arrays:
        soc                : state of charge (0-1)
        p_charge_W         : power into battery (positive)
        p_discharge_W      : power out of battery (positive)
        p_curtailed_W      : excess renewable that could not be stored
        p_unserved_W       : load not met
        p_grid_W           : net grid exchange (negative = import)
    """
    n = len(p_supply_W)
    e_cap_Wh = battery.capacity_kWh * 1000
    soc = np.zeros(n)
    p_charge = np.zeros(n)
    p_discharge = np.zeros(n)
    p_curtailed = np.zeros(n)
    p_unserved = np.zeros(n)

    soc_prev = battery.soc_initial
    for t in range(n):
        # Self-discharge first
        soc_t = soc_prev * (1 - battery.self_discharge_per_h * dt_h)
        net_W = p_supply_W[t] - p_demand_W[t]

        if net_W >= 0:
            # Excess → charge battery
            p_in_W = min(net_W, battery.p_max_charge_kW * 1000)
            # Energy actually stored (after efficiency loss)
            e_stored_Wh = p_in_W * dt_h * battery.eta_charge
            headroom_Wh = (battery.soc_max - soc_t) * e_cap_Wh
            e_stored_Wh = min(e_stored_Wh, headroom_Wh)
            # Back out actual electrical power drawn from supply
            p_actual_W = e_stored_Wh / dt_h / max(battery.eta_charge, 1e-9)
            soc_t += e_stored_Wh / e_cap_Wh
            p_charge[t] = p_actual_W
            p_curtailed[t] = max(0, net_W - p_actual_W)
        else:
            # Deficit → discharge battery
            deficit_W = -net_W
            p_out_max_W = min(deficit_W, battery.p_max_discharge_kW * 1000)
            # Energy that battery needs to release (more than delivered due to losses)
            e_needed_Wh = p_out_max_W * dt_h / max(battery.eta_discharge, 1e-9)
            available_Wh = (soc_t - battery.soc_min) * e_cap_Wh
            e_released_Wh = min(e_needed_Wh, max(available_Wh, 0))
            p_delivered_W = e_released_Wh * battery.eta_discharge / dt_h
            soc_t -= e_released_Wh / e_cap_Wh
            p_discharge[t] = p_delivered_W
            p_unserved[t] = max(0, deficit_W - p_delivered_W)

        soc[t] = soc_t
        soc_prev = soc_t

    p_grid_W = -p_unserved + p_curtailed  # negative = import, positive = export

    return {
        'soc': soc,
        'p_charge_W': p_charge,
        'p_discharge_W': p_discharge,
        'p_curtailed_W': p_curtailed,
        'p_unserved_W': p_unserved,
        'p_grid_W': p_grid_W,
    }


def reliability_metrics(p_demand_W: np.ndarray,
                        p_unserved_W: np.ndarray) -> dict[str, float]:
    """Common reliability KPIs.

    Returns
    -------
    LPSP : Loss of Power Supply Probability (energy basis, 0-1)
    LOLE_h : Loss of Load Expectation (hours/year with unmet demand)
    coverage : fraction of demand met (1 - LPSP)
    """
    e_demand = p_demand_W.sum()
    e_unmet = p_unserved_W.sum()
    lpsp = e_unmet / e_demand if e_demand > 0 else 0
    lole_h = (p_unserved_W > 1).sum()  # hours with >1 W of unserved load
    return {
        'LPSP': lpsp,
        'LOLE_h': float(lole_h),
        'coverage': 1 - lpsp,
        'energy_demand_kWh': e_demand / 1000,
        'energy_unmet_kWh': e_unmet / 1000,
    }
