# 💪 3D — The Mind: What sensors/data feed the twin?

> **Methodology question**: What are the sensors (data) that our dynamic physical system can consume? Understand how used sensors work for interpreting properly the data that we get from them.

## 🧠 What "sensors" means for a HRES digital twin

A sensor is **any source of information the twin can consume**. For the DT-HRES-S there are three categories, in increasing order of "realness":

| Tier | Source | Latency | Cost | Accuracy | Status |
|---|---|---|---|---|---|
| **Tier 1** | TMY files (synthetic) | Static | Free | ±5-10% | ✅ In use today |
| **Tier 2** | Web APIs (NASA POWER, PVGIS) | Daily | Free | ±5-8% | 🟡 Ready, not deployed |
| **Tier 3** | Physical sensors (in Ixil) | Real-time | Expensive | ±1-3% | 🔴 Pending field deployment |

The brilliance of our architecture: **the twin doesn't care which tier feeds it**. The `src/sensors.py` module abstracts all three behind a common interface (`DataSource`). The simulator and ML models call `source.read()` without knowing if the data came from a CSV or a real piranometer.

## 🌡 The physical sensors we will eventually consume

When Ixil is instrumented (HRES 5), the system will have these sensors. Each one needs to be understood — not just connected — to interpret data correctly.

### Solar irradiance — Pyranometer

**What it measures:** Global Horizontal Irradiance (GHI) in W/m².
**How it works:** A black absorber surface heats up under sunlight; a thermopile measures the temperature difference relative to a shaded reference. The voltage is proportional to incident radiation.
**Reference instrument:** Kipp & Zonen CMP10 (secondary standard, ±2% accuracy)
**Cheap alternative:** Silicon-based sensor like Apogee SP-510 (±5%, ~$200 USD vs ~$2,500 for CMP10)
**Calibration considerations:**
- Must be perfectly horizontal (small tilt = large error)
- Must be cleaned regularly (soiling = -10% to -30% in dusty environments)
- Thermopile sensors have slow response (~5 sec to 95%); silicon are faster but less accurate

### Air temperature — Thermistor or RTD

**What it measures:** Ambient air temperature in °C.
**How it works:** Electrical resistance changes with temperature in a known curve.
**Critical:** Must be in a **radiation shield** (white louvered cover) or it reads up to 10°C too hot in sunlight.
**Common errors:**
- Mounted too close to PV panel → reads panel heat, not air
- Not ventilated → 5-10°C overestimate
- Direct sun exposure → up to 15°C overestimate

### Wind speed — Anemometer

