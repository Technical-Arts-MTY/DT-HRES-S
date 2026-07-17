# 📊 Data — DT-HRES-S

## Folder structure

```
data/
├── raw/                            ← original, immutable source files
│   └── SolarDataofMexicanCities.xlsx
├── processed/                      ← cleaned, schema-normalized CSVs
│   ├── monterrey_tmy.csv           ← 8,737 hourly records × 22 columns
│   ├── campeche_tmy.csv
│   ├── mexico_city_tmy.csv
│   ├── san_ignacio_tmy.csv
│   └── cities_summary.csv          ← annual statistics, one row per city
└── metadata/
    ├── data_dictionary.md          ← full variable documentation
    └── sources.md                  ← data provenance & references
```

## Quick load (Python)

```python
import pandas as pd

# Load one city
df_mty = pd.read_csv('data/processed/monterrey_tmy.csv')

# Load all cities into a single dataframe
import glob
all_cities = pd.concat([pd.read_csv(f) for f in glob.glob('data/processed/*_tmy.csv')
                        if 'summary' not in f], ignore_index=True)

# Summary table
summary = pd.read_csv('data/processed/cities_summary.csv')
print(summary)
```

## Quick load (Google Colab — direct from GitHub)

```python
BASE = 'https://raw.githubusercontent.com/Aaron-Cuevas/DT-HRES-S/main/data/processed/'
df_mty = pd.read_csv(BASE + 'monterrey_tmy.csv')
```

## Why these four cities?

The four cities span Mexico's main climate zones, which is critical for training a digital twin that generalizes:

| Climate (Köppen) | Representative city | Implication for HRES |
|---|---|---|
| **BSh** semi-arid hot | Monterrey | Best wind resource (4.5 m/s avg), high temps stress PV |
| **Aw** tropical savanna | Campeche | High humidity → soiling/corrosion concerns |
| **Cwb** highland subtropical | Mexico City | High elevation → low air density, cool temps boost PV efficiency |
| **BWh** hot desert | San Ignacio | Highest GHI (2,155 kWh/m²/yr), lowest wind |

For the project's primary site **Ixil, Yucatán** (climate Aw), Campeche is the closest analog in the dataset.

## Data validation results

All four CSVs pass:
- ✅ No missing values
- ✅ Annual GHI within 1,500–2,300 kWh/m²/yr (Mexican range)
- ✅ Energy balance check: |GHI - (DNI·cos θ_z + DHI)| / GHI < 5% at midday
- ✅ Temperature range physically plausible (-5 to 50 °C)
- ✅ All 12 months represented, all 24 hours present

See `tests/test_data_quality.py` for the validation suite.

## Adding new data

To add a new city or implementation site:

1. Place the raw file in `data/raw/`
2. Add city metadata to `src/data_loader.py` `CITIES` dictionary
3. Run `python -m src.data_loader --process-all`
4. Update this README and `cities_summary.csv`
