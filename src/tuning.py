"""
tuning.py — Nested leave-one-city-out tuning of the DT-HRES-S surrogates
==========================================================================
Closes the pending task of notebook 20, section 7: a fair hyperparameter
search for the neural network, compared against Decision Tree, Random
Forest and SVM on the same held-out-city folds.

Relation to previous work:
    `ml_models.leave_one_city_out()` and the first version of notebook 20
    section 7 scored the four models on the same city folds, with fixed
    features, and picked the NN grid point by its mean R2 on those folds.
    Read per city, that run showed (a) the NN gap with RF came from the
    Mexico City fold alone, (b) MAPE reached 1e17 because half the hours
    have zero power, and (c) the NN was chosen and scored on the same
    folds. This module keeps the folds and models and changes the
    protocol around them. `ml_models` is left untouched so earlier
    notebooks still run. Full rationale and results:
    docs/model_selection.md

Design decisions (previous -> new):
    D1  Features: 20 fixed inputs -> two sets compared (ablation), the
        original one and the inputs actually read by `pv_model.simulate()`.
        Elevation and pressure are never read by the PV physics, and Mexico
        City lies far outside their training range.
    D2  Metrics: MAPE over all hours -> MAPE on daylight hours plus nMAE,
        which divides once by total energy. R2 and CV-RMSE are kept.
    D3  Folds: one level -> nested leave-one-city-out. The configuration is
        chosen with the three training cities only, then scored on the
        held-out city, so the held-out city still stands in for Ixil.
    D4  Selection: best mean R2 -> best worst-case inner R2. Ixil is one
        unseen site, not an average of sites.
    D5  The same features, folds, metrics and seeds for all four models.

Usage:
    python -m src.tuning --smoke          # 1-2 min end-to-end check
    python -m src.tuning                  # full run (inner + outer)
    python -m src.tuning --phases final   # deployment config on all 4 cities

Results are appended to CSV files as they finish, so an interrupted run
(e.g., a Colab disconnect) resumes where it stopped.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import warnings
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from . import battery_model, ml_models, pv_model, wind_model
from . import hres_simulator as hres
from .data_loader import CITIES, load_city


# -----------------------------------------------------------------------------
# Features (D1)
# -----------------------------------------------------------------------------
CYCLICAL_FEATURES = ['hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                     'doy_sin', 'doy_cos']

# Feature set used by notebook 20 before this module existed.
BASE_FEATURES = ml_models.DEFAULT_FEATURES + CYCLICAL_FEATURES

# Inputs read by pv_model.simulate() to compute the target:
#   solar_position   <- day_of_year, hour, latitude, longitude
#   poa_irradiance   <- ghi_Wm2, dhi_Wm2, dni_proj_Wm2
#   cell_temperature <- dry_bulb_C, wind_speed_ms
# Cyclical encodings follow their source column. month, elevation_m,
# atm_pressure_atm, rel_humidity_pct and wind_dir_deg are never read.
PHYSICAL_FEATURES = [
    'ghi_Wm2', 'dni_proj_Wm2', 'dhi_Wm2',
    'dry_bulb_C', 'wind_speed_ms',
    'hour', 'day_of_year', 'latitude', 'longitude',
    'hour_sin', 'hour_cos', 'doy_sin', 'doy_cos',
]

FEATURE_SETS = {'base': BASE_FEATURES, 'physical': PHYSICAL_FEATURES}

# The ablation only removes inputs; it never adds new information.
assert set(PHYSICAL_FEATURES) <= set(BASE_FEATURES)

TARGET = 'p_pv_W'


# -----------------------------------------------------------------------------
# Metrics (D2)
# -----------------------------------------------------------------------------
# Below 50 W (1.25 % of the 4 kWp array) the hour is dawn, dusk or night:
# relative errors there are huge but carry almost no energy.
DAYLIGHT_THRESHOLD_W = 50.0


def metrics(y_true, y_pred) -> dict:
    """R2, CV-RMSE, nMAE and daylight MAPE, all in percent except R2."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true

    mean_y = y_true.mean()
    total_y = y_true.sum()
    day = y_true > DAYLIGHT_THRESHOLD_W

    return {
        'R2': r2_score(y_true, y_pred),
        'CV_RMSE_pct': 100 * np.sqrt(mean_squared_error(y_true, y_pred)) / mean_y
                       if mean_y > 0 else np.nan,
        'nMAE_pct': 100 * np.abs(err).sum() / total_y if total_y > 0 else np.nan,
        'MAPE_day_pct': 100 * np.mean(np.abs(err[day] / y_true[day]))
                        if day.any() else np.nan,
    }


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
NN_GRID = {
    'hidden_layer_sizes': [(64,), (128,), (128, 64), (256, 128)],
    'alpha': [1e-4, 1e-3, 1e-2],          # L2 regularization
    'learning_rate_init': [1e-3, 5e-3],
}

