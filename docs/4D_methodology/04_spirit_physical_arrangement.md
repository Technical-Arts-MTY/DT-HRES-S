# 💪 4D — The Spirit: In what physical arrangement does it live?

> **Methodology question**: In what mechanical arrangement could it fit in? Understand the physical structure of the HRES and its energy structure for getting noise considerations in the final optimization.

## ⚡ The physical architecture of a community HRES

The DT-HRES-S targets **off-grid AC microgrids** for indigenous communities. The canonical architecture has 7 functional blocks:

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ☀ PV Array  →→→  Charge Controller  →→→                            │
│                                            DC                        │
│  🌪 Wind Turbine →→ Rectifier/CC  →→→     Bus  →→→  Inverter  →→→    │
│                                                                  ↓   │
│  🔋 Battery Bank  ←←  Charge Controller  ←←                     AC   │
│                                                                  ↓   │
│                              Bus  →→→ Distribution Panel  →→→  Loads│
│                                                                      │
│  ⛽ (Optional) Diesel Genset  →→→  (parallels with inverter)         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Block 1 — PV Array

**Physical components:**
- Solar panels (typically 350-500 Wp monocrystalline)
- Aluminum mounting structure (fixed tilt, ground-mount typical for community scale)
- DC cabling (12-14 AWG for 6 kWp systems)
- DC string fuses

**Critical design parameters captured by the model:**
- **Tilt angle** — for Ixil (lat 21°N), optimal annual tilt ≈ 20°. For winter optimization, +10°.
- **Azimuth** — south-facing (180°). Deviation of ±30° causes <5% loss.
- **String voltage** — must match charge controller input range.

**Physical losses not in idealized model (HRES 5 must capture):**
- **Soiling** — dust accumulation: -5% in rainy climate (Ixil), -15% in desert (San Ignacio)
- **Shading** — partial shade on one panel can disable the whole string
- **Mismatch** — panels of slightly different output limit each other
- **Module degradation** — 0.5% per year typical, accumulates to -10% at year 20

### Block 2 — Wind Turbine

**Physical components:**
- Rotor (typically 3-blade, 3-5 m diameter for community scale)
- Generator (permanent magnet, direct drive preferred for low maintenance)
- Tower (12-20 m, free-standing or guyed)
- Rectifier (turbine output is variable-frequency AC → DC for battery bus)
- Furling/braking mechanism (protects against overspeed)

**Critical considerations:**
- **Hub height matters cubically** for energy yield — taller tower = much more energy.
- **Site assessment** — local turbulence from buildings/trees can reduce output 30-50%.
- **Bird/bat impact** — community must accept presence of moving blades.
- **Noise** — small turbines produce 40-50 dBA at 50 m. Place away from sleeping areas.

### Block 3 — Charge controllers

**Two types:**
- **PWM (Pulse Width Modulation)** — cheap, simple, ~75% efficient. Wastes energy when PV voltage > battery voltage.
- **MPPT (Maximum Power Point Tracking)** — expensive, 95-98% efficient. Tracks the PV array's optimal operating point.

For community systems above 1 kWp, **MPPT is mandatory** — the efficiency gain pays for itself in 2-3 years.

### Block 4 — Battery Bank

**Chemistry choices:**

| Chemistry | $/kWh | Cycle life | Depth of discharge | Best for |
|---|---|---|---|---|
| Lead-acid (deep cycle) | $150 | 500-1000 | 50% | Tight budget, cool climate |
| **LFP (LiFePO₄)** | $400 | 3000-6000 | 80-90% | **Recommended for tropical** |
| NMC Li-ion | $450 | 1500-2500 | 80% | Less suitable (thermal runaway risk) |

**Why LFP for Ixil:**
- High ambient temperature accelerates lead-acid sulfation
- LFP tolerates 60°C operation
- 3-5× cycle life pays for higher upfront cost over 20-year project lifetime

**Battery sizing rule of thumb:** 1-2 days of autonomy. For 10 kWh/day demand → 15-25 kWh battery bank.

