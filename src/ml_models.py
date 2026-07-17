"""
ml_models.py — Machine Learning candidate models for DT-HRES-S
=================================================================
Wraps the four algorithms required by Task 3.3 of the project:
    1. Decision Tree         (interpretable baseline)
    2. Random Forest         (ensemble, robust)
    3. Support Vector Machine (non-linear kernel regression)
    4. Neural Network        (universal approximator)

All models share the same interface so they can be benchmarked
fairly in `notebooks/10_model_comparison_validation.ipynb`.

The target variable is the **hourly PV-array AC power** (or any other
quantity from the physics simulator). The features are weather data
plus calendar variables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


# Default features for the DT (digital twin) regression problem
DEFAULT_FEATURES = [
    'ghi_Wm2', 'dni_proj_Wm2', 'dhi_Wm2',
    'dry_bulb_C', 'rel_humidity_pct',
    'wind_speed_ms', 'wind_dir_deg',
    'atm_pressure_atm',
    'month', 'hour', 'day_of_year',
    'latitude', 'longitude', 'elevation_m',
]


def cyclical_encode(df: pd.DataFrame) -> pd.DataFrame:
    """Encode hour, month, day_of_year as sin/cos pairs.

    This is critical for any ML model that doesn't natively understand
    that hour=23 is adjacent to hour=0.
    """
    out = df.copy()
    out['hour_sin'] = np.sin(2 * np.pi * out['hour'] / 24)
    out['hour_cos'] = np.cos(2 * np.pi * out['hour'] / 24)
    out['month_sin'] = np.sin(2 * np.pi * out['month'] / 12)
    out['month_cos'] = np.cos(2 * np.pi * out['month'] / 12)
    out['doy_sin'] = np.sin(2 * np.pi * out['day_of_year'] / 365)
    out['doy_cos'] = np.cos(2 * np.pi * out['day_of_year'] / 365)
    return out


def make_models(random_state: int = 42) -> dict:
    """Instantiate the four DT-HRES-S candidate models with sensible defaults.

    SVM and NN are wrapped in pipelines with StandardScaler since they
    are scale-sensitive.
    """
    return {
        'DecisionTree': DecisionTreeRegressor(
            max_depth=15, min_samples_leaf=20, random_state=random_state
        ),
        'RandomForest': RandomForestRegressor(
            n_estimators=200, max_depth=20, min_samples_leaf=10,
            n_jobs=-1, random_state=random_state
        ),
        'SVM': Pipeline([
            ('scaler', StandardScaler()),
            ('svr', SVR(kernel='rbf', C=10, gamma='scale', epsilon=0.05)),
        ]),
        'NeuralNetwork': Pipeline([
            ('scaler', StandardScaler()),
            ('mlp', MLPRegressor(
                hidden_layer_sizes=(64, 32),
                activation='relu',
                solver='adam',
                max_iter=300,
                early_stopping=True,
                random_state=random_state,
            )),
        ]),
    }


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Standard regression metrics + CV-RMSE & MBE used in energy modeling."""
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    mean_y = y_true.mean()
    cv_rmse = (rmse / mean_y * 100) if mean_y > 0 else np.nan  # %
    mbe = (y_pred - y_true).mean()  # mean bias error
    return {
        'RMSE': rmse, 'MAE': mae, 'R2': r2,
        'CV_RMSE_pct': cv_rmse, 'MBE': mbe,
    }


def benchmark(df: pd.DataFrame,
              target_col: str = 'p_pv_W',
              features: list[str] | None = None,
              test_size: float = 0.2,
              random_state: int = 42,
              encode_cyclical: bool = True) -> pd.DataFrame:
    """Train all four candidate models and return a metrics comparison.

    Parameters
    ----------
    df : DataFrame that already contains the target column (e.g., output
         of `hres_simulator.run()`)
    target_col : column to predict (default = 'p_pv_W')
    features : list of feature column names. Defaults to DEFAULT_FEATURES.
    encode_cyclical : whether to add sin/cos features for hour/month/doy

    Returns
    -------
    DataFrame indexed by model name with metrics columns.
    """
    if features is None:
        features = DEFAULT_FEATURES.copy()

    work = cyclical_encode(df) if encode_cyclical else df.copy()
    if encode_cyclical:
        features = features + ['hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                                'doy_sin', 'doy_cos']

    # Drop rows with NaN
    work = work[features + [target_col]].dropna()
    X = work[features].values
    y = work[target_col].values

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=True
    )

    results = {}
    for name, model in make_models(random_state).items():
        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_te)
        results[name] = compute_metrics(y_te, y_pred)

    return pd.DataFrame(results).T


def leave_one_city_out(df_all: pd.DataFrame,
                       target_col: str = 'p_pv_W',
                       city_col: str = 'city',
                       features: list[str] | None = None) -> pd.DataFrame:
    """Cross-validation: train on n-1 cities, test on the held-out city.

    This is the strongest validation for a digital twin meant to generalize
    to new locations (e.g., Ixil, Yucatán).
    """
    if features is None:
        features = DEFAULT_FEATURES.copy()
    work = cyclical_encode(df_all)
    features = features + ['hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                            'doy_sin', 'doy_cos']
    work = work[features + [target_col, city_col]].dropna()

    rows = []
    for held_out in work[city_col].unique():
        train = work[work[city_col] != held_out]
        test = work[work[city_col] == held_out]
        X_tr, y_tr = train[features].values, train[target_col].values
        X_te, y_te = test[features].values, test[target_col].values

        for name, model in make_models().items():
            model.fit(X_tr, y_tr)
            y_pred = model.predict(X_te)
            m = compute_metrics(y_te, y_pred)
            m.update({'held_out_city': held_out, 'model': name})
            rows.append(m)

    return pd.DataFrame(rows).set_index(['held_out_city', 'model'])
