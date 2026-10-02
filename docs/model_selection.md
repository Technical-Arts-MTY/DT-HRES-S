# 🧪 Model Selection — Nested Leave-One-City-Out

This document records how the deployment model of DT-HRES-S is chosen, what changed with respect to the previous protocol, and why. It closes the pending task of notebook 20, section 7 ("fair tuning of the neural network before the physical device").

| | |
|---|---|
| **Code** | `src/tuning.py` (logic), `notebooks/20_raspberry_deployment.ipynb` §7 (Colab run) |
| **Tests** | `tests/test_tuning.py` |
| **Target** | `p_pv_W` — hourly PV AC power of the reference 4 kWp array |
| **Models** | Decision Tree, Random Forest, SVM, Neural Network (MLP) — Task 3.3 |

## Why this protocol had to change

The previous comparison (notebook 20 §7, first version, and `ml_models.leave_one_city_out()`) ran the four models over leave-one-city-out folds and reported the mean R². Its Colab run gave:

```
Previous protocol (base features, NN grid scored on the same folds it was chosen on)
  Random Forest   R² = 0.994
  Decision Tree   R² = 0.989
  Neural Network  R² = 0.872   ← Mexico City fold: R² = 0.511, CV-RMSE = 96 %
  SVM             R² = 0.632
  MAPE            1e16 – 1e17 for every model and city
```

Reading that table per city, three problems appear. None of them is a bug in the code; they are weaknesses of the protocol:

1. **The gap between NN and RF came from a single fold.** Without Mexico City the NN averaged R² ≈ 0.99. The question was *why* Mexico City.
2. **MAPE was not usable.** Half of the hours are night (`p_pv_W = 0`), and MAPE divides every hourly error by the true value.
3. **The NN number was optimistic.** The grid was searched and scored on the same four folds; the other three models had no such advantage.

The five decisions below answer those problems. Each one is listed as *previous → new → why*.

## Design decisions

### D1 — Features: inputs read by the physics (ablation)

**Previous:** 20 features — `ml_models.DEFAULT_FEATURES` plus six cyclical encodings.

**New:** two sets are compared side by side.

| Set | Columns | Count |
|---|---|---|
| `base` | the previous 20 | 20 |
| `physical` | only the columns read by `pv_model.simulate()` | 13 |

`pv_model.simulate()` reads `day_of_year`, `hour`, `latitude`, `longitude` (solar position), `ghi_Wm2`, `dhi_Wm2`, `dni_proj_Wm2` (plane-of-array irradiance) and `dry_bulb_C`, `wind_speed_ms` (cell temperature). Cyclical encodings follow their source column. `elevation_m`, `atm_pressure_atm`, `rel_humidity_pct`, `wind_dir_deg` and `month` are never read.

**Why:** Mexico City sits far outside the training range of two of the unused inputs:

| | Monterrey | Campeche | San Ignacio | **Mexico City** |
|---|---|---|---|---|
| `elevation_m` | 540 | 10 | 80 | **2 240** |
| `atm_pressure_atm` | 0.95 | 1.00 | 0.99 | **0.78** |

A neural network extrapolates those values through weights that have nothing to do with the physics of the panel. Tree models cannot extrapolate: they treat 2 240 m as 540 m, which happens to be the physically correct behaviour for this target. The decision comes from reading the simulator, not from the scores, and the `base` set is kept so the effect can be measured. The physical set only removes inputs (`assert` in `src/tuning.py`).

**Rule kept for future features:** an input is legitimate only if it is available before the answer is known. Intermediate simulator outputs (`poa_Wm2`, `t_cell_C`, `p_dc_W`) are in the simulated DataFrame but are never features: they would leak the target.

### D2 — Metrics: daylight MAPE and nMAE

**Previous:** R², MAPE, CV-RMSE.

**New:** R², CV-RMSE, nMAE and MAPE on daylight hours.

| Metric | Definition | Why |
|---|---|---|
| R² | `sklearn.metrics.r2_score` | Unchanged |
| CV-RMSE | `100 · RMSE / mean(y)` | Unchanged; ASHRAE Guideline 14 metric |
| nMAE | `100 · Σ|e| / Σy` | Divides once by the total energy; never undefined |
| MAPE (daylight) | MAPE over hours with `y > 50 W` | Keeps the metric the report asks for, on the hours where it is defined |

The 50 W threshold (`DAYLIGHT_THRESHOLD_W`, 1.25 % of the array) removes dawn and dusk hours where a 20 W error reads as a 400 % error while carrying almost no energy.

### D3 — Nested folds

