# 📖 Data Dictionary — DT-HRES-S

## Source
- **File:** `data/raw/SolarDataofMexicanCities.xlsx`
- **Format:** Typical Meteorological Year (TMY) — similar to EnergyPlus EPW / TMY3
- **Resolution:** Hourly, 8,737 records (≈ 1 year)
- **Cities covered:** Monterrey, Campeche, Mexico City, San Ignacio

## Schema (processed CSVs)

| # | Column | Type | Units | Description | Use in DT |
|---|---|---|---|---|---|
| 1 | `city` | str | — | City name | Grouping/filter |
| 2 | `time_hr` | int | hour of year (0-8736) | Cumulative hour from Jan 1, 00:00 | Time index |
| 3 | `dry_bulb_C` | float | °C | Ambient dry-bulb air temperature | **PV temp correction**, NN input |
| 4 | `dew_point_C` | float | °C | Dew point temperature | Humidity calcs |
| 5 | `wet_bulb_C` | float | °C | Wet bulb temperature | Evap cooling |
| 6 | `sky_temp_C` | float | °C | Effective sky temperature | Radiative heat loss |
| 7 | `humidity_ratio` | float | kg_water/kg_dry_air | Specific humidity | Psychrometrics |
| 8 | `rel_humidity_pct` | float | % (0-100) | Relative humidity | Soiling, comfort |
| 9 | `wind_speed_ms` | float | m/s | Wind speed at 10 m height | **Wind turbine input**, NN input |
| 10 | `wind_dir_deg` | float | ° (0-360) | Wind direction (0=N, 90=E) | Turbine yaw |
| 11 | `atm_pressure_atm` | float | atm | Atmospheric pressure | Air density correction |
| 12 | `month` | int | 1-12 | Month of year | **NN input (cyclical)** |
| 13 | `hour` | int | 0-23 | Hour of day | **NN input (cyclical)** |
| 14 | `day_of_year` | int | 1-365 | Julian day | Solar geometry |
| 15 | `ghi_Wm2` | float | W/m² | **Global Horizontal Irradiance** | **PV input (key)** |
| 16 | `dni_proj_Wm2` | float | W/m² | DNI × cos(zenith) | Tracker systems |
| 17 | `dhi_Wm2` | float | W/m² | **Diffuse Horizontal Irradiance** | Tilted surface calcs |
| 18 | `latitude` | float | ° | City latitude | Solar geometry |
| 19 | `longitude` | float | ° | City longitude | Time zone |
| 20 | `elevation_m` | float | m | Elevation above sea level | Air density, AM |

## Key derived quantities (computed in `src/`)

| Quantity | Formula | Module |
|---|---|---|
| Direct Normal Irradiance | `DNI = DNI_proj / cos(θ_z)` | `pv_model.py` |
| Tilted irradiance (POA) | Hay-Davies / Perez model | `pv_model.py` |
| Cell temperature | `T_cell = T_amb + (NOCT-20)/800 × GHI` | `pv_model.py` |
| PV DC power | `P_pv = P_rated × (GHI/1000) × [1 + γ(T_cell - 25)]` | `pv_model.py` |
| Air density | `ρ = P/(R·T)` with elevation correction | `wind_model.py` |
| Wind power | Power curve interpolation | `wind_model.py` |
| Battery SoC | `SoC(t+1) = SoC(t) + η·P_in·Δt / E_max` | `battery_model.py` |

## Data quality notes

- **GHI vs DHI consistency:** for clear-sky midday hours, GHI ≈ DNI·cos(θ_z) + DHI. This identity is used in `tests/test_data_quality.py`.
- **Annual GHI sanity check:** Mexican cities should fall in **1,500–2,300 kWh/m²/yr**. All four cities are within this range ✅.
- **Missing values:** none in the four city sheets (8,737 complete records each).
- **Time convention:** Local Standard Time (no DST). Hour 0 = midnight.

## Coordinate system

- **Latitude / Longitude:** WGS84 decimal degrees
- **Elevation:** meters above mean sea level (MSL)

## Recommended additions for DT-HRES-S

To complete the digital twin, the following datasets should be added by Task 3.2 (Samuel Canul, Data Lead):

1. **Demand profiles** for typical indigenous community loads (lighting, refrigeration, water pumping, small appliances)
2. **Technical specs** for representative PV panels, wind turbines, and Li-ion batteries available in the Mexican market
3. **Cost data** in MXN for techno-economic analysis (LCOE, NPC)
4. **Ixil-specific data** (Yucatán) — primary implementation site
5. **Cienega de González data** (Nuevo León) — secondary site via NGO Escalada Libre México

## References

- ASHRAE Handbook of Fundamentals (2021), Ch. 14 — Climatic Design Information
- EnergyPlus Weather File Format Documentation (EPW)
- Wilcox, S., & Marion, W. (2008). *Users Manual for TMY3 Data Sets*. NREL/TP-581-43156
