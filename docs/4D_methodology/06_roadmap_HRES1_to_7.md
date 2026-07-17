# 🗺 Roadmap — From HRES 1 to HRES 7

> The 4D Methodology defines a progressive journey for building a complete digital twin. Each stage builds on the previous. Skipping stages causes the project to collapse.

## 🥚 Stage HRES 1 — Theory ("The Concept")

**Question:** What is HRES and what equations describe it?

**Status:** ✅ **Complete**

**Deliverables:**
- [01_concept_HRES.md](01_concept_HRES.md) — full theoretical document
- `src/pv_model.py` — PV physics in code
- `src/wind_model.py` — wind physics in code
- `src/battery_model.py` — battery dynamics in code

**Owner:** Víctor Cardeña (Simulation Lead)

---

## 🥚 Stage HRES 2 — Optimization Body

**Question:** What do we optimize, and for whom?

**Status:** 🟡 **In progress**

**Deliverables:**
- [02_body_optimization.md](02_body_optimization.md) — done
- Interface sketch (mockup) — done
- `notebooks/12_community_interface.ipynb` with ipywidgets — **pending**
- LCOE calculation in `src/hres_simulator.py` — **pending**

**Owner:** Carlos Rodríguez Tenorio (Data & Design Engineering) + Aaron Cuevas

**Estimated completion:** End of April 2026

---

## 💪 Stage HRES 3 — Sensors / Mind

**Question:** What data does the twin consume? How do we interpret it?

**Status:** 🟡 **Abstraction in place, real sensors pending**

**Deliverables:**
- [03_mind_sensors.md](03_mind_sensors.md) — done
- `src/sensors.py` with `TMYFileSource` — done
- `NASAPowerSource` integration — **pending Task 3.2**
- `PiranometerSource` for real hardware — **pending field deployment**

**Owner:** Samuel Canul (Data Lead)

**Estimated completion:** NASA POWER tier by May 2026; physical sensors pending field campaign

---

## 💪 Stage HRES 4 — Digital Shadow (Synthetic Real-Time)

**Question:** Can we run a real-time simulation with synthetic data?

**Status:** ✅ **Complete (this is what v0.2.0 delivers)**

**Deliverables:**
- `src/hres_simulator.py` — complete integrated simulator
- `notebooks/11_digital_twin_prototype.ipynb` — runs end-to-end
- Tests pass (`tests/test_data_quality.py`) — 8/8 ✅

**Owner:** Aaron Cuevas (Technical Lead) + Víctor Cardeña

**Notes:** This is where we are TODAY. We can simulate any HRES configuration for any of the 4 cities, with full hourly resolution for a year, in ~2 seconds.

---

## 💪 Stage 4D — Physical Arrangement / Spirit

**Question:** What does the real physical system look like in Ixil?

**Status:** 🔴 **Awaiting field data**

**Deliverables:**
- [04_spirit_physical_arrangement.md](04_spirit_physical_arrangement.md) — generic done
- Ixil-specific architecture diagram — **pending field visit**
- Specific component selection (panel model, turbine model, etc.) — **pending**
- Electrical drawings — **pending**

**Owner:** Aaron + Víctor + Carlos (after field visit)

**Blockers:** Task 1.1 (KAP diagnostic in Ixil) must happen first.

**Estimated completion:** After June 2026 field campaign.

---

## 🧠 Stage HRES 5 — Pipeline Replacement (Real Data)

**Question:** Can we replace synthetic data with real measurements?

**Status:** 🔴 **Pending Ixil field campaign + sensor deployment**

**Deliverables:**
- Ixil TMY data integrated (`data/processed/ixil_tmy.csv`)
- Real demand profile from Ixil (`data/processed/ixil_demand.csv`)
- Physical sensor data streaming (when deployed)
- ML re-trained including Ixil data

**Owner:** Samuel + José Llashag + field team

**Blockers:**
- Field visit to Ixil
- Sensor procurement (~$5,000 USD for minimal sensor package)
- Local installation partner

**Estimated completion:** Probably Q3-Q4 2026

---

## 👻 Stage HRES 6 — Self-Correction

**Question:** Can the twin detect when its predictions diverge from reality and self-correct?