# Two configurations and a handful of epochs: only checks the plumbing.
SMOKE_GRID = {
    'hidden_layer_sizes': [(64,), (128, 64)],
    'alpha': [1e-4],
    'learning_rate_init': [1e-3],
}

# The first seed is used for the search; all of them for the final scores,
# so the reported number shows how much it moves with initialization.
SEEDS = (42, 0, 1, 2, 3)

# Fixed hyperparameters of the reference models (notebook 20, section 7).
BASELINES = ('DecisionTree', 'RandomForest', 'SVM')
DETERMINISTIC = {'SVM'}


def iter_configs(grid: dict):
    keys = list(grid)
    for combo in product(*(grid[k] for k in keys)):
        yield dict(zip(keys, combo))


def config_label(cfg: dict) -> str:
    """Readable, CSV-safe identifier, e.g. 'h=128x64 a=1e-04 lr=1e-03'."""
    h = 'x'.join(str(n) for n in cfg['hidden_layer_sizes'])
    return f"h={h} a={cfg['alpha']:.0e} lr={cfg['learning_rate_init']:.0e}"


def build_nn(cfg: dict, seed: int, max_iter: int = 400):
    # Scaling lives inside the pipeline, so it is fitted on training cities only.
    return make_pipeline(
        StandardScaler(),
        MLPRegressor(max_iter=max_iter, early_stopping=True,
                     n_iter_no_change=15, random_state=seed, **cfg),
    )


def build_baseline(name: str, seed: int):
    if name == 'DecisionTree':
        return DecisionTreeRegressor(max_depth=20, min_samples_leaf=5,
                                     random_state=seed)
    if name == 'RandomForest':
        # n_jobs=1: parallelism is already handled one level up.
        return RandomForestRegressor(n_estimators=200, max_depth=20,
                                     min_samples_leaf=5, n_jobs=1,
                                     random_state=seed)
    if name == 'SVM':
        return make_pipeline(StandardScaler(), SVR(C=10, gamma='scale'))
    raise ValueError(f'Unknown baseline: {name}')


# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------
def default_config() -> hres.HRESConfig:
    """Same reference system as notebook 20, section 2."""
    return hres.HRESConfig(
        pv=pv_model.PVSystem(p_rated_W=400, n_panels=10, tilt_deg=20, azimuth_deg=180),
        wind=wind_model.WindTurbine(rated_power_W=3000, rotor_diameter_m=4.0,
                                    hub_height_m=12.0),
        battery=battery_model.Battery(capacity_kWh=10, p_max_charge_kW=3.0,
                                      p_max_discharge_kW=3.0),
    )


