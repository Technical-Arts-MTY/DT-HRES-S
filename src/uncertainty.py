"""
uncertainty.py — Universe principle: Uncertainty quantification
=================================================================
> "In real life things aren't certain, and our twin must know that.
>  Every time we get a result, we must include a margin of mistake."
> — Technical Arts 4D methodology

This module quantifies and propagates uncertainty in three sources:

  1. INPUT uncertainty   — from sensor calibration limits (Tier 1/2/3)
  2. MODEL uncertainty   — from ML variance (Random Forest tree spread)
  3. ALEATORIC noise     — irreducible variability in the system itself

Combined into a single confidence interval delivered with every prediction.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


# Default uncertainty levels by data tier (% of value)
DEFAULT_INPUT_UNCERTAINTY = {
    'TMY_file':        {'ghi': 5.0,  'temp': 1.0, 'wind': 10.0},
    'NASA_POWER_API':  {'ghi': 8.0,  'temp': 1.5, 'wind': 15.0},
    'physical_sensor': {'ghi': 2.0,  'temp': 0.5, 'wind': 3.0},
}


@dataclass
class UncertaintyBudget:
    """Container for the three uncertainty components of a prediction.

    All values are percentages of the predicted quantity.
    """
    input_pct: float       # from sensors / data source
    model_pct: float       # from ML variance
    aleatoric_pct: float   # irreducible

    @property
    def combined_pct(self) -> float:
        """Total uncertainty via quadrature (assumes uncorrelated sources)."""
        return float(np.sqrt(
            self.input_pct ** 2 + self.model_pct ** 2 + self.aleatoric_pct ** 2
        ))

    def interval_95(self, prediction: float) -> tuple[float, float]:
        """95% confidence interval (≈ ±1.96σ assuming Gaussian)."""
        margin = 1.96 * self.combined_pct / 100 * prediction
        return (prediction - margin, prediction + margin)

    def summary(self, prediction: float) -> str:
        lo, hi = self.interval_95(prediction)
        return (f"{prediction:.1f} ± {self.combined_pct:.1f}% "
                f"(95% CI: [{lo:.1f}, {hi:.1f}])")


# -----------------------------------------------------------------------------
# Source 1 — Input uncertainty propagation
# -----------------------------------------------------------------------------
def propagate_pv_input_uncertainty(source_type: str = 'TMY_file') -> float:
    """Estimate PV-power uncertainty due to input sensor errors only.

    For PV: P_pv ∝ GHI, so a fractional error in GHI is roughly the same in P_pv.
    Temperature has small effect (γ ≈ -0.4%/°C × ~1°C ≈ 0.4%).
    Combined via first-order Taylor expansion.
    """
    u = DEFAULT_INPUT_UNCERTAINTY.get(source_type, DEFAULT_INPUT_UNCERTAINTY['TMY_file'])
    # ∂P/∂GHI is ~linear → use full GHI uncertainty
    # ∂P/∂T is ~γ ≈ 0.004/°C — for 1°C uncertainty, ~0.4%
    return float(np.sqrt(u['ghi'] ** 2 + (0.4 * u['temp']) ** 2))


def propagate_wind_input_uncertainty(source_type: str = 'TMY_file') -> float:
    """Wind power error is much larger because P_wind ∝ v³.

    5% error in v becomes ~15% error in P_wind.
    """
    u = DEFAULT_INPUT_UNCERTAINTY.get(source_type, DEFAULT_INPUT_UNCERTAINTY['TMY_file'])
    # ∂P/∂v · v/P = 3 → fractional error multiplied by 3
    return float(3 * u['wind'])


# -----------------------------------------------------------------------------
# Source 2 — Model uncertainty (Random Forest specific)
# -----------------------------------------------------------------------------
def rf_prediction_with_uncertainty(model, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return mean prediction AND per-sample std across the forest's trees.

    The standard deviation across trees is a natural uncertainty estimate
    for Random Forest. High disagreement among trees = high uncertainty.

    Parameters
    ----------
    model : trained sklearn RandomForestRegressor
    X     : input features, shape (n_samples, n_features)

    Returns
    -------
    mean_pred : shape (n_samples,) — average prediction
    std_pred  : shape (n_samples,) — std across the forest's trees
    """
    if not hasattr(model, 'estimators_'):
        raise TypeError("This function requires a fitted RandomForestRegressor.")
    # Collect predictions from every tree
    per_tree = np.array([tree.predict(X) for tree in model.estimators_])
    mean_pred = per_tree.mean(axis=0)
    std_pred = per_tree.std(axis=0)
    return mean_pred, std_pred