**Status:** 🟡 **Scaffold in place**

**Deliverables:**
- `src/auto_correction.py` — base class implemented
- `AutoCorrector.check_drift()` — basic threshold detection ✅
- Automatic retraining trigger — **pending**
- Quality alerting (email/Slack when drift detected) — **pending**

**Owner:** Regina Muñoz (ML & Validation Lead) + José Llashag (ML Systems & Deployment)

**Notes:** This stage **only matters once HRES 5 is live** (need real data to detect drift against). Can be designed in advance but not validated.

**Estimated completion:** Q4 2026 if HRES 5 lands on schedule.

---

## 👻 Stage HRES 7 — ML predicts the future

**Question:** Can the twin **forecast** future states (not just now-cast)?

**Status:** 🟡 **Now-casting works; true forecasting pending**

**What's working today:**
- The 4 ML models (DT, RF, SVM, NN) predict instantaneous power given instantaneous weather. This is **now-casting**.
- Cross-validation across cities ✅

**What's missing for true forecasting:**
- **Time-series features** — using past 24/48/72 hours of weather as input
- **Weather forecast integration** — pulling tomorrow's weather from NOAA/CONAGUA APIs
- **Sequence models** — possibly LSTM or Transformer for multi-step prediction
- **Probabilistic outputs** — not just point forecasts but distributions

**Owner:** Regina + José + Miguel Garduño (Benchmarking Engineer)

**Estimated completion:** v0.4 — Q1 2027 if HRES 6 is done.

---

## 📅 Master timeline

```
2026
├── Q1 (Mar-May)
│   ├── ✅ HRES 1 — Theory complete
│   ├── ✅ HRES 4 — Digital Shadow complete (v0.2.0)
│   ├── 🟡 HRES 2 — Optimization body (Carlos + Aaron)
│   └── 🟡 HRES 3 — NASA POWER integration (Samuel)
│
├── Q2 (Jun-Aug)
│   ├── 🟡 4D Physical arrangement — after Ixil field visit
│   ├── 🟡 HRES 2 — Community interface in Colab
│   └── 🔴 HRES 5 prep — sensor procurement
│
├── Q3 (Sep-Nov)
│   ├── 🔴 HRES 5 — Real Ixil data integrated
│   ├── 🔴 v0.3.0 release — Real-data digital twin
│   └── 🔴 Technical report draft (Carlos)
│
└── Q4 (Dec)
    ├── 🔴 HRES 6 — Auto-correction in production
    └── 🔴 Output 3.1 delivered to EPICS in IEEE

2027
└── Q1 (Jan-Mar)
    ├── 🔴 HRES 7 — Forecasting capability
    ├── 🔴 v1.0 release
    └── 🔴 Possible publication / conference presentation
```

## 🚦 What can block us

| Risk | Severity | Mitigation |
|---|---|---|
| Field visit to Ixil delayed | High | Use NASA POWER data as interim |
| Sensor budget unavailable | Medium | Start with NASA POWER only (no Tier 3) |
| Team turnover (students graduate) | Medium | Document everything (this folder!) |
| Real data shows ML underperforms | Medium | Have physics-based fallback ready |
| Scope creep (community wants more features) | Low | Stick to Output 3.1 deliverables |

---

## 🎯 What to do next (concrete actions for v0.3.0)

In priority order:

1. **🥚 Complete HRES 2** — build `notebooks/12_community_interface.ipynb` with ipywidgets sliders. Visible impact, low effort. (Aaron + Arturo)

2. **💪 Complete NASA POWER source** — implement `NASAPowerSource` in `src/sensors.py` to pull real Ixil weather data. Unblocks HRES 5 for the weather side. (Samuel)

3. **🔌 Start the REST API** — minimal FastAPI in `src/api.py` to expose predictions. Critical for the "open-access" claim. (José Llashag)

4. **❓ Integrate uncertainty** — wire `src/uncertainty.py` into all ML predictions. (Regina)

5. **📡 Telemetry** — full logging across the simulator. Easy and unblocks debugging. (Arturo)

If we complete these 5 items, v0.3.0 is a substantially more mature product than v0.2.0, ready for the Q3 2026 field deployment.

---

📖 Return to [4D Methodology overview](README.md)