### Block 5 — Inverter

**Converts DC battery bus to AC household power (127 V / 60 Hz for Mexico).**

**Two architectures:**

- **String inverter** (centralized) — one big inverter handles all panels + battery. Simpler, cheaper, single point of failure.
- **Microinverters** (per-panel) — small inverter on each panel. More expensive, more resilient, better with partial shading.

For community HRES, **string inverter + battery hybrid inverter** (like Victron MultiPlus or Studer Xtender) is standard.

**Quality matters:**
- **Pure sine wave** required for sensitive electronics (medical, IT).
- **Surge capacity** important for motor loads (water pumps, refrigerators).
- **Total Harmonic Distortion** should be < 3% to avoid damaging sensitive equipment.

### Block 6 — Distribution

**From the inverter, AC power feeds:**
- Main distribution panel with breakers per circuit
- Underground or aerial cabling to each house/facility
- Smart meters (optional but recommended for billing/feedback)

**Voltage drop is the silent killer:** for long runs in low-voltage (127 V) systems, voltage drop > 5% causes flickering lights and appliance damage. Cable sizing must account for distances.

### Block 7 — Loads (the demand profile)

The **most underestimated dimension** of HRES design. The model is only as good as the assumed loads. Critical questions:

- How many houses? How many people per house?
- What appliances? (LED lights = 5W each, fridge = 100-200W avg, TV = 60W)
- What community facilities? (School computers, clinic refrigerator for vaccines, water pump)
- What are usage hours? (Morning prep, evening peak common in rural Mexico)
- Seasonal variation? (Higher in dry season for fans)

Until field data arrives, we use a **synthetic profile** in `src/hres_simulator.py` → `synthetic_community_load()`.

## 🔊 Noise considerations

Real systems have noise sources that idealized models ignore. The twin must eventually account for these:

| Source | Effect on output | Order of magnitude |
|---|---|---|
| Sensor measurement noise | Random variation in inputs | ±2-5% (well-calibrated) |
| Soiling | Systematic underestimate | -5% to -30% (cleanable) |
| Module degradation | Slow systematic decline | -0.5%/year |
| Inverter efficiency curve | Non-linear with load | -2-5% at part-load |
| Battery aging | Capacity fade | -20% over 10 years |
| Wind turbulence | Reduces effective wind | -10-30% at obstructed sites |
| Grid frequency drift | Inverter inefficiency | -1-2% |
| Cable I²R losses | Voltage drop | -3-8% (depends on cable runs) |

The ML model **eventually learns these patterns** from real data — that's the key advantage over pure physics simulation. With enough field data, the twin becomes more accurate than any first-principles model.

## 🗺 Site-specific considerations for Ixil

**What we know:**
- Tropical climate (Aw), high humidity, daily afternoon rain in summer
- Latitude 21°N → high sun year-round
- Limited wind (interior Yucatán, not coastal)
- Yucatán peninsula bedrock makes ground-mount foundations easy

**What we don't know yet** (pending field visit):
- Available land area (limits PV size)
- Existing electrical infrastructure (if any)
- Tree shading patterns through the year
- Community's specific equipment inventory
- Local labor availability for installation

This document should be **updated by Aaron + Víctor after the first site visit** with a real architecture diagram, photographs, and component selection matrix.

## 🎯 What the team needs to do (4D dimension)

| Task | Who | When |
|---|---|---|
| Document standard architecture (this file) | Aaron | ✅ Complete |
| Field visit to Ixil | All | Pending Task 1.1 |
| Update with Ixil-specific layout | Aaron + Víctor | After visit |
| Select specific component models | Víctor | After visit |
| Document electrical drawings | Carlos (Data & Design Engineering) | After Víctor |
| Voltage drop calculations for actual layout | Víctor | After visit |
| Integration with `hres_simulator.py` | Aaron | After all above |

---

🔴 **Status**: Generic architecture documented. Ixil-specific architecture pending field data.
