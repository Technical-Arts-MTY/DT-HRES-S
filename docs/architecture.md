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
                                                              tuning (nested LOCO,
                                                              model selection)
                                                                       │
                                                                       ↓
                                                              dt_hres_s_deployment.joblib
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
            ↓  ml_models.cyclical_encode() + benchmark()     (quick, random split)
            ↓  tuning.run()                                   (nested leave-one-city-out)
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

Status of each criterion, the protocol used to measure them and why it replaced the earlier single-level comparison: [model_selection.md](model_selection.md). Note that ASHRAE Guideline 14 sets CV-RMSE ≤ 30 % for hourly data and ≤ 15 % for monthly data (see `RESEARCH_GUIDE.md` §4.4); the 10 % threshold above is stricter than the guideline and is pending confirmation by the team.

## Where new contributors plug in

| Module | Module leader from Task 3 | Open work items |
|---|---|---|
| `data_loader.py` | Samuel Canul | Add Ixil-specific TMY; load curves |
| `pv_model.py` | Víctor Cardeña | Add bifacial panels, tracking systems |
| `wind_model.py` | Víctor Cardeña | Add additional turbine catalog entries |
| `battery_model.py` | Aaron Cuevas | Add capacity-fade model |
| `hres_simulator.py` | Daniel Leiva / Aaron | Add diesel genset backup |
| `ml_models.py` | José Llashag / Regina | Hyperparameter optimization for DT / RF / SVM (only the NN is tuned so far) |
| `tuning.py` | Braulio | Measure inference on the Pi 5; tune the baselines with the same nested folds |
| `validation.py` | Miguel Garduño | Physics-constraint checking |
| Notebooks | Arturo Cruz | Add ipywidgets for community-facing UI |
