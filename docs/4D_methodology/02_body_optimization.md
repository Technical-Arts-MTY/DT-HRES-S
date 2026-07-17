# 🥚 2D — The Body: What do we optimize and for whom?

> **Methodology question**: In this process, what do we want to optimize and in what form? Speak in %, for who (x), what will say the output for x (in y time z machine stops).

## 🎯 Who is the user (x)?

The DT-HRES-S has **three distinct user personas**, each with different optimization priorities:

### Persona 1: The community member (Ixil resident)

> "I just want to know: will I have electricity when I turn on the light?"

**What they value:** Reliability (no blackouts), simplicity, low cost.
**Output language:** Percentages, MXN, intuitive plots.
**Key metric:** **Coverage %** = (energy supplied / energy demanded) × 100

**Example output:**
> "With 6 kWp of solar panels and 15 kWh battery, you will have electricity **96% of the time**. Cost: **MXN 280,000**. Estimated lifetime: **20 years**."

### Persona 2: The NGO project manager (Escalada Libre, Fundación)

> "I have a budget of $300,000 MXN. What's the best system I can deploy with that?"

**What they value:** Maximum impact per peso, comparability between communities.
**Output language:** Cost-benefit ratios, scenario comparisons.
**Key metric:** **LCOE** (Levelized Cost of Energy) = total lifetime cost / total energy delivered, in MXN/kWh.

**Example output:**
> "Under your $300,000 budget, the optimal mix is 4 kWp PV + 10 kWh battery + 1 small wind turbine. **LCOE: 3.20 MXN/kWh**, **coverage: 92%**, **renewable fraction: 88%**."

### Persona 3: The technical evaluator (Dr. Rasikh, academic reviewers)

> "Does the model meet engineering standards? Is the methodology defensible?"

**What they value:** Statistical rigor, reproducibility, citation-quality metrics.
**Output language:** RMSE, R², CV-RMSE, confidence intervals.
**Key metrics:** ASHRAE Guideline 14 compliance.

**Example output:**
> "Random Forest model achieves CV-RMSE = 5.4% (below ASHRAE threshold of 10%), R² = 0.99 on leave-one-city-out cross-validation. MBE = -0.7%, indicating slight conservative bias."

## 🎯 What do we optimize?

The system has **multiple objectives that conflict**. There's no single "best" answer — there's a **Pareto frontier**.

### Primary objectives (typically conflicting)

| Objective | Symbol | Unit | Direction |
|---|---|---|---|
| Coverage | C | % | maximize |
| Cost | LCOE | MXN/kWh | minimize |
| Renewable fraction | RF | % | maximize |
| Battery cycle life | N_cycles | cycles/year | minimize |

### Secondary objectives (constraints, not optimized)

- LPSP (Loss of Power Supply Probability) < 5% (community minimum requirement)
- LOLE (Loss of Load Expectation) < 100 hours/year
- Total CO₂ emissions over 20-year lifetime < threshold
- Local manufacturing content > 30% (where feasible)

## 📐 How we express objectives mathematically

### Coverage / LPSP

```
LPSP = Σ E_unmet(t) / Σ E_demand(t)
Coverage = 1 - LPSP
```

**Status in code:** ✅ Computed in `src/battery_model.py` → `reliability_metrics()`

### LCOE (Levelized Cost of Energy)

```
LCOE = (CapEx + Σ OpEx(t) / (1+r)^t) / Σ E_delivered(t) / (1+r)^t
```

Where:
- CapEx = capital expenditure (panels, turbine, battery, inverter, installation)
- OpEx = operating expenses (maintenance, replacements)
- r = discount rate (typically 7-10% for rural Mexico)
- t = year of project lifetime (20 years typical)

**Status in code:** 🔴 Not implemented yet. Pending Task 3.4 (Carlos).

### Renewable Fraction

```
RF = (E_pv + E_wind - E_curtailed) / E_demand_met
```

**Status in code:** ✅ Computed in `src/hres_simulator.py` → `summarize()`

## 🔄 The optimization loop

When the Colab interface is ready, the flow will be:

```
1. User inputs community parameters (houses, school, clinic, budget)
                                ↓
2. Synthesizer builds demand profile for that community
                                ↓
3. Optimizer sweeps configurations:
   for PV_kWp in [2, 4, 6, 8, 10, 12]:
     for battery_kWh in [5, 10, 15, 20, 25]:
       for wind_kW in [0, 1, 3, 5]:
                                ↓
4. ML model predicts performance for each combination (milliseconds)
                                ↓
5. Compute objectives: coverage, LCOE, RF
                                ↓
6. Filter feasible (LPSP < 5%, within budget)
                                ↓
7. Show Pareto frontier: "minimum cost for each coverage level"
                                ↓
8. User picks their preferred trade-off
```

Without the ML this would take minutes. With the ML, the entire sweep happens in **seconds**, enabling interactive UI.

## 🎨 Sketch of the final interface

The community-facing notebook (`notebooks/12_community_interface.ipynb`) will look like:

```
┌──────────────────────────────────────────────────────────────────┐
│  DT-HRES-S Community Simulator (es / maya)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📍 Comunidad: [Ixil ▼]    🏘 Número de casas: [≈≈■≈≈] 20         │
│                                                                  │
│  Servicios:                                                      │
│    ☑ Iluminación básica       ☑ Refrigeración (cocina/vacunas)   │
│    ☑ Escuela                  ☐ Clínica de salud                 │
│    ☐ Bomba de agua            ☐ Centro comunitario               │
│                                                                  │
│  💰 Presupuesto disponible: $[≈≈■≈≈≈≈≈] 250,000 MXN              │
│                                                                  │
│  [ Calcular sistema óptimo ]                                     │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 Resultados:                                                  │
│                                                                  │
│  ★ Tu sistema recomendado:                                       │
│     • 6 kWp de paneles solares (15 paneles de 400 W)            │
│     • 1 aerogenerador de 3 kW                                    │
│     • 15 kWh de batería de litio                                 │
│                                                                  │
│  ✓ Cobertura: 95% del tiempo tendrás electricidad                │
│  ✓ Costo total: $245,000 MXN                                     │
│  ✓ Vida útil estimada: 20 años                                   │
│  ✓ 100% renovable (sin diésel)                                   │
│                                                                  │
│  📈 [gráfico: producción típica de un día]                       │
│  📈 [gráfico: cobertura a lo largo del año]                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Status:** Sketch only. Implementation pending (Task 3.1, Aaron + Arturo with ipywidgets).

## 📊 Example outputs for each persona

### For the community member
```
✓ Tendrás luz el 96% del tiempo
✓ La inversión inicial es de 280 mil pesos
✓ Sin pagos mensuales después de la instalación
✓ El sistema dura 20 años
```

### For the NGO manager
```
Configuration   | Coverage | LCOE      | RF   | Verdict
================|==========|===========|======|========
4 kWp PV only   | 78%      | 3.80 $/kWh| 78%  | ❌ low coverage
6 kWp + 15 kWh  | 95%      | 3.20 $/kWh| 92%  | ⭐ RECOMMENDED
8 kWp + 20 kWh  | 98%      | 3.55 $/kWh| 95%  | ⚠ overbuilt
```

### For the technical evaluator
```
Cross-validation results (leave-one-city-out):
  Random Forest:   R² = 0.991 ± 0.003,  CV-RMSE = 5.4% ± 0.8%
  Decision Tree:   R² = 0.985 ± 0.005,  CV-RMSE = 8.5% ± 1.2%
  Neural Network:  R² = 0.987 ± 0.004,  CV-RMSE = 7.9% ± 1.5%
  SVM (RBF):       R² = 0.962 ± 0.012,  CV-RMSE = 22.8% ± 3.1%

✓ All models below ASHRAE Guideline 14 threshold (CV-RMSE < 30%)
✓ Random Forest selected as production model
```

---

🟡 **Status**: Concept clear, interface sketch ready, implementation pending. Carlos + Aaron + Arturo are responsible for completing this dimension.
