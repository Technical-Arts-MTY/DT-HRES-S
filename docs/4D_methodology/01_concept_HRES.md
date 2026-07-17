# 🥚 1D — The Concept: What is HRES and what do we predict?

> **Feynman test**: If you can't explain it to a 3-year-old, you don't understand it yet.

## 👶 Explain it to a child

> Imagine a small town in the jungle with no electricity. We want to bring them light, refrigerators for vaccines, and computers for the school. But we can't run wires from the city — it's too far. So we build a tiny electricity factory **in the town itself**.
>
> The factory has three parts:
> - **Solar panels** that catch sunlight and turn it into electricity (but only during the day).
> - A **windmill** that catches wind (works day AND night, but only when there's wind).
> - A **battery** that stores extra electricity for later (like a piggy bank, but for energy).
>
> When the town uses electricity (lights, fridge), it comes from solar + windmill + battery, all mixed together. That's why it's called "**hybrid**".
>
> The hard question: how big should each piece be? Too small and there are blackouts. Too big and we waste money. Our job is to figure out the perfect size for each town.

## 🔬 Theory of the process

A **Hybrid Renewable Energy System (HRES)** is an electrical generation system that combines two or more renewable sources to supply a demand, typically in **off-grid** or weak-grid contexts. The "hybrid" name comes from mixing technologies whose weaknesses cancel each other:

| Source | Strength | Weakness | Complementarity |
|---|---|---|---|
| Solar PV | Predictable peak (noon) | Zero at night, drops with clouds | Wind often blows at night |
| Wind | Day and night | Unpredictable, cubic dependency on speed | Solar fills calm-windy gaps |
| Battery | Smooths everything | Expensive, finite cycles | Buffers both above |

The system also typically includes:
- **Inverter** — converts DC (from panels/battery) to AC (for household use)
- **Charge controller** — protects the battery from over/under-charging
- **Demand** — the load to supply (lights, refrigeration, pumps, etc.)

## 🎯 What we want to predict

The digital twin must answer two complementary questions:

### Operational question (now-casting)
> Given today's weather, **how much power is the system producing right now?**

This is what `src/hres_simulator.py` and `src/ml_models.py` answer. Inputs are hourly meteorological data, outputs are hourly power flows.

### Design question (sizing optimization)
> Given a community's expected demand and local climate, **what is the optimal size of each component?**

This is what the Colab interface (in development) will answer. The user inputs community parameters (houses, school, clinic, budget), the twin returns recommended PV kWp, wind kW, and battery kWh.

## 📐 The master equations

These are the equations our 1D theory must respect. The ML models are validated against these — if the ML predicts something physically impossible, we reject it.

### PV power output

```
P_pv = P_nominal × (POA / 1000) × [1 + γ × (T_cell − 25°C)] × η_inverter × derate
```

| Symbol | Meaning | Typical value |
|---|---|---|
| P_pv | AC power output | predicted (W) |
| P_nominal | Nameplate panel power | 300-500 W |
| POA | Plane-of-array irradiance | 0-1100 W/m² |
| γ | Temperature coefficient | -0.35 to -0.45 %/°C |
| T_cell | Cell temperature | T_ambient + 25-40°C at peak sun |
| η_inverter | Inverter efficiency | 0.94-0.98 |
| derate | Soiling + cabling + mismatch | 0.80-0.90 |

**Where this lives in code:** `src/pv_model.py`, function `pv_dc_power()` and `pv_ac_power()`.

### Wind power output

```
P_wind ∝ ½ × ρ × A × v³ × Cp     (Betz law derivative)
```

But in practice we use the **manufacturer's power curve** (measured in a wind tunnel) and interpolate.

| Symbol | Meaning | Typical value |
|---|---|---|
| ρ | Air density | 1.0-1.25 kg/m³ |
| A | Rotor swept area | π × (D/2)² |
| v | Wind speed at hub height | 0-25 m/s |
| Cp | Power coefficient | ≤ 0.59 (Betz limit) |

**Where this lives in code:** `src/wind_model.py`, function `power_from_curve()`.

### Battery state of charge

```
SoC(t+1) = SoC(t) + [(P_charge × η_charge) − (P_discharge / η_discharge)] × Δt / E_max
```

Subject to physical constraints:
- 0.20 ≤ SoC ≤ 0.95 (preserves battery life)
- |P_charge|, |P_discharge| ≤ rated power

**Where this lives in code:** `src/battery_model.py`, function `simulate_dispatch()`.

### Energy balance (the central HRES equation)

At every time step:

```
P_pv + P_wind + P_battery_discharge = P_demand + P_battery_charge + P_curtailed + P_unmet
```

The dispatch algorithm (greedy by default) decides:
- If supply > demand: excess goes to battery; if battery full → curtailed
- If supply < demand: deficit comes from battery; if battery empty → unmet

**Where this lives in code:** `src/hres_simulator.py`, function `run()`.

## 🤔 What parts of the future do we want to predict?

The proper digital twin (HRES 7) eventually predicts:

| Horizon | Quantity | Use |
|---|---|---|
| Now | Current power output | Real-time monitoring |
| Next 24h | Tomorrow's generation curve | Optimal dispatch planning |
| Next year | Annual energy yield | System sizing |
| 10-25 years | Long-term degradation | Replacement planning |

**Today (v0.2.0)** we cover only the "now" and "annual" horizons via the simulator. **Next-day forecasting** requires real-time weather forecasts and is part of HRES 7.

## 📚 References for further reading

- Duffie, J. A. & Beckman, W. A. (2013). *Solar Engineering of Thermal Processes* (4th ed.). Wiley.
- Manwell, J. F., McGowan, J. G., & Rogers, A. L. (2009). *Wind Energy Explained* (2nd ed.). Wiley.
- Erdinc, O. & Uzunoglu, M. (2012). "Optimum design of hybrid renewable energy systems: Overview of different approaches." *Renewable and Sustainable Energy Reviews*, 16(3), 1412-1425.
- Bhattacharyya, S. C. (2013). "Mini-grid based off-grid electrification to enhance electricity access in developing countries: What policies may be required?" *Energy Policy*, 86, 71-83.

---

✅ **Status**: Complete. This document captures the 1D conceptual foundation. Any new team member should read this before touching code.