def rf_uncertainty_pct(mean_pred: np.ndarray, std_pred: np.ndarray) -> np.ndarray:
    """Convert mean ± std to percentage uncertainty.

    Returns nan for predictions where mean ≈ 0 (avoid divide-by-zero,
    typical at night when no PV power).
    """
    pct = np.where(np.abs(mean_pred) > 1, std_pred / mean_pred * 100, np.nan)
    return pct


# -----------------------------------------------------------------------------
# Source 3 — Aleatoric (irreducible) noise — estimated from training residuals
# -----------------------------------------------------------------------------
def estimate_aleatoric_uncertainty(y_true: np.ndarray, y_pred: np.ndarray,
                                    nonzero_threshold: float = 10) -> float:
    """Estimate residual variability after the model has done its best.

    Computes CV-RMSE on the residuals, which approximates the irreducible
    noise floor — the part of variability the model fundamentally cannot
    explain (e.g., turbulent wind gusts).
    """
    mask = y_true > nonzero_threshold
    if mask.sum() == 0:
        return 0.0
    residuals = y_true[mask] - y_pred[mask]
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mean_y = float(np.mean(y_true[mask]))
    return rmse / mean_y * 100 if mean_y > 0 else 0.0


# -----------------------------------------------------------------------------
# Combined budget — convenience entry point
# -----------------------------------------------------------------------------
def full_budget_for_pv(source_type: str = 'TMY_file',
                       model_uncertainty_pct: float = 5.4,
                       aleatoric_pct: float = 2.0) -> UncertaintyBudget:
    """Build the standard uncertainty budget for a PV prediction.

    Defaults are calibrated for v0.2.0:
      - Model: Random Forest on synthetic data — CV-RMSE 5.4%
      - Aleatoric: small for synthetic data, will grow with real data
    """
    return UncertaintyBudget(
        input_pct=propagate_pv_input_uncertainty(source_type),
        model_pct=model_uncertainty_pct,
        aleatoric_pct=aleatoric_pct,
    )


def full_budget_for_wind(source_type: str = 'TMY_file',
                         model_uncertainty_pct: float = 8.0,
                         aleatoric_pct: float = 10.0) -> UncertaintyBudget:
    """Wind has much larger uncertainty due to cubic v→P dependency."""
    return UncertaintyBudget(
        input_pct=propagate_wind_input_uncertainty(source_type),
        model_pct=model_uncertainty_pct,
        aleatoric_pct=aleatoric_pct,
    )


if __name__ == '__main__':
    # Smoke test
    print("=== PV uncertainty budget (TMY file source) ===")
    b = full_budget_for_pv(source_type='TMY_file')
    pred = 3247.5  # W
    print(f"Input:     ±{b.input_pct:.2f}%")
    print(f"Model:     ±{b.model_pct:.2f}%")
    print(f"Aleatoric: ±{b.aleatoric_pct:.2f}%")
    print(f"Combined:  ±{b.combined_pct:.2f}%")
    print(f"Summary:   {b.summary(pred)}")
    print()
    print("=== Same, but with NASA POWER source (lower-quality data) ===")
    b2 = full_budget_for_pv(source_type='NASA_POWER_API')
    print(f"Combined:  ±{b2.combined_pct:.2f}%")
    print()
    print("=== Wind uncertainty (much larger because P ∝ v³) ===")
    bw = full_budget_for_wind(source_type='TMY_file')
    print(f"Combined:  ±{bw.combined_pct:.2f}%")
    print(f"Summary:   {bw.summary(1820.0)}")
