"""
auto_correction.py — HRES 6: Self-correction
================================================
Implements the HRES 6 stage of the 4D methodology: the twin detects when
its predictions diverge from reality and triggers re-training.

This is the difference between a Digital Shadow (static, one-way) and a
true Digital Twin (dynamic, self-correcting).

Activates once HRES 5 is live (real measurements flowing from Ixil).
Before that, this module's `check_drift()` returns informative messages
explaining the dependency.

Workflow:
    1. Each prediction is logged via telemetry.py
    2. When measurements arrive, they are paired with predictions by timestamp
    3. AutoCorrector.check_drift() compares paired errors against threshold
    4. If drift exceeds threshold → retrain model with accumulated data
    5. New model is versioned, validated, and deployed

Owner: Regina Muñoz (ML & Validation Lead) + José Llashag (ML Systems).
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import json
import numpy as np
import pandas as pd


class AutoCorrector:
    """Detects drift between twin predictions and real measurements.

    Once instantiated, it consumes predictions and measurements (via its
    own methods or by reading a telemetry log), pairs them by timestamp,
    and produces drift diagnostics.
    """

    def __init__(self,
                 model_version: str,
                 retraining_threshold_pct: float = 15.0,
                 minimum_samples: int = 100,
                 tolerance_seconds: int = 60):
        """
        Parameters
        ----------
        model_version : str
            Identifier of the model being monitored (e.g., 'rf_v0.2.0')
        retraining_threshold_pct : float
            If mean error exceeds this percentage, recommend retraining.
            ASHRAE Guideline 14 considers >30% CV-RMSE as failed model.
        minimum_samples : int
            Don't evaluate drift until at least this many paired samples exist.
        tolerance_seconds : int
            How close in time a prediction and measurement must be to pair them.
        """
        self.model_version = model_version
        self.threshold = retraining_threshold_pct
        self.min_samples = minimum_samples
        self.tolerance = timedelta(seconds=tolerance_seconds)

        # In-memory buffer of (timestamp, prediction, measurement)
        self._pairs: list[dict] = []

    # ------------------------------------------------------------- ingestion
    def log_prediction(self, timestamp: datetime, prediction: float,
                       features: Optional[dict] = None) -> None:
        """Record a prediction; measurement comes later."""
        self._pairs.append({
            'timestamp': timestamp,
            'prediction': prediction,
            'measurement': None,
            'features': features or {},
        })

    def log_measurement(self, timestamp: datetime, measurement: float) -> bool:
        """Find a matching prediction and pair them.

        Returns True if a pairing was made, False otherwise.
        """
        for entry in self._pairs:
            if entry['measurement'] is None and \
               abs(entry['timestamp'] - timestamp) <= self.tolerance:
                entry['measurement'] = measurement
                return True
        return False

    def load_from_telemetry(self, telemetry_jsonl: str | Path) -> int:
        """Bulk-load predictions and measurements from a telemetry log.

        Returns the number of pairs successfully created.
        """
        n_loaded = 0
        with open(telemetry_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                etype = entry.get('event_type')
                payload = entry.get('payload', {})
                if etype == 'prediction':
                    ts = datetime.fromisoformat(payload['prediction_for_timestamp'])
                    self.log_prediction(ts, payload['prediction'], payload.get('features'))
                    n_loaded += 1
                elif etype == 'measurement':
                    ts = datetime.fromisoformat(payload['measurement_timestamp'])
                    self.log_measurement(ts, payload['measured_value'])
        return n_loaded

    # ----------------------------------------------------------- diagnostics
    def check_drift(self) -> dict:
        """Compare paired predictions vs measurements; report drift status.

        Returns a dict with:
            drift_detected     : bool
            mean_error_pct     : float
            mean_bias_pct      : float (positive = overestimate)
            samples_evaluated  : int
            action             : str ('ok' | 'retrain_recommended' | 'investigate')
            reason             : human-readable explanation
        """
        paired = [p for p in self._pairs if p['measurement'] is not None]
        n = len(paired)

        if n == 0:
            return {
                'drift_detected': False,
                'samples_evaluated': 0,
                'action': 'no_data',
                'reason': 'No paired predictions/measurements yet. '
                          'This module activates when HRES 5 (real sensor data) is live.',
            }

        if n < self.min_samples:
            return {
                'drift_detected': False,
                'samples_evaluated': n,
                'action': 'collecting',
                'reason': f'Only {n} samples (need at least {self.min_samples}). '
                          'Continue collecting before drift evaluation.',
            }

        # Filter daytime values (predictions for very small loads are unreliable)
        valid = [p for p in paired if p['measurement'] > 10]
        errors_pct = [
            (p['prediction'] - p['measurement']) / max(p['measurement'], 1) * 100
            for p in valid
        ]
        abs_errors_pct = [abs(e) for e in errors_pct]

        mean_abs_error = float(np.mean(abs_errors_pct))
        mean_bias = float(np.mean(errors_pct))
        drift = mean_abs_error > self.threshold

        if drift:
            action = 'retrain_recommended'
            reason = (f'Mean absolute error {mean_abs_error:.1f}% exceeds threshold '
                      f'{self.threshold}%. Bias {mean_bias:+.1f}% '
                      f"({'overestimating' if mean_bias > 0 else 'underestimating'}).")
        else:
            action = 'ok'
            reason = (f'Mean absolute error {mean_abs_error:.1f}% within threshold '
                      f'{self.threshold}%. Model is healthy.')

        return {
            'drift_detected': drift,
            'mean_error_pct': mean_abs_error,
            'mean_bias_pct': mean_bias,
            'samples_evaluated': len(valid),
            'threshold_pct': self.threshold,
            'action': action,
            'reason': reason,
            'model_version': self.model_version,
        }

    def get_dataset_for_retraining(self) -> pd.DataFrame:
        """Return paired data as a DataFrame ready for retraining."""
        paired = [p for p in self._pairs if p['measurement'] is not None]
        rows = []
        for p in paired:
            row = dict(p['features'])
            row['target'] = p['measurement']
            row['timestamp'] = p['timestamp']
            rows.append(row)
        return pd.DataFrame(rows)


if __name__ == '__main__':
    # Smoke test: simulate drift detection
    corrector = AutoCorrector(model_version='rf_v0.2.0', retraining_threshold_pct=15.0,
                              minimum_samples=10)

    # Simulate a model that overestimates by 20% (drift!)
    from datetime import datetime, timedelta
    base = datetime(2026, 6, 15, 12, 0)
    for i in range(50):
        ts = base + timedelta(hours=i)
        true_value = 2500 + 500 * np.sin(i / 24 * 2 * np.pi)  # daily cycle
        predicted = true_value * 1.20  # 20% overestimate
        corrector.log_prediction(ts, predicted)
        corrector.log_measurement(ts, true_value)

    result = corrector.check_drift()
    print('=== Drift check result ===')
    for k, v in result.items():
        print(f'  {k}: {v}')
