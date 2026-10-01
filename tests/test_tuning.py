"""
Tests for src/tuning.py — metrics, feature sets and configuration selection.
Run with:  pytest tests/test_tuning.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import tuning


def test_physical_features_drop_unused_inputs():
    for col in ('elevation_m', 'atm_pressure_atm', 'month', 'month_sin', 'month_cos'):
        assert col not in tuning.PHYSICAL_FEATURES
        assert col in tuning.BASE_FEATURES


def test_metrics_finite_with_night_hours():
    y_true = np.array([0.0, 0.0, 1000.0, 2000.0])
    y_pred = np.array([5.0, 0.0, 900.0, 2100.0])
    m = tuning.metrics(y_true, y_pred)
    assert all(np.isfinite(v) for v in m.values())


def test_daylight_mape_ignores_low_power_hours():
    # 2 W at dawn predicted as 40 W would be a 1900 % error; it must not count.
    y_true = np.array([2.0, 1000.0])
    y_pred = np.array([40.0, 1100.0])
    assert np.isclose(tuning.metrics(y_true, y_pred)['MAPE_day_pct'], 10.0)


def test_nmae_divides_by_total_energy():
    y_true = np.array([0.0, 100.0, 300.0])
    y_pred = np.array([10.0, 90.0, 300.0])
    assert np.isclose(tuning.metrics(y_true, y_pred)['nMAE_pct'], 5.0)


def test_daylight_mape_nan_when_no_daylight():
    m = tuning.metrics(np.zeros(3), np.ones(3))
    assert np.isnan(m['MAPE_day_pct'])


def test_select_configs_prefers_best_worst_case():
    # 'steady' has the lower mean but the better worst case: it must win.
    results = pd.DataFrame({
        'outer_city': ['A'] * 4,
        'config': ['spiky', 'spiky', 'steady', 'steady'],
        'R2': [0.99, 0.50, 0.90, 0.88],
    })
    chosen = tuning.select_configs(results, ['outer_city'])
    assert chosen.loc[0, 'config'] == 'steady'


def test_config_labels_are_unique():
    labels = [tuning.config_label(c) for c in tuning.iter_configs(tuning.NN_GRID)]
    assert len(labels) == len(set(labels)) == 24
