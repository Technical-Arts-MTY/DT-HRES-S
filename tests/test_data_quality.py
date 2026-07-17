"""tests/test_data_quality.py — Data validation suite

Run with: pytest tests/
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from src.data_loader import load_city, CITIES


def test_all_cities_load():
    """Every declared city must have a processable CSV."""
    for city in CITIES:
        df = load_city(city)
        assert len(df) == 8737, f"{city}: expected 8737 rows, got {len(df)}"


def test_no_missing_critical_values():
    """No NaN in the physics-critical columns."""
    critical = ['ghi_Wm2', 'dhi_Wm2', 'dry_bulb_C', 'wind_speed_ms',
                'month', 'hour', 'day_of_year']
    for city in CITIES:
        df = load_city(city)
        for col in critical:
            assert df[col].notna().all(), f"{city}.{col} has NaN values"


def test_annual_ghi_realistic():
    """Annual GHI for Mexican cities must be in 1,200–2,500 kWh/m²/yr."""
    for city in CITIES:
        df = load_city(city)
        ghi = df['ghi_Wm2'].sum() / 1000
        assert 1200 <= ghi <= 2500, f"{city}: GHI={ghi:.0f} outside [1200, 2500]"


def test_temperature_plausible():
    """Dry-bulb temperature within plausible Mexican range."""
    for city in CITIES:
        df = load_city(city)
        assert -10 <= df['dry_bulb_C'].min() <= 15, f"{city}: T_min too cold"
        assert 30 <= df['dry_bulb_C'].max() <= 55, f"{city}: T_max out of range"


def test_wind_speed_non_negative():
    """Wind speed must be ≥ 0."""
    for city in CITIES:
        df = load_city(city)
        assert (df['wind_speed_ms'] >= 0).all(), f"{city}: negative wind speed"


def test_hour_month_day_complete():
    """All 24 hours and all 12 months present."""
    for city in CITIES:
        df = load_city(city)
        assert set(df['hour'].unique()) == set(range(24)), f"{city}: hours incomplete"
        assert set(df['month'].unique()) == set(range(1, 13)), f"{city}: months incomplete"


def test_ghi_zero_at_night():
    """GHI must be 0 between local hours 22 and 4."""
    for city in CITIES:
        df = load_city(city)
        night = df[df['hour'].isin([23, 0, 1, 2, 3])]
        # Allow tiny numerical noise
        assert (night['ghi_Wm2'] < 5).all(), f"{city}: non-zero GHI at night"


def test_irradiance_components_consistent():
    """Energy balance: GHI ≥ DHI almost always (allow tiny rounding)."""
    for city in CITIES:
        df = load_city(city)
        # GHI must be ≥ DHI on average
        assert df['ghi_Wm2'].mean() >= df['dhi_Wm2'].mean() * 0.9


if __name__ == '__main__':
    # Quick CLI mode without pytest
    fns = [test_all_cities_load, test_no_missing_critical_values,
           test_annual_ghi_realistic, test_temperature_plausible,
           test_wind_speed_non_negative, test_hour_month_day_complete,
           test_ghi_zero_at_night, test_irradiance_components_consistent]
    for fn in fns:
        try:
            fn()
            print(f'  ✅ {fn.__name__}')
        except AssertionError as e:
            print(f'  ❌ {fn.__name__}: {e}')
