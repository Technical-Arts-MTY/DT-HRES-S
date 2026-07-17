"""
telemetry.py — Continuous logging and tracking
================================================
Implements the 4D methodology Universe principles of **Telemetry** and
**Tracking**: every prediction, every input, every model version is logged
with full provenance.

The log format is JSONL (one JSON object per line) for:
  - Easy streaming and tailing
  - Direct ingestion to Pandas, Spark, or time-series databases
  - Human-readable inspection

Usage:
    from src.telemetry import TelemetryLogger

    logger = TelemetryLogger(session_id='ixil_test_001')
    logger.log_prediction(
        timestamp=datetime.now(),
        features={'ghi_Wm2': 850, 'dry_bulb_C': 32},
        prediction=3247.5,
        model_version='rf_v0.2.0',
        source_metadata=source.metadata(),
    )
    logger.close()
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid


class TelemetryLogger:
    """Append-only structured logger for digital twin operations.

    Each log entry is a JSON object with:
      - timestamp (UTC ISO 8601)
      - session_id (unique per twin session)
      - event_type ('prediction', 'measurement', 'drift_alert', 'model_load', ...)
      - payload (event-specific data)

    Logs are written to JSONL files under `results/telemetry/`.
    """

    def __init__(self, session_id: str | None = None,
                 log_dir: str | Path | None = None):
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"

        if log_dir is None:
            log_dir = Path(__file__).resolve().parent.parent / 'results' / 'telemetry'
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        date_tag = datetime.now(timezone.utc).strftime('%Y%m%d')
        self.log_path = self.log_dir / f'telemetry_{date_tag}_{self.session_id}.jsonl'
        self._file = open(self.log_path, 'a', encoding='utf-8')

        self._write_event('session_start', {
            'session_id': self.session_id,
            'log_path': str(self.log_path),
        })

    # ------------------------------------------------------------------ core
    def _write_event(self, event_type: str, payload: dict) -> None:
        entry = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'session_id': self.session_id,
            'event_type': event_type,
            'payload': payload,
        }
        self._file.write(json.dumps(entry, default=str) + '\n')
        self._file.flush()  # ensure durability

    # -------------------------------------------------------------- specific
    def log_prediction(self,
                       timestamp: datetime,
                       features: dict,
                       prediction: float,
                       model_version: str = 'unknown',
                       uncertainty_pct: float | None = None,
                       source_metadata: dict | None = None) -> None:
        """Log one ML prediction event.

        Parameters
        ----------
        timestamp : when the prediction is FOR (not when it was made)
        features : input dict (e.g., from DataSource.read())
        prediction : the model output in physical units (W, kWh, etc.)
        model_version : identifier of the model used
        uncertainty_pct : optional uncertainty estimate
        source_metadata : output of DataSource.metadata() for provenance
        """
        self._write_event('prediction', {
            'prediction_for_timestamp': timestamp.isoformat(),
            'features': features,
            'prediction': prediction,
            'model_version': model_version,
            'uncertainty_pct': uncertainty_pct,
            'source_metadata': source_metadata,
        })

    def log_measurement(self,
                        timestamp: datetime,
                        measured_value: float,
                        sensor_id: str,
                        units: str = 'W') -> None:
        """Log a real measurement from a physical sensor (HRES 5+)."""
        self._write_event('measurement', {
            'measurement_timestamp': timestamp.isoformat(),
            'measured_value': measured_value,
            'sensor_id': sensor_id,
            'units': units,
        })

    def log_drift_alert(self,
                        mean_error_pct: float,
                        samples_evaluated: int,
                        threshold_pct: float,
                        action: str) -> None:
        """Log a drift detection alert from auto_correction.py."""
        self._write_event('drift_alert', {
            'mean_error_pct': mean_error_pct,
            'samples_evaluated': samples_evaluated,
            'threshold_pct': threshold_pct,
            'action': action,
        })

    def log_model_load(self,
                       model_version: str,
                       model_path: str,
                       n_features: int,
                       training_metrics: dict) -> None:
        """Log when a model is loaded into the twin."""
        self._write_event('model_load', {
            'model_version': model_version,
            'model_path': model_path,
            'n_features': n_features,
            'training_metrics': training_metrics,
        })

    def log_custom(self, event_type: str, payload: dict) -> None:
        """Escape hatch for arbitrary events."""
        self._write_event(event_type, payload)

    # ----------------------------------------------------------------- close
    def close(self) -> None:
        self._write_event('session_end', {'session_id': self.session_id})
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# -----------------------------------------------------------------------------
# Convenience: read back JSONL logs into a DataFrame
# -----------------------------------------------------------------------------
def read_log(log_path: str | Path):
    """Load a telemetry JSONL log into a pandas DataFrame for analysis."""
    import pandas as pd
    records = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.json_normalize(records)


if __name__ == '__main__':
    # Smoke test
    with TelemetryLogger(session_id='smoke_test') as tlog:
        tlog.log_prediction(
            timestamp=datetime.now(),
            features={'ghi_Wm2': 850, 'dry_bulb_C': 32, 'wind_speed_ms': 5.5},
            prediction=3247.5,
            model_version='rf_v0.2.0_smoketest',
            uncertainty_pct=5.4,
            source_metadata={'source_type': 'TMY_file', 'city': 'Campeche'},
        )
        tlog.log_drift_alert(
            mean_error_pct=18.5,
            samples_evaluated=150,
            threshold_pct=15.0,
            action='retrain_recommended',
        )
    print(f"✓ Smoke test wrote to: {tlog.log_path}")