**Previous:** one level. The NN grid was evaluated on the four held-out cities and the best mean was reported.

**New:** two levels.

```
OUTER (scoring) — one fold per held-out city
│
├─ held out: Mexico City → training cities: Monterrey, Campeche, San Ignacio
│   │
│   ├─ INNER (selection) — training cities only
│   │     for each of the 24 NN configurations:
│   │         train on 2 cities, validate on the 3rd   (× 3)
│   │     → keep the configuration with the best worst-case R²   (D4)
│   │
│   └─ train the chosen configuration on the 3 cities → score on Mexico City
│
└─ ... same for the other three cities
```

**Why:** choosing a configuration and scoring it on the same folds is studying with the exam. The held-out city must play no role in the choice, otherwise it no longer represents Ixil. The size of that bias is measurable here: with the same `base` features, the previous protocol gave the NN a mean R² of 0.872; the nested protocol gives 0.636.

The outer score evaluates the *procedure*. The configuration to deploy is chosen afterwards with the same rule over the four cities (`--phases final`, file `deployment_config.csv`).

### D4 — Selection rule: best worst case

**Previous:** best mean R² across folds.

**New:** best minimum R² across inner folds; mean R² breaks ties.

**Why:** Ixil is one unseen site, not an average of sites. A configuration that is excellent in three cities and fails in the fourth is a bad bet for a single deployment. The mean also lets one extreme fold decide the ranking, which is what happened with Mexico City.

### D5 — Same conditions for the four models

Features, folds, metrics and seeds are shared by the four models. Every outer score is repeated over five seeds (`SEEDS = (42, 0, 1, 2, 3)`; SVM is deterministic and runs once), so the spread caused by initialization is reported next to the score.

The baselines keep the fixed hyperparameters of notebook 20 §7 (DT `max_depth=20, min_samples_leaf=5`; RF 200 trees, `max_depth=20, min_samples_leaf=5`; SVM RBF `C=10`). Only the NN is tuned; this is declared as a limitation below.

## Results

> **Source:** official Colab run, 2026-10-01 — Python 3.13.15, scikit-learn 1.6.1, numpy 2.1.3, pandas 2.2.3, joblib 1.6.0, 2 CPU cores, 896 fits in 61 min. A local verification run (Python 3.14.6, scikit-learn 1.9.1, numpy 2.5.3, pandas 3.0.6, 16 CPU cores, 14.5 min) gave identical NN, RF and SVM scores to three decimals and the same selected configurations; Decision Tree scores differ by at most 0.2 percentage points of CV-RMSE. The result therefore holds across three scikit-learn minor versions.

### Summary — mean over held-out cities, seeds averaged

| Features | Model | R² mean | R² worst | CV-RMSE % | nMAE % | MAPE day % | Inference, 1 year |
|---|---|---|---|---|---|---|---|
| `physical` | **Random Forest** | **0.994** | **0.986** | **9.8** | **4.4** | **9.3** | 344 ms |
| `physical` | Decision Tree | 0.990 | 0.983 | 12.7 | 5.7 | 11.0 | 4 ms |
| `physical` | Neural Network | 0.990 | 0.980 | 12.7 | 9.2 | 16.4 | 57 ms |
| `physical` | SVM | 0.873 | 0.607 | 39.2 | 33.0 | 37.8 | 18.5 s |
| `base` | Random Forest | 0.994 | 0.986 | 10.0 | 4.5 | 9.5 | 294 ms |
| `base` | Decision Tree | 0.989 | 0.982 | 13.9 | 6.0 | 11.8 | 4 ms |
| `base` | Neural Network | 0.636 | −0.377 | 52.6 | 49.6 | 72.9 | 43 ms |
| `base` | SVM | 0.632 | −0.002 | 70.0 | 60.0 | 61.3 | 22.0 s |

Inference is `predict_us_per_sample × 8 737 hours`, single process, measured on the Colab CPU runtime while other fits were running. On the local laptop the same figures were roughly half (RF 160 ms, NN 40 ms). It must be measured again on the Raspberry Pi 5.

### CV-RMSE per held-out city (%)

| Features | Model | Campeche | Mexico City | Monterrey | San Ignacio |
|---|---|---|---|---|---|
| `physical` | Random Forest | 6.1 | 10.0 | 7.6 | 15.6 |
| `physical` | Decision Tree | 9.0 | 12.6 | 11.9 | 17.2 |
| `physical` | Neural Network | 12.4 | 10.3 | 9.7 | 18.4 |
| `base` | Neural Network | 19.4 | **150.9** | 11.7 | 28.4 |

