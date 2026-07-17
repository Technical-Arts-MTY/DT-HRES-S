# 🏗 DT-HRES-S Architecture

## High-level overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    DT-HRES-S DIGITAL TWIN                        │
│                                                                  │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐ │
│  │  TMY data    │→ │  Physics-based │→ │   Hourly system      │ │
│  │  (4 cities)  │  │   simulation   │  │   operation labels   │ │
│  └──────────────┘  └────────────────┘  └──────────┬───────────┘ │
│         │                                          │             │
│         │          ┌─────────────────────────┐    │             │
│         └─────────→│  Feature engineering    │←───┘             │
│                    │  (cyclical encoding)    │                  │
│                    └────────────┬────────────┘                  │
│                                 ↓                                │
│                    ┌─────────────────────────┐                  │
│                    │   ML model training     │                  │
│                    │   DT / RF / SVM / NN    │                  │
│                    └────────────┬────────────┘                  │
│                                 ↓                                │
│                    ┌─────────────────────────┐                  │
│                    │  Validated DT-HRES-S    │←── PHYSICS       │
│                    │  (fast surrogate)       │    CONSTRAINTS   │
│                    └────────────┬────────────┘                  │
│                                 ↓                                │
│           ┌─────────────────────┴─────────────────────┐         │
│           ↓                                           ↓         │
│  ┌──────────────────┐                    ┌──────────────────┐  │
│  │  Community use:  │                    │   Scenario       │  │
│  │  size systems    │                    │   exploration:   │  │
│  │  in seconds      │                    │   what-if loops  │  │
│  └──────────────────┘                    └──────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Why a "twin" and not just a simulator?

A traditional simulator (HOMER, PVsyst) takes minutes per scenario. A digital twin that has **learned the simulator's behavior** answers in **milliseconds**, which enables:

- **Interactive Colab sliders** for community workshops (Task 4.1)
- **Hundreds of scenarios** to find the optimal system size
- **Real-time updates** when local conditions change
- **Generalization to new communities** without re-running expensive physics simulations every time

The trade-off: the twin must be **validated** against the physics so we trust its outputs. That's what Task 3.4 is for.

## Module dependencies

```
data_loader ────┐
                │
                ↓
            pv_model ────┐
            wind_model ──┼──→ hres_simulator ──→ (training data) ──→ ml_models
            battery_model┘                                            │
                                                                       ↓
                                                              dt_hres_s_v1.pkl
                                                                       │
                                                                       ↓
                                                              validation
                                                                       │
                                                                       ↓
                                                              community deployment
```

## Data flow per city (training)

```
SolarDataofMexicanCities.xlsx (1 sheet per city)
            │
            ↓  src/data_loader.process_raw()
            │
data/processed/<city>_tmy.csv  (8,737 rows × 22 cols)
            │
            ↓  hres_simulator.run(df, config)
            │
DataFrame with physics outputs:
  • p_pv_W (target)
  • p_wind_W
  • soc, p_unserved_W, ...
            │
            ↓  ml_models.cyclical_encode() + benchmark()
            │
        Trained model + metrics
            │
            ↓  results/models/*.pkl
```

## Why these 4 ML algorithms?

The project mandate (Task 3.3) specifies these four. Each plays a role:

| Algorithm | Strength | Role in DT-HRES-S |
|---|---|---|
| **Decision Tree** | Fully interpretable, fast | Educational tool, baseline for community workshops |
| **Random Forest** | Robust, low variance, no scaling | **Default production model** |
| **SVM (RBF)** | Captures smooth non-linearities | Comparison baseline; usually slower at inference |
| **Neural Network** | High capacity, can capture complex interactions | Best performance on large datasets; harder to explain |

Selection criteria (Task 3.4):
1. Cross-city R² ≥ 0.95 on the leave-one-city-out test
2. CV-RMSE ≤ 10% (ASHRAE Guideline 14)
3. Inference time < 100 ms for 1 year of data
4. Reproducibility: fixed random seeds, version-locked dependencies

## Where new contributors plug in

| Module | Module leader from Task 3 | Open work items |
|---|---|---|
| `data_loader.py` | Samuel Canul | Add Ixil-specific TMY; load curves |
| `pv_model.py` | Víctor Cardeña | Add bifacial panels, tracking systems |
| `wind_model.py` | Víctor Cardeña | Add additional turbine catalog entries |
| `battery_model.py` | Aaron Cuevas | Add capacity-fade model |
| `hres_simulator.py` | Daniel Leiva / Aaron | Add diesel genset backup |
| `ml_models.py` | José Llashag / Regina | Hyperparameter optimization (Optuna) |
| `validation.py` | Miguel Garduño | Physics-constraint checking |
| Notebooks | Arturo Cruz | Add ipywidgets for community-facing UI |
