"""
sensors.py — 3D Mind: Data source abstraction layer
=====================================================
Implements the 4D methodology principle of **Modularity**: the simulator
should not care whether weather data comes from a TMY file, NASA POWER
API, or a real pyranometer.

This module defines a common interface `DataSource` and three concrete
implementations:
  - TMYFileSource    : reads processed CSVs (current default)
  - NASAPowerSource  : fetches from NASA POWER API (any lat/lon)
  - PiranometerSource: real-time sensor reading (HRES 5, pending hardware)

Usage:
    source = TMYFileSource('data/processed/campeche_tmy.csv', 'Campeche')
    reading = source.read(datetime(2026, 6, 15, 12, 0))
    metadata = source.metadata()
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


# -----------------------------------------------------------------------------
# Abstract base class — every data source must implement these two methods
# -----------------------------------------------------------------------------
class DataSource(ABC):
    """Abstract interface for any meteorological data source.

    The DT-HRES-S twin reads weather through this interface. Concrete
    implementations decide where data comes from.
    """

    @abstractmethod
    def read(self, timestamp: datetime) -> dict:
        """Return one reading for a given timestamp.

        Required keys in the returned dict:
            ghi_Wm2          : Global Horizontal Irradiance (W/m²)
            dhi_Wm2          : Diffuse Horizontal Irradiance (W/m²)
            dni_proj_Wm2     : DNI projected on horizontal (W/m²)
            dry_bulb_C       : Ambient temperature (°C)
            rel_humidity_pct : Relative humidity (%)
            wind_speed_ms    : Wind speed at measurement height (m/s)
            timestamp        : echo of input timestamp (UTC)
        """

    @abstractmethod
    def metadata(self) -> dict:
        """Return provenance and calibration info for tracking.

        Required keys:
            source_type      : 'TMY_file' | 'NASA_POWER_API' | 'physical_sensor'
            uncertainty_ghi_pct : nominal uncertainty in GHI (%)
            calibration_date : last calibration date (or 'N/A')
            sensor_model     : sensor model/identifier
        """


# -----------------------------------------------------------------------------
# Tier 1 — TMY file (synthetic data, what we use today)
# -----------------------------------------------------------------------------
class TMYFileSource(DataSource):
    """Reads processed Typical Meteorological Year CSVs.

    This is the default data source for v0.2.0. Each city has 8,737 hourly
    records derived from `SolarDataofMexicanCities.xlsx`.
    """

    def __init__(self, csv_path: str | Path, city: str = "Unknown"):
        self.csv_path = Path(csv_path)
        self.city = city
        if not self.csv_path.exists():
            raise FileNotFoundError(f"TMY file not found: {self.csv_path}")
        self.df = pd.read_csv(self.csv_path)
        # Index by (month, day_of_year, hour) for fast lookup
        self._index = self.df.set_index(['month', 'day_of_year', 'hour'])

    def read(self, timestamp: datetime) -> dict:
        """Look up the TMY record matching the timestamp's (month, day, hour).

        Year is ignored since TMY is climatology, not actual history.
        """
        key = (timestamp.month, timestamp.timetuple().tm_yday, timestamp.hour)
        try:
            row = self._index.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
        except KeyError:
            raise KeyError(f"No TMY record for {timestamp} (key={key})")

        return {
            'ghi_Wm2':          float(row['ghi_Wm2']),
            'dhi_Wm2':          float(row['dhi_Wm2']),
            'dni_proj_Wm2':     float(row['dni_proj_Wm2']),
            'dry_bulb_C':       float(row['dry_bulb_C']),
            'rel_humidity_pct': float(row['rel_humidity_pct']),
            'wind_speed_ms':    float(row['wind_speed_ms']),
            'timestamp':        timestamp.isoformat(),
        }

    def metadata(self) -> dict:
        return {
            'source_type':         'TMY_file',
            'city':                self.city,
            'csv_path':            str(self.csv_path),
            'records_available':   len(self.df),
            'uncertainty_ghi_pct': 5.0,   # ASHRAE typical for TMY
            'uncertainty_temp_C':  1.0,
            'uncertainty_wind_pct':10.0,
            'calibration_date':    'N/A — synthetic TMY',
            'sensor_model':        'N/A',
            'reading_timestamp':   datetime.now(timezone.utc).isoformat(),
        }


# -----------------------------------------------------------------------------
# Tier 2 — NASA POWER API (real satellite-derived data, any location)
# -----------------------------------------------------------------------------
class NASAPowerSource(DataSource):
    """Fetches meteorological data from NASA POWER API.

    NASA POWER provides satellite-derived hourly meteorological data
    for any latitude/longitude worldwide, free, no authentication required.

    API documentation: https://power.larc.nasa.gov/docs/services/api/

    This source is the **bridge from TMY (Tier 1) to real sensors (Tier 3)**:
    it provides location-specific data for Ixil without waiting for field
    instrumentation.

    Note: Implementation pending Task 3.2 (Samuel Canul). The skeleton below
    shows the expected interface.
    """

    POWER_API_URL = (
        "https://power.larc.nasa.gov/api/temporal/hourly/point"
    )

    def __init__(self, lat: float, lon: float,
                 start_date: str = "20200101", end_date: str = "20201231",
                 cache_path: str | Path | None = None):
        self.lat = lat
        self.lon = lon
        self.start_date = start_date
        self.end_date = end_date
        self.cache_path = Path(cache_path) if cache_path else None
        self._cache_df = None

    def fetch_year(self) -> pd.DataFrame:
        """Download one year of hourly data from NASA POWER.

        Returns a DataFrame with the same schema as the processed TMY CSVs.
        Cached to disk if cache_path is provided.
        """
        # Pending implementation — Samuel Canul, Task 3.2
        # Pseudocode:
        # 1. Build URL with parameters: ALLSKY_SFC_SW_DWN (GHI), T2M (temp),
        #    WS10M (wind speed), RH2M (rel humidity), DIFF (DHI)
        # 2. requests.get(URL)
        # 3. Parse JSON response
        # 4. Convert to DataFrame matching our schema
        # 5. Cache to self.cache_path
        # 6. Return DataFrame
        raise NotImplementedError(
            "NASAPowerSource.fetch_year() pending Task 3.2 — Samuel Canul.\n"
            "See https://power.larc.nasa.gov/docs/services/api/temporal/hourly/"
        )

    def read(self, timestamp: datetime) -> dict:
        if self._cache_df is None:
            self._cache_df = self.fetch_year()
        # Lookup logic similar to TMYFileSource
        raise NotImplementedError("Pending implementation")

    def metadata(self) -> dict:
        return {
            'source_type':         'NASA_POWER_API',
            'lat':                 self.lat,
            'lon':                 self.lon,
            'date_range':          f"{self.start_date}-{self.end_date}",
            'uncertainty_ghi_pct': 8.0,   # satellite-derived, typical
            'uncertainty_temp_C':  1.5,
            'uncertainty_wind_pct':15.0,  # known wind underestimate
            'calibration_date':    'Auto (satellite)',
            'sensor_model':        'Satellite-derived (MERRA-2)',
            'api_url':             self.POWER_API_URL,
            'reading_timestamp':   datetime.now(timezone.utc).isoformat(),
        }


# -----------------------------------------------------------------------------
# Tier 3 — Physical sensors (HRES 5, pending field deployment)
# -----------------------------------------------------------------------------
class PiranometerSource(DataSource):
    """Real-time reading from a physical weather station in Ixil.

    Activates when HRES 5 is reached (sensor hardware deployed in field).
    Likely communication protocol: Modbus RTU over RS-485, or MQTT over LTE.

    This skeleton documents the expected interface. Implementation pending
    hardware procurement and field installation.
    """

    def __init__(self, device_id: str, port: str = "/dev/ttyUSB0",
                 baudrate: int = 9600, sensor_model: str = "Kipp & Zonen CMP10"):
        self.device_id = device_id
        self.port = port
        self.baudrate = baudrate
        self.sensor_model = sensor_model
        # Future: self.connection = serial.Serial(port, baudrate)

    def read(self, timestamp: datetime = None) -> dict:
        """Read current values from the physical station.

        The timestamp argument is ignored — physical sensors read NOW.
        Stored for trace compatibility with TMY-based sources.
        """
        # Pending implementation — José Llashag (ML Systems & Deployment)
        # Pseudocode:
        # 1. Issue Modbus read request to sensor
        # 2. Parse response bytes into engineering units
        # 3. Apply calibration corrections
        # 4. Return standardized dict
        raise NotImplementedError(
            "PiranometerSource pending HRES 5 — field deployment of sensors.\n"
            "Owner: José Llashag (ML Systems & Deployment Lead)."
        )

    def metadata(self) -> dict:
        return {
            'source_type':         'physical_sensor',
            'device_id':           self.device_id,
            'port':                self.port,
            'sensor_model':        self.sensor_model,
            'uncertainty_ghi_pct': 2.0,   # Class A pyranometer
            'uncertainty_temp_C':  0.2,
            'uncertainty_wind_pct': 3.0,  # cup anemometer
            'calibration_date':    '2026-01-15',  # placeholder
            'next_calibration_due': '2027-01-15',
            'reading_timestamp':   datetime.now(timezone.utc).isoformat(),
        }


# -----------------------------------------------------------------------------
# Convenience factory
# -----------------------------------------------------------------------------
def make_source(kind: str, **kwargs) -> DataSource:
    """Factory to create a DataSource by kind name.

    Examples:
        source = make_source('tmy', csv_path='data/processed/campeche_tmy.csv',
                             city='Campeche')
        source = make_source('nasa', lat=21.12, lon=-88.73)
    """
    kind = kind.lower()
    if kind in ('tmy', 'tmy_file', 'file'):
        return TMYFileSource(**kwargs)
    if kind in ('nasa', 'nasa_power', 'api'):
        return NASAPowerSource(**kwargs)
    if kind in ('pyranometer', 'sensor', 'physical'):
        return PiranometerSource(**kwargs)
    raise ValueError(f"Unknown source kind: {kind}. "
                     "Use 'tmy', 'nasa', or 'pyranometer'.")


if __name__ == '__main__':
    # Smoke test: read one hour from Campeche TMY
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    source = TMYFileSource(
        csv_path=repo_root / 'data' / 'processed' / 'campeche_tmy.csv',
        city='Campeche'
    )
    print("=== TMY File Source ===")
    print("Metadata:", source.metadata())
    print()
    reading = source.read(datetime(2026, 6, 15, 13, 0))  # June 15, 1pm
    print("Reading at 2026-06-15 13:00:")
    for k, v in reading.items():
        print(f"  {k}: {v}")
