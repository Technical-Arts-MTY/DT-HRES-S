# 🪐 The Universe Principles

> *"The Universe where our twin lives in: Modularity, Telemetry, Tracking, APIs, Uncertainty. This, as not necessary, are a good practice for our digital twin."*
> — Technical Arts methodology

Beyond the 4 dimensions of the model itself, every healthy digital twin must respect 5 transversal principles. These are **not optional** — they're what separates a research demo from a production-grade system.

---

## 1. 🧩 Modularity

> *"Our twin must divide its thoughts. The functions of the code must be separate and the function of one part must not depend on others."*

### Why it matters

A digital twin lives for years. Components get swapped (today TMY file, tomorrow real sensor). Team members rotate (Samuel graduates, someone else takes Data). If everything is tangled, every change breaks everything else.

### How DT-HRES-S implements it

**Each `src/*.py` module has a single responsibility:**

| Module | Single responsibility |
|---|---|
| `data_loader.py` | Read processed data, expose to other modules |
| `pv_model.py` | Compute PV power from weather (physics) |
| `wind_model.py` | Compute wind power from weather (physics) |
| `battery_model.py` | Battery state and dispatch (physics) |
| `hres_simulator.py` | Integrate all components (orchestration only) |
| `ml_models.py` | Train and evaluate ML (no physics, no I/O) |
| `sensors.py` | Abstract data sources (no simulation logic) |
| `telemetry.py` | Logging and monitoring (no business logic) |
| `auto_correction.py` | Detect drift and retrain (no inference logic) |
| `uncertainty.py` | Propagate errors (no model logic) |

**Test for modularity**: can I delete one file and still understand the rest? Yes, because each is self-contained. ✅

### Where we could improve

- `hres_simulator.py` knows too much about other modules. Consider an event-driven architecture for v0.3.
- Configuration is hardcoded in some places. Should move to YAML files.

---

## 2. 📡 Telemetry

> *"Our twin must be capable of receiving instructions from outside. Our twin must be obtaining data from a physical system continuously."*

### Why it matters

A static twin is useless. The whole point of a "twin" (vs. a "model") is that it **stays in sync with reality**. That requires a continuous stream of data flowing in.

### How DT-HRES-S implements it

**Today (v0.2.0)**: Telemetry is logged via `src/telemetry.py`, which provides:

```python
from src.telemetry import TelemetryLogger

logger = TelemetryLogger("ixil_session_001")
logger.log_prediction(
    timestamp=datetime.now(),
    features={'ghi_Wm2': 850, 'T_amb_C': 32, ...},
    prediction=3250.0,
    model_version='rf_v1',
    uncertainty_pct=5.4,
)
```

This writes to a structured log file (JSONL format) that can be:
- Replayed for debugging
- Aggregated for analytics
- Fed back into `auto_correction.py` for drift detection

**Tomorrow (HRES 5)**: When sensors are deployed, telemetry becomes a real stream:
- Sensors push to MQTT broker
- Twin subscribes and updates predictions in real-time
- Latency target: < 5 minutes from measurement to twin state

### Where we could improve

- Currently file-based logging only. A real deployment needs cloud database (InfluxDB / TimescaleDB).
- No streaming yet. Need MQTT or Kafka integration in HRES 5.

---

## 3. 📍 Tracking

> *"Our twin must be capable of knowing where and when something happened to it. The structure must respond when data enter for certain way, with what sensor, and what calibration."*

### Why it matters

If your twin says "the PV produces 3 kW", that statement is only meaningful if you also know:
- **When** was this measured/predicted? (timestamp)
- **Where** is the system? (location, system ID)
- **From what sensor**? (which pyranometer, what calibration date)
- **With what uncertainty**? (±5% or ±20%?)

Without tracking, the data is unreliable for decisions.

### How DT-HRES-S implements it

**Every data record carries metadata.** The `DataSource.metadata()` method returns:

```python
{
    'source_type': 'TMY_file',
    'city': 'Campeche',
    'uncertainty_ghi_pct': 5.0,
    'calibration_date': 'N/A — synthetic',
    'sensor_model': 'N/A',
    'timestamp_read': '2026-03-15T14:30:22Z',
}
```

When real sensors come online, this expands to:

```python
{
    'source_type': 'physical_sensor',
    'device_id': 'IXIL_PYRANO_01',
    'sensor_model': 'Kipp & Zonen CMP10',
    'uncertainty_ghi_pct': 2.0,
    'calibration_date': '2026-01-15',
    'next_calibration_due': '2027-01-15',
    'mounting_tilt_deg': 0.0,
    'mounting_azimuth_deg': 'N/A',
    'last_cleaning': '2026-03-10',
    'firmware_version': '2.3.1',
    'timestamp_read': '2026-03-15T14:30:22Z',
}
```

Every prediction in `telemetry.py` is tagged with this metadata. **Provenance is preserved end-to-end.**