def build_dataset(config: hres.HRESConfig | None = None, stride: int = 1) -> pd.DataFrame:
    """Simulate the four cities and add cyclical features.

    stride > 1 keeps one row out of `stride` (used by the smoke test only).
    """
    config = config or default_config()
    sims = [hres.run(load_city(city), config) for city in CITIES]
    df = ml_models.cyclical_encode(pd.concat(sims, ignore_index=True))
    df = df.dropna(subset=BASE_FEATURES + [TARGET]).reset_index(drop=True)
    return df.iloc[::stride].reset_index(drop=True)


# -----------------------------------------------------------------------------
# Single fit (runs inside a worker process)
# -----------------------------------------------------------------------------
def _fit_eval(model, X, y, train_idx, test_idx) -> dict:
    t0 = time.perf_counter()
    with warnings.catch_warnings():
        # Hitting max_iter is recorded in the 'epochs' column instead.
        warnings.simplefilter('ignore', ConvergenceWarning)
        model.fit(X[train_idx], y[train_idx])
    fit_s = time.perf_counter() - t0
    epochs = getattr(model[-1] if hasattr(model, 'steps') else model, 'n_iter_', np.nan)

    t0 = time.perf_counter()
    pred = model.predict(X[test_idx])
    predict_us = 1e6 * (time.perf_counter() - t0) / len(test_idx)

    out = metrics(y[test_idx], pred)
    out.update(epochs=epochs, fit_s=fit_s, predict_us_per_sample=predict_us)
    return out


def _held_out_task(key: dict, model, X, y, cities, train_out: tuple, test_city: str) -> dict:
    """Train on every city not in `train_out`, test on `test_city`."""
    train_idx = np.flatnonzero(~np.isin(cities, train_out))
    test_idx = np.flatnonzero(cities == test_city)
    return {**key, **_fit_eval(model, X, y, train_idx, test_idx)}


# -----------------------------------------------------------------------------
# Checkpointed parallel execution
# -----------------------------------------------------------------------------
def _run_tasks(tasks: list, csv_path: Path, key_cols: list, n_jobs: int) -> pd.DataFrame:
    """Run (key, delayed_call) tasks, skipping keys already in `csv_path`.

    Results are appended in batches, so at most one batch is lost if the
    process dies.
    """
    done = set()
    if csv_path.exists():
        prev = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        done = set(map(tuple, prev[key_cols].to_numpy()))

    pending = [(k, call) for k, call in tasks
               if tuple(str(k[c]) for c in key_cols) not in done]
    print(f'  {csv_path.name}: {len(tasks) - len(pending)} done, {len(pending)} pending')

    workers = joblib.cpu_count() if n_jobs < 0 else n_jobs
    batch = max(1, 4 * workers)
    t0 = time.perf_counter()

    with Parallel(n_jobs=n_jobs) as parallel:
        for start in range(0, len(pending), batch):
            rows = parallel(call for _, call in pending[start:start + batch])
            pd.DataFrame(rows).to_csv(csv_path, mode='a', index=False,
                                      header=not csv_path.exists())
            n = min(start + batch, len(pending))
            print(f'    {n}/{len(pending)}  ({time.perf_counter() - t0:.0f} s)', flush=True)

    return pd.read_csv(csv_path)


# -----------------------------------------------------------------------------
# Configuration selection (D4)
# -----------------------------------------------------------------------------
def select_configs(results: pd.DataFrame, group_cols: list) -> pd.DataFrame:
    """Per group, keep the config with the best worst-case R2 (mean R2 breaks ties)."""
    agg = (results.groupby(group_cols + ['config'])['R2']
                  .agg(R2_worst='min', R2_mean='mean', n_folds='count')
                  .reset_index())
    agg = agg.sort_values(group_cols + ['R2_worst', 'R2_mean'],
                          ascending=[True] * len(group_cols) + [False, False])
    return agg.groupby(group_cols, as_index=False).first()


# -----------------------------------------------------------------------------
# Run bookkeeping
# -----------------------------------------------------------------------------
def _environment() -> dict:
    return {
        'started_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'python': platform.python_version(),
        'sklearn': sklearn.__version__,
        'numpy': np.__version__,
        'pandas': pd.__version__,
        'joblib': joblib.__version__,
        'platform': platform.platform(),
        'cpu_count': joblib.cpu_count(),
    }


