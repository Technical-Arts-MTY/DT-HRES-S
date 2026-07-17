# 🧭 4D Methodology — DT-HRES-S

> *"Digital Twin: A model that corrects current data of our system with information of the future"*
> — Technical Arts, ITESM Student Chapter

This folder documents how the DT-HRES-S project follows the **4D Methodology** for building digital twins from scratch. The methodology was developed by Technical Arts (ITESM Student Chapter) and we adopted it because:

1. **It bridges disciplines.** Digital twin projects mix mechanical, electrical, software, and data engineers. The 4D framework forces all developers to understand the system conceptually first, regardless of their specialty.
2. **It enforces a Feynman-style modeling.** Every dimension must be explainable to a 3-year-old before code is written. This catches conceptual gaps early.
3. **It's progressive.** Each step (HRES 1 through 7) builds on the previous one, so the project never has to be rewritten — only extended.

## 🥚🥚💪💪🧠🧠👻👻 The journey

| Stage | Question | Our document | Status |
|---|---|---|---|
| **1D — Concept** 🥚 | What is HRES and what do we predict? | [01_concept_HRES.md](01_concept_HRES.md) | ✅ Complete |
| **2D — Body** 🥚 | What do we optimize and for whom? | [02_body_optimization.md](02_body_optimization.md) | 🟡 In progress |
| **3D — Mind** 💪 | What sensors/data feed the twin? | [03_mind_sensors.md](03_mind_sensors.md) | 🟡 In progress |
| **4D — Spirit** 💪 | In what physical arrangement does it live? | [04_spirit_physical_arrangement.md](04_spirit_physical_arrangement.md) | 🔴 Awaiting field data |
| **HRES 4** 🧠 | Digital Shadow with synthetic data | (code: `src/hres_simulator.py`) | ✅ Complete |
| **HRES 5** 🧠 | Pipeline replacement with real data | (code: `src/sensors.py`) | 🔴 Pending Ixil field campaign |
| **HRES 6** 👻 | Auto-correction | (code: `src/auto_correction.py`) | 🟡 Scaffold ready |
| **HRES 7** 👻 | ML predicts the future | (code: `src/ml_models.py`) | 🟡 Now-casting works |

📖 Roadmap detallado: [06_roadmap_HRES1_to_7.md](06_roadmap_HRES1_to_7.md)

## 🪐 The Universe principles

Beyond the 4 dimensions, every good digital twin must respect 5 transversal principles. We document how DT-HRES-S addresses each:

📖 [05_universe_principles.md](05_universe_principles.md)

| Principle | Why it matters | DT-HRES-S status |
|---|---|---|
| **Modularity** | The twin must divide its thoughts. Functions independent. | 🟢 Good |
| **Telemetry** | The twin must receive instructions from outside continuously. | 🟡 Logging in place, streaming pending |
| **Tracking** | The twin must know where and when something happened. | 🟡 Timestamps yes, sensor calibration metadata partial |
| **APIs** | The twin must speak with other tools (MATLAB, Python, DBs). | 🔴 REST API pending |
| **Uncertainty** | In real life, things aren't certain. Every result needs an error margin. | 🟡 Module `uncertainty.py` ready, integration pending |

## 🎯 Where to start

If you're a new contributor:

1. Read [01_concept_HRES.md](01_concept_HRES.md) — understand WHAT we're building
2. Read [02_body_optimization.md](02_body_optimization.md) — understand WHY (the optimization goals)
3. Read [06_roadmap_HRES1_to_7.md](06_roadmap_HRES1_to_7.md) — see where YOU fit in
5. Pick a task aligned with your skills and the current stage
6. Read the relevant `src/*.py` module to understand the existing code

## 💡 Why this works

> "As digital twins rely on a general modelling of the system first in math and physics terms, it prioritizes understanding first the general behavior in these terms for all developers, no matter what is its role, following a Feynman's style modelling for the entire system (explain it as you explain to a 3-year-old kid). This methodology surges from the dispersion that a digital twin project can carry, since the developers are from different areas."
> — Technical Arts methodology paper
