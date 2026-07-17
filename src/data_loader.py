"""
data_loader.py — Unified TMY data loading for DT-HRES-S
========================================================
Loads cleaned hourly meteorological data for the 4 Mexican cities
(Monterrey, Campeche, Mexico City, San Ignacio) and exposes a single
interface for the simulation engine and ML models.

Usage:
    from src.data_loader import load_city, load_all_cities, CITIES
    df = load_city('Monterrey')
    df_all = load_all_cities()
"""
from pathlib import Path
import pandas as pd

# ---------------------------------------------------------------------------
# City metadata (single source of truth)
# ---------------------------------------------------------------------------
CITIES = {
    'Monterrey':   {'lat': 25.6866, 'lon': -100.3161, 'elevation_m': 540,
                    'state': 'Nuevo León',          'climate_koppen': 'BSh',
                    'climate_desc': 'Semi-arid hot'},
    'Campeche':    {'lat': 19.8301, 'lon': -90.5349,  'elevation_m': 10,
                    'state': 'Campeche',            'climate_koppen': 'Aw',
                    'climate_desc': 'Tropical savanna'},
    'Mexico City': {'lat': 19.4326, 'lon': -99.1332,  'elevation_m': 2240,
                    'state': 'CDMX',                'climate_koppen': 'Cwb',
                    'climate_desc': 'Subtropical highland'},
    'San Ignacio': {'lat': 27.2833, 'lon': -112.9,    'elevation_m': 80,
                    'state': 'Baja California Sur', 'climate_koppen': 'BWh',
                    'climate_desc': 'Hot desert'},
}

# Default location of processed CSVs (relative to repo root)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'processed'


def _city_to_filename(city: str) -> str:
    return city.lower().replace(' ', '_') + '_tmy.csv'


def load_city(city: str, data_dir: Path | str | None = None) -> pd.DataFrame:
    """Load processed TMY data for a single city.

    Parameters
    ----------
    city : str
        Name as in CITIES dict (e.g., 'Monterrey').
    data_dir : optional path
        Directory containing the processed CSVs. Defaults to ../data/processed.

    Returns
    -------
    DataFrame with 22 columns and 8,737 hourly records.
    """
    if city not in CITIES:
        raise ValueError(f"Unknown city '{city}'. Available: {list(CITIES.keys())}")

    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    fp = data_dir / _city_to_filename(city)
    if not fp.exists():
        raise FileNotFoundError(
            f"Processed CSV not found: {fp}\n"
            f"Run `python -m src.data_loader --process-all` to regenerate."
        )

    df = pd.read_csv(fp)
    # Build a proper datetime index (assuming year is non-leap for TMY convention)
    df['datetime'] = pd.to_datetime('2023-01-01') + pd.to_timedelta(df['time_hr'], unit='h')
    return df


def load_all_cities(data_dir: Path | str | None = None) -> pd.DataFrame:
    """Concatenate all four cities into a single tidy DataFrame."""
    frames = [load_city(c, data_dir) for c in CITIES]
    return pd.concat(frames, ignore_index=True)


def get_summary(data_dir: Path | str | None = None) -> pd.DataFrame:
    """Return the city-level summary table (annual statistics)."""
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    return pd.read_csv(data_dir / 'cities_summary.csv')


# ---------------------------------------------------------------------------
# Pre-processing: convert raw Excel → cleaned CSVs
# ---------------------------------------------------------------------------
def process_raw(raw_xlsx: Path | str, out_dir: Path | str) -> None:
    """Convert the raw multi-sheet Excel into 4 normalized CSVs.

    Handles inconsistent column layouts across sheets by locating
    GHI/DNI/DHI relative to the 'Month'/'Hour'/'Day' headers.
    """
    import openpyxl

    raw_xlsx, out_dir = Path(raw_xlsx), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for city, info in CITIES.items():
        wb = openpyxl.load_workbook(raw_xlsx, data_only=True)
        headers = [str(c.value).strip() if c.value else 'None' for c in wb[city][1]]
        wb.close()

        df_raw = pd.read_excel(raw_xlsx, sheet_name=city, header=None, skiprows=1)
        day_idx = headers.index('Day')

        out = pd.DataFrame({
            'time_hr':          df_raw.iloc[:, 0],
            'dry_bulb_C':       df_raw.iloc[:, 1],
            'dew_point_C':      df_raw.iloc[:, 2],
            'wet_bulb_C':       df_raw.iloc[:, 3],
            'sky_temp_C':       df_raw.iloc[:, 4],
            'humidity_ratio':   df_raw.iloc[:, 5],
            'rel_humidity_pct': df_raw.iloc[:, 6],
            'wind_speed_ms':    df_raw.iloc[:, 7],
            'wind_dir_deg':     df_raw.iloc[:, 8],
            'atm_pressure_atm': df_raw.iloc[:, 9],
            'month':            df_raw.iloc[:, headers.index('Month')],
            'hour':             df_raw.iloc[:, headers.index('Hour')],
            'day_of_year':      df_raw.iloc[:, day_idx],
            'ghi_Wm2':          df_raw.iloc[:, day_idx + 1],
            'dni_proj_Wm2':     df_raw.iloc[:, day_idx + 2],
            'dhi_Wm2':          df_raw.iloc[:, day_idx + 3],
        })
        out.insert(0, 'city', city)
        out['latitude'] = info['lat']
        out['longitude'] = info['lon']
        out['elevation_m'] = info['elevation_m']

        fp = out_dir / _city_to_filename(city)
        out.to_csv(fp, index=False)
        print(f"  ✓ {city:15s} → {fp.name}")

        summary_rows.append({
            'city': city,
            'state': info['state'],
            'climate_koppen': info['climate_koppen'],
            'latitude': info['lat'],
            'longitude': info['lon'],
            'elevation_m': info['elevation_m'],
            'GHI_kWh_m2_yr': round(out['ghi_Wm2'].sum() / 1000, 0),
            'DHI_kWh_m2_yr': round(out['dhi_Wm2'].sum() / 1000, 0),
            'T_avg_C': round(out['dry_bulb_C'].mean(), 1),
            'T_min_C': round(out['dry_bulb_C'].min(), 1),
            'T_max_C': round(out['dry_bulb_C'].max(), 1),
            'wind_avg_ms': round(out['wind_speed_ms'].mean(), 1),
            'wind_max_ms': round(out['wind_speed_ms'].max(), 1),
            'RH_avg_pct': round(out['rel_humidity_pct'].mean(), 1),
            'records': len(out),
        })

    pd.DataFrame(summary_rows).to_csv(out_dir / 'cities_summary.csv', index=False)
    print(f"  ✓ Summary → cities_summary.csv")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description="DT-HRES-S data loader CLI")
    p.add_argument('--process-all', action='store_true', help="Regenerate processed CSVs from raw XLSX")
    p.add_argument('--raw',  default='data/raw/SolarDataofMexicanCities.xlsx')
    p.add_argument('--out',  default='data/processed')
    args = p.parse_args()

    if args.process_all:
        print(f"Processing {args.raw} → {args.out}/ ...")
        process_raw(args.raw, args.out)
        print("Done.")
    else:
        for c in CITIES:
            df = load_city(c)
            print(f"{c:15s}: {len(df):,} rows × {len(df.columns)} cols")