### Where we could improve

- Add sensor health monitoring (battery level, signal strength, drift over time).
- Auto-detect uncalibrated sensors (e.g., flag if calibration overdue).

---

## 4. 🔌 APIs

> *"Our twin has its own tools for communicating with others that don't speak its idiom. The API must serve for communicating with other software as MATLAB, python, databases."*

### Why it matters

The twin shouldn't be locked inside a single Jupyter notebook. Other systems need to query it:
- A web dashboard for community members
- A MATLAB model used by NGO engineers
- A SCADA system monitoring the actual installation
- A mobile app for technicians

All of these speak different languages. The twin must speak a **universal protocol**: HTTP/REST with JSON.

### How DT-HRES-S implements it

**Status: 🔴 Pending.** The REST API is scheduled for v0.3.

**Planned architecture** (in `src/api.py`):

```python
from fastapi import FastAPI
from pydantic import BaseModel
from src.ml_models import load_model

app = FastAPI(title="DT-HRES-S API", version="0.3.0")

class WeatherInput(BaseModel):
    ghi_Wm2: float
    dry_bulb_C: float
    wind_speed_ms: float
    hour: int
    month: int
    latitude: float
    longitude: float

class PowerPrediction(BaseModel):
    p_pv_W: float
    p_wind_W: float
    uncertainty_pct: float
    model_version: str
    timestamp: str

@app.post("/predict", response_model=PowerPrediction)
def predict(weather: WeatherInput):
    model = load_model('results/models/rf_v1.pkl')
    prediction = model.predict_single(weather.dict())
    return prediction
```

**Once deployed**, any tool can query:

```bash
curl -X POST https://dt-hres-s.example.org/predict \
  -H "Content-Type: application/json" \
  -d '{"ghi_Wm2": 850, "dry_bulb_C": 32, "wind_speed_ms": 5.5, ...}'
```

And get:
```json
{"p_pv_W": 3247.5, "p_wind_W": 1820.3, "uncertainty_pct": 5.4, ...}
```

### Where we could improve

- Add WebSocket endpoint for real-time streaming.
- Add OpenAPI / Swagger auto-documentation.
- Implement authentication (JWT) for production deployment.

---

## 5. ❓ Uncertainty

> *"In real life, things aren't certain, and our twin must know that. Every time we get a result, we must include a margin of mistake."*

### Why it matters

A prediction without an uncertainty estimate is dangerous. If the twin says "you need 6 kWp", but the real answer is "6 kWp ± 3 kWp", the NGO might:
- Install 6 and have insufficient power (if reality was on the high end)
- Install 9 and waste money (if reality was on the low end)
- Make catastrophic decisions assuming false precision

### How DT-HRES-S implements it

**Status: 🟡 Module ready, integration pending.** See `src/uncertainty.py`.

**Three sources of uncertainty are tracked:**

#### 1. Input uncertainty (from sensors)
Propagated using first-order Taylor expansion:
```
σ_output² ≈ Σ (∂f/∂xᵢ)² × σ_xᵢ²
```

For PV power, the GHI uncertainty dominates: 5% GHI error → 5% P_pv error.

#### 2. Model uncertainty (from ML)
For Random Forest, computed via the spread of predictions across the 200 trees:
```python
predictions_per_tree = [tree.predict(x) for tree in forest.estimators_]
mean = np.mean(predictions_per_tree)
std = np.std(predictions_per_tree)
ci_95 = mean ± 1.96 × std
```

This is **free** for Random Forest — every prediction comes with a built-in confidence interval.

#### 3. Aleatoric uncertainty (irreducible noise)
Some variability is fundamental — even with perfect sensors and models, the wind isn't perfectly predictable. Captured via the residual variance in training data.

**Combined uncertainty** delivered to the user:
```python
total_uncertainty_pct = sqrt(input² + model² + aleatoric²)
```

### How it's communicated

For the community member:
> "You will have electricity 95% of the time, **probably between 92% and 98%**."

For the technical evaluator:
> "P_pv = 3247 W ± 175 W (95% CI), composed of 4.2% sensor uncertainty + 2.1% model uncertainty."

---

## 📊 Universe principle scorecard

| Principle | v0.2.0 Status | Target v0.3.0 |
|---|---|---|
| Modularity | 🟢 90% | 95% (config files) |
| Telemetry | 🟡 60% | 90% (cloud DB) |
| Tracking | 🟡 70% | 95% (full metadata) |
| APIs | 🔴 10% | 80% (REST API live) |
| Uncertainty | 🟡 50% | 90% (UI integrated) |

These are the dimensions Arturo Cruz (Integration & Reproducibility) owns. Progress on the Universe principles is what turns a research project into something useable.

---

📚 **Further reading:** "Beautiful Code" by Andy Oram & Greg Wilson (referenced in the original 4D methodology) — modular code design patterns.