The full table (all metrics, seed spread) is `per_city.csv`.

### Findings

1. **D1 explains the Mexico City failure.** With `physical` features the NN goes from R² −0.377 to 0.994 in Mexico City, and its seed spread there drops from ±0.95 to ±0.001. The other cities barely move.
2. **Random Forest still leads, now on a fair comparison.** The R² gap with the NN is small (worst case 0.986 vs 0.980), but RF makes half the energy error (nMAE 4.4 % vs 9.2 %). RF is unaffected by D1, as expected from a model that cannot extrapolate, so its lead does not depend on that decision.
3. **San Ignacio is the hardest site for every model** (CV-RMSE 15–18 %, daylight MAPE 21–27 %). It is the northern- and western-most city: its latitude and longitude lie outside the range of the other three.
4. **The same mechanism appears in the inner folds.** When the training cities are only Campeche and Mexico City (latitudes 19.8° and 19.4°), the NN fails on Monterrey and San Ignacio (best inner R² 0.02 and −0.17). The issue is not a particular input but extrapolation beyond the training range.
5. **For Ixil** (≈ 21.3° N, 89.7° W) latitude lies inside the training range and longitude just east of Campeche. The Campeche fold is the closest proxy: RF scores R² 0.998, nMAE 3.0 % there.
6. **No network hit the 400-epoch cap** (maximum 132); all stopped by early stopping.

### NN configuration to deploy, if the NN is ever chosen

`hidden_layer_sizes=(128, 64), alpha=1e-2, learning_rate_init=1e-3`, physical features — worst-case R² 0.985 over the four cities. Recorded for reproducibility; the current evidence points to Random Forest.

## Against the Task 3.4 selection criteria

The criteria listed in `docs/architecture.md`:

| Criterion | RF | NN | DT |
|---|---|---|---|
| Cross-city R² ≥ 0.95 | ✅ all cities | ✅ all cities (physical) | ✅ all cities |
| CV-RMSE ≤ 10 % | ⚠️ mean 9.8 %, San Ignacio 15.6 % | ❌ mean 12.7 % | ❌ mean 12.7 % |
| Inference < 100 ms per year | ❌ 344 ms single process | ✅ 57 ms | ✅ 4 ms |
| Reproducibility | ✅ fixed seeds, versions logged | ✅ | ✅ |

Two open points for the team:

- **The CV-RMSE threshold is not consistent across the repository.** `docs/architecture.md` and the persona example in `docs/4D_methodology/02_body_optimization.md` say 10 %; `docs/RESEARCH_GUIDE.md` §4.4 quotes ASHRAE Guideline 14 as ≤ 30 % hourly and ≤ 15 % monthly. Against 30 % hourly, every model except SVM passes in every city.
- **RF inference time** exceeds the budget on Colab (344 ms per year with one process, `n_jobs=1`). The Pi 5 has four cores; `n_jobs=-1` at inference, or fewer trees, are the levers to bring it under 100 ms. The NN meets the budget (57 ms) at a higher energy error (nMAE 9.2 % vs 4.4 %), so the choice is a trade-off the team has to make with a measurement on the device.

## Limitations

- **Four cities.** Inner folds train on two cities, so the selection is noisy: the chosen configuration differs between outer folds (`(128, 64)` wins in 7 of 8).
- **Only the NN is tuned.** DT, RF and SVM keep fixed hyperparameters; SVM in particular is likely under-configured.
- **Simulator, not reality.** Every score measures how well a model imitates `hres_simulator`, not the error against measured power. The sim-to-real gap is open until HRES 5 brings sensor data.
- **Night hours are kept.** Removing them (the target is zero by physics) would halve the training cost and is a candidate for future work; it was not done here to change one thing at a time.

## How to reproduce

```bash
python -m src.tuning --smoke                           # 1-2 min check
python -m src.tuning --phases inner outer final        # full run
pytest tests/test_tuning.py -v
```

In Colab: notebook 20, section 7. Results are appended to CSV as each batch finishes; running the cell again resumes an interrupted run. A results folder refuses to mix two different experiments (grid, features, seeds or threshold).

| File | Content |
|---|---|
| `inner.csv` | Every inner fit: feature set, outer city, configuration, inner city, metrics |
| `selected_configs.csv` | Configuration chosen in each outer fold |
| `outer.csv` | Every outer fit, all models and seeds |
| `per_city.csv`, `summary.csv` | Tables above |
| `final.csv`, `deployment_config.csv` | Four-city search and the configuration to deploy |
| `run.json` | Experiment fingerprint and library versions of each session |