**What it measures:** Wind speed (m/s) and optionally direction (degrees).
**Types:**
- **Cup anemometer** — three cups rotate; rotation rate ∝ wind speed. Reliable, cheap, low maintenance.
- **Ultrasonic anemometer** — measures travel time of ultrasonic pulses between transducers. No moving parts, more accurate at low speeds, more expensive.
**Critical:** **Mounting height matters.** TMY data is at 10 m; wind turbines are at ~12-15 m hub height. Use wind shear law (`α = 1/7` for open terrain) to extrapolate.
**Common errors:**
- Mounted too low → underestimate (turbines won't perform as predicted)
- Obstacles within 10× the height of the anemometer → turbulence biases readings

### Relative humidity — Capacitive sensor

**What it measures:** Relative humidity (%).
**How it works:** A polymer film absorbs water vapor, changing its dielectric constant; capacitance change is proportional to RH.
**Why it matters for HRES:** High humidity in tropical climates (Ixil/Campeche) accelerates PV connector corrosion and affects soiling rate.

### DC current and voltage — Hall effect / shunt sensors

**What it measures:** Power flow from PV array, into battery, and to inverter (P = V × I).
**How it works:** Hall effect sensors measure magnetic field around a current-carrying wire (non-invasive). Voltage measured directly across terminals.
**Critical:** Must be sampled at high frequency (≥1 Hz) to capture battery dynamics. TMY-style hourly data is too coarse for SoC accuracy.

### Battery state of charge — Coulomb counting + voltage

**The hardest sensor to interpret.** SoC cannot be measured directly; it must be **estimated** from current integration plus voltage correction.

**Standard approach:**
1. **Coulomb counting**: SoC(t) = SoC(t₀) + ∫(I × η) dt / Q_capacity
2. **Open-circuit voltage correction**: when battery rests, V_OC maps to SoC via a known curve
3. **Kalman filter**: combines both estimates with their uncertainties

**Why it's tricky:**
- Coulomb counting drifts (integration errors accumulate)
- Voltage method works only at rest (V varies with current under load)
- Temperature affects everything (cold reduces apparent capacity)

This is why HRES 6 (auto-correction) is critical: the twin's predicted SoC must be periodically reset against measured SoC, or it diverges.

## 🛠 The sensor abstraction layer

To handle all three tiers cleanly, `src/sensors.py` implements an abstract base class:

```python
class DataSource(ABC):
    @abstractmethod
    def read(self, timestamp: datetime) -> dict:
        """Returns dict with ghi_Wm2, dry_bulb_C, wind_speed_ms, etc."""

    @abstractmethod
    def metadata(self) -> dict:
        """Returns calibration info, uncertainty, sensor model, etc."""
```

Three implementations:

1. **`TMYFileSource`** — reads from `data/processed/*.csv`. Used today.
2. **`NASAPowerSource`** — fetches from https://power.larc.nasa.gov/api/ for any lat/lon worldwide. Free, no auth needed.
3. **`PiranometerSource`** — placeholder for real Modbus/serial sensor connection. Activates in HRES 5.

The simulator code is **identical** regardless of source:

```python
# Old way (rigid, tied to file):
df = pd.read_csv('campeche_tmy.csv')

# New way (modular, swappable):
source = TMYFileSource('campeche_tmy.csv', 'Campeche')   # today
# source = NASAPowerSource(lat=21.12, lon=-88.73)        # tomorrow
# source = PiranometerSource(device_id='IXIL_PV_01')     # someday
```

This is the **Modularity** principle of the Universe applied concretely.

## 📊 Uncertainty propagation

Every sensor has measurement uncertainty. The twin must **carry this uncertainty all the way to the final output**. This is the Universe principle of **Uncertainty**.

| Sensor | Typical uncertainty | Effect on PV prediction |
|---|---|---|
| Pyranometer (Class A) | ±2% | ±2% in P_pv |
| Pyranometer (Silicon) | ±5% | ±5% in P_pv |
| Thermistor (in shield) | ±0.2°C | ±0.1% in P_pv (small) |
| Anemometer (cup) | ±0.3 m/s + 1% | ±10% in P_wind (cubic dependency!) |

**Wind sensors are the bottleneck.** Because P_wind ∝ v³, a 5% error in v becomes a 15% error in P_wind. This is why wind sizing is harder than solar sizing — and why a piranometer-only deployment (no anemometer) is acceptable for solar-only HRES.

The module `src/uncertainty.py` propagates these errors using:
- **First-order Taylor expansion** for analytical cases
- **Monte Carlo sampling** for ML predictions (bootstrap on training data)

## 🎯 What the team needs to do (3D dimension)

| Task | Who | When |
|---|---|---|
| Implement `TMYFileSource` (done) | Aaron | ✅ Complete |
| Implement `NASAPowerSource` | Samuel | Before April 2026 |
| Define sensor selection criteria for Ixil | Víctor + Samuel | Before field visit |
| Procure sensors (pyranometer + RTD + anemometer + V/I) | NGO partner | Pending budget |
| Implement `PiranometerSource` (Modbus/serial) | José Llashag | After hardware arrives |
| Calibration protocol document | Miguel | Before deployment |

---

🟡 **Status**: Abstraction in place (`src/sensors.py`). TMY tier complete. NASA POWER tier ready to implement. Physical tier awaiting field campaign.