def _check_run_file(out_dir: Path, fingerprint: dict) -> None:
    """Refuse to mix two different experiments in the same folder."""
    path = out_dir / 'run.json'
    if path.exists():
        run = json.loads(path.read_text(encoding='utf-8'))
        if run['fingerprint'] != fingerprint:
            raise ValueError(f'{out_dir} holds a different experiment; '
                             'use another --out folder.')
    else:
        run = {'fingerprint': fingerprint, 'sessions': []}
    run['sessions'].append(_environment())
    path.write_text(json.dumps(run, indent=2), encoding='utf-8')


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
def run(out_dir: str | Path,
        phases: tuple = ('inner', 'outer'),
        n_jobs: int = -1,
        smoke: bool = False) -> dict:
    """Run the requested phases and return the summary tables.

    inner : NN grid search, training on 2 cities, validating on the 3rd,
            for every held-out (outer) city.
    outer : selected NN config and the three baselines, trained on 3 cities
            and scored on the held-out one, over all seeds.
    final : NN grid over plain leave-one-city-out on all 4 cities; picks the
            configuration to deploy. Not part of the evaluation.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    grid = SMOKE_GRID if smoke else NN_GRID
    max_iter = 20 if smoke else 400
    stride = 10 if smoke else 1
    seeds = SEEDS[:2] if smoke else SEEDS

    configs = {config_label(c): c for c in iter_configs(grid)}
    _check_run_file(out_dir, {
        'grid': list(configs), 'max_iter': max_iter, 'stride': stride,
        'seeds': list(seeds), 'features': FEATURE_SETS,
        'daylight_threshold_W': DAYLIGHT_THRESHOLD_W,
    })

    df = build_dataset(stride=stride)
    y = df[TARGET].to_numpy(dtype=float)
    cities = df['city'].to_numpy()
    X_sets = {name: df[cols].to_numpy(dtype=float) for name, cols in FEATURE_SETS.items()}
    city_names = list(CITIES)
    print(f'Dataset: {len(df):,} rows, {len(city_names)} cities')

    if 'inner' in phases:
        print('Phase inner: NN search with 3 cities per outer fold')
        tasks = []
        for fset, X in X_sets.items():
            for outer in city_names:
                for inner in (c for c in city_names if c != outer):
                    for label, cfg in configs.items():
                        key = {'feature_set': fset, 'outer_city': outer,
                               'config': label, 'inner_city': inner}
                        tasks.append((key, delayed(_held_out_task)(
                            key, build_nn(cfg, seeds[0], max_iter), X, y, cities,
                            (outer, inner), inner)))
        _run_tasks(tasks, out_dir / 'inner.csv',
                   ['feature_set', 'outer_city', 'config', 'inner_city'], n_jobs)

    if 'outer' in phases:
        print('Phase outer: held-out city scores for all four models')
        selected = select_configs(pd.read_csv(out_dir / 'inner.csv'),
                                  ['feature_set', 'outer_city'])
        selected.to_csv(out_dir / 'selected_configs.csv', index=False)

        tasks = []
        for row in selected.itertuples(index=False):
            for seed in seeds:
                key = {'feature_set': row.feature_set, 'outer_city': row.outer_city,
                       'model': 'NeuralNetwork', 'config': row.config, 'seed': seed}
                tasks.append((key, delayed(_held_out_task)(
                    key, build_nn(configs[row.config], seed, max_iter),
                    X_sets[row.feature_set], y, cities,
                    (row.outer_city,), row.outer_city)))
        for fset, X in X_sets.items():
            for outer in city_names:
                for name in BASELINES:
                    for seed in (seeds[:1] if name in DETERMINISTIC else seeds):
                        key = {'feature_set': fset, 'outer_city': outer,
                               'model': name, 'config': '-', 'seed': seed}
                        tasks.append((key, delayed(_held_out_task)(
                            key, build_baseline(name, seed), X, y, cities,
                            (outer,), outer)))
        _run_tasks(tasks, out_dir / 'outer.csv',
                   ['feature_set', 'outer_city', 'model', 'config', 'seed'], n_jobs)

    if 'final' in phases:
        print('Phase final: deployment config over leave-one-city-out on 4 cities')
        tasks = []
        for fset, X in X_sets.items():
            for held in city_names:
                for label, cfg in configs.items():
                    key = {'feature_set': fset, 'config': label, 'held_out_city': held}
                    tasks.append((key, delayed(_held_out_task)(
                        key, build_nn(cfg, seeds[0], max_iter), X, y, cities,
                        (held,), held)))
        final = _run_tasks(tasks, out_dir / 'final.csv',
                           ['feature_set', 'config', 'held_out_city'], n_jobs)
        select_configs(final, ['feature_set']).to_csv(
            out_dir / 'deployment_config.csv', index=False)

    return summarize(out_dir)


def summarize(out_dir: str | Path) -> dict:
    """Build the result tables from whatever CSVs exist in `out_dir`."""
    out_dir = Path(out_dir)
    tables = {}

    path = out_dir / 'outer.csv'
    if path.exists():
        outer = pd.read_csv(path)
        cols = ['R2', 'CV_RMSE_pct', 'nMAE_pct', 'MAPE_day_pct', 'predict_us_per_sample']
        keys = ['feature_set', 'model', 'outer_city']

        per_city = outer.groupby(keys)[cols].mean()
        per_city['R2_std_seeds'] = outer.groupby(keys)['R2'].std()
        per_city['n_seeds'] = outer.groupby(keys)['R2'].count()
        per_city = per_city.reset_index()

        summary = (per_city.groupby(['feature_set', 'model'])
                   .agg(R2_mean=('R2', 'mean'), R2_worst=('R2', 'min'),
                        CV_RMSE_pct=('CV_RMSE_pct', 'mean'),
                        nMAE_pct=('nMAE_pct', 'mean'),
                        MAPE_day_pct=('MAPE_day_pct', 'mean'),
                        predict_us=('predict_us_per_sample', 'mean'))
                   .reset_index()
                   .sort_values(['feature_set', 'R2_worst'], ascending=[True, False]))

        per_city.to_csv(out_dir / 'per_city.csv', index=False)
        summary.to_csv(out_dir / 'summary.csv', index=False)
        tables.update(per_city=per_city, summary=summary)

    for name in ('selected_configs', 'deployment_config'):
        path = out_dir / f'{name}.csv'
        if path.exists():
            tables[name] = pd.read_csv(path)

    return tables


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description='Nested LOCO tuning for DT-HRES-S')
    parser.add_argument('--out', default=None,
                        help='results folder (default: results/tuning/full or /smoke)')
    parser.add_argument('--phases', nargs='+', default=['inner', 'outer'],
                        choices=['inner', 'outer', 'final'])
    parser.add_argument('--n-jobs', type=int, default=-1)
    parser.add_argument('--smoke', action='store_true',
                        help='tiny grid, 20 epochs, 1/10 of the rows')
    args = parser.parse_args(argv)

    out = args.out or f"results/tuning/{'smoke' if args.smoke else 'full'}"
    t0 = time.perf_counter()
    tables = run(out, phases=tuple(args.phases), n_jobs=args.n_jobs, smoke=args.smoke)

    with pd.option_context('display.width', 160, 'display.max_columns', 20):
        for name, table in tables.items():
            print(f'\n== {name}\n{table.round(3).to_string(index=False)}')
    print(f'\nTotal time: {(time.perf_counter() - t0) / 60:.1f} min. Results in {out}')


if __name__ == '__main__':
    main()
