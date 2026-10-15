# HydroLoop | هايدرو لوب — integrated engineering simulation

HydroLoop (EcoFlow Algae Façade) turns AC condensate into the make-up water of a closed-loop
microalgae façade panel and sends the surplus, by gravity, to an evaporative pad in front of the
AC condenser. This tool simulates the whole chain in **one coupled hourly model**:

**Water Loop · Bio Loop · Carbon Loop · Oxygen production · Energy Loop · Cooling Loop · Economic Loop**

It is a **decision tool, not a marketing model**. It reports *when the idea works, when it weakens
and when it fails*. All results are **Simulated / Estimated / Subject to Field Validation**.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py          # opens the dashboard in the browser
python -m pytest -q           # 31 unit / edge-case tests
python tools/build_sources.py # regenerates sources.json after editing the ledger
```

Python ≥ 3.10. `psychrolib` is optional — a vendored copy of PsychroLib 2.5.0 (MIT licence,
ASHRAE Fundamentals equations) in `vendor/` is used automatically.

### Climate data
* **Built-in (default):** NOAA 1991-2020 normals for Jeddah + ASHRAE design-day profile + FAO-56 /
  Duffie-Beckman solar derivation. Works offline.
* **NASA POWER hourly:** choose it in the sidebar; the app downloads the year for 21.49 N, 39.19 E
  and caches it in `data/`. Needs internet on your machine.
* **Your CSV:** columns `month,day,hour,T,RH,GHI[,DHI,P]` (8760 rows).

### Condensate modes
* **Measured Mode** (highest confidence): enter the L/h you measured during the 3-day collection test.
* **Psychrometric Mode:** coil inlet/outlet humidity ratios (ASHRAE) × dry-air flow × runtime.

## Files

| File | Role |
|---|---|
| `app.py` | Streamlit UI: Executive & Sustainability dashboards, 13 tabs, exports |
| `simulation.py` | Hourly orchestrator coupling all loops; daily / monthly / annual sums |
| `climate_model.py` | Jeddah climate, solar on the façade, NASA POWER / CSV loaders |
| `psychrometrics.py` | ASHRAE psychrometrics via PsychroLib |
| `hvac_model.py` | AC coil condensate, runtime, condenser pre-cooling, COP and savings |
| `water_balance.py` | Clean-tank mass balance with overflow and spill |
| `overflow_hydraulics.py` | Gravity line: ρgh, Torricelli, orifice, Darcy-Weisbach |
| `algae_model.py` | Strains, BG-11, light/temperature/pH responses, growth, reactor thermal model |
| `carbon_oxygen.py` | Gas supply, CO₂ fixation (2 methods), O₂ (2 methods), ideal-gas volume |
| `energy_model.py` | Pumps, air pump, sensors, controller, LED, PV |
| `economic_model.py` | CAPEX/OPEX (no invented prices), net benefit, payback, allowable CAPEX |
| `health.py` | Algae Health Score, *What limits HydroLoop*, Validation Targets |
| `sensitivity.py` | One-at-a-time sensitivity and tornado data |
| `charts.py` | Plotly figures (Sankeys, paradox chart, tornado …) |
| `reporting.py` | Confidence per output, equations, CSV / Excel / PDF export |
| `config.py` | Loads defaults only from `sources.json`; scenario presets; confidence logic |
| `sources.json` | **Source Ledger**: every number with evidence type, source, DOI, strain, confidence, warning |
| `tools/build_sources.py` | Human-editable generator of `sources.json` |
| `assumptions.md` · `references.md` · `AUDIT.md` | Assumptions, references, engineering audit |
| `tests/` | Unit and edge-case tests |
| `results/` | Reference-case outputs (Excel, CSV, PDF, sensitivity, summary JSON) |

## Rules built into the code
* No number without a ledger entry. Missing sources → **Design Input** (Low confidence), never an invented value.
* Annual values are sums of 8760 simulated hours, never one ideal day × 365.
* CO₂ is **Gross Biological CO₂ Fixation**, never an offset; O₂ is stoichiometric, never "city air".
* The two CO₂ methods and the two O₂ methods are cross-checks and are never added.
* Fixation cannot exceed the carbon actually transferred; growth stops when C, N or P runs out.
* The overflow line has no pump (0 W); flow = min(available overflow, orifice capacity).
* Media cooling = min(psychrometric limit, water-quantity limit); never below the wet-bulb temperature.
* Net electricity subtracts the reactor, control and media fan penalty; a negative result is shown.
* Biomass revenue = 0 and payback = "not computable" until documented prices are entered.
