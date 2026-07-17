# 👥 Team — Responsibilities by 4D Dimension

This document maps each member of Task 3 (Technical Development) to the dimension of the 4D methodology where their primary responsibility lies. The mapping reflects each person's main focus, not their only task; some responsibilities cross dimensions.

The naming of the dimensions follows the body metaphor of the methodology: a system is brought to life through its Concept (the founding idea), its Body (its structure and purpose), its Mind (its perception), and its Spirit (its physical reality and the whole).

---

## 1D · Concept — theory & equations

| Person | Role | Responsibility |
|---|---|---|
| Víctor Cardeña | Simulation Lead | Codes and maintains the physical models for PV, wind, and battery (`src/pv_model.py`, `src/wind_model.py`, `src/battery_model.py`) |
| Daniel Leiva | Module Leader | Writes and maintains the concept documentation in `docs/4D_methodology/01_concept_HRES.md`; reviews consistency across modules |

📖 Dimension reference: [`01_concept_HRES.md`](01_concept_HRES.md)

---

## 2D · Body — what to optimize and for whom

| Person | Role | Responsibility |
|---|---|---|
| Aaron Cuevas | Technical Lead | Defines the repository structure and integrates the modules; reviews that the four dimensions fit together without conflicts |
| Carlos Rodríguez Tenorio | Data & Design Engineering | Builds the community interface (`notebooks/12_community_interface.ipynb`) and codes the objective calculations: coverage, LCOE, and renewable fraction |

📖 Dimension reference: [`02_body_optimization.md`](02_body_optimization.md)

---

## 3D · Mind — sensors & data

| Person | Role | Responsibility |
|---|---|---|
| Samuel Canul | Data Lead | Implements `NASAPowerSource.fetch_year()` in `src/sensors.py` and obtains the Ixil TMY (21.12°N, −88.73°W) from the NASA POWER API |
| José Llashag | ML Systems & Deployment | Implements `PiranometerSource` (serial / Modbus reading) and configures model deployment |

📖 Dimension reference: [`03_mind_sensors.md`](03_mind_sensors.md)

---

## 4D · Spirit — physical arrangement & reality

| Person | Role | Responsibility |
|---|---|---|
| Arturo Cruz | Integration & Reproducibility | Implements the 5 Universe principles: modularity, telemetry (`src/telemetry.py`), tracking, REST API, and uncertainty propagation |
| Emilio Urbina | Baseline DT/RF | Trains the baseline models (Decision Tree and Random Forest) on the HRES 4 simulator output |
| Félix Valadez | Simulation analytics | Analyzes the simulation series: capacity factors, load curves, and hourly coverage |

📖 Dimension references: [`04_spirit_physical_arrangement.md`](04_spirit_physical_arrangement.md), [`05_universe_principles.md`](05_universe_principles.md)

---

## Cross-cutting — prediction & validation · HRES 6–7

These responsibilities span all dimensions; they consume the outputs and keep the model honest over time.

| Person | Role | Responsibility |
|---|---|---|
| Regina Muñoz | ML & Validation Lead | Validates the models with leave-one-city-out cross-validation and implements drift detection in `src/auto_correction.py` |
| Miguel Garduño | Benchmarking Engineer | Compares the models (DT, RF, SVM, NN) using RMSE, R², and CV-RMSE; verifies physical consistency (P_pv ≤ GHI × area × η_max) |

📖 Stage reference: [`06_roadmap_HRES1_to_7.md`](06_roadmap_HRES1_to_7.md)

---

## Unassigned

| Person | Status |
|---|---|
| Luis Benvenuto | To be assigned — pending profile |
| Roberto Pérez | To be assigned — pending profile |

---

*The mapping above indicates each person's primary responsibility, not their only task. As Technical Lead, Aaron Cuevas works across all dimensions.*
