# Assumptions (what to replace first)

Every numeric value lives in `sources.json` with its evidence type. This file lists the
**modelling simplifications** and **design definitions** that are not single numbers.

## Modelling simplifications
1. **Climate (default):** monthly NOAA normals → hourly temperature with the ASHRAE fraction-of-daily-range
   profile; humidity ratio held constant through each day (computed at the daily mean temperature);
   step change between months; time axis = local solar time (Jeddah solar noon ≈ 12:23 AST).
   Extremes (45-52 °C records) are not represented → use NASA POWER hourly or measured data.
2. **Solar:** Ångström-Prescott with FAO-56 default coefficients (0.25/0.50), Erbs monthly diffuse fraction,
   Collares-Pereira & Rabl / Liu & Jordan hourly split, isotropic sky on a vertical façade.
   PAR = 0.45 × global; 4.57 µmol/J.
3. **AC load:** runtime fraction rises linearly with outdoor temperature between `t_bal` and `t_des`
   (bin-type assumption, not a building simulation). Indoor return air is fixed (24 °C / 55 %).
4. **Coil leaving state** fixed (13 °C, 95 %); if the coil load at full flow exceeds the unit capacity,
   condensate is scaled down by the capacity ratio.
5. **HVAC power:** Carnot-fraction COP calibrated to the rated COP at 35 °C; capacity gain from pre-cooling
   is **not credited** (only the compressor power reduction).
6. **Empirical saving slope** 1.525 %/K = linearisation of Ibrahim et al. (2017) 6.1 % at ≈ 4 K →
   *Sensitivity Approximation*, not a law.
7. **Media fan penalty:** added fan power V·Δp/η at constant airflow, Δp scaled with (v/3.048)² from EVAPCO
   data. A real propeller fan would lose airflow instead; treat the penalty as an engineering estimate.
8. **Pad storage** is neglected: water delivered in an hour is evaporated or drained in that hour.
9. **Overflow capacity** is computed at the lip head (tank level above the lip is ignored).
10. **Reactor thermal model:** lumped water mass, solar absorptance α and loss coefficient U per face are
    Design Inputs (Low confidence) — calibrate with the 5-minute temperature log.
11. **Aeration evaporation:** gas leaves saturated at the culture temperature.
12. **Growth:** Pirt model with yield and maintenance from Zijffers et al. (2010), validated up to
    930 µmol m⁻² s⁻¹; a user fraction (`hl_use`) of photons above that is credited.
    Temperature factor = interpolation between published points (UTEX 1230: ratios of final dry weight,
    not specific growth rates). pH factor = Huesemann et al. (2018) DOE 1412 at 36 °C.
    **No Monod/half-saturation constants were invented:** C, N and P limit growth only through
    stoichiometric availability.
13. **Biomass composition** = Chisti (2007) generic formula CH1.83O0.48N0.11P0.01 (ash-free); ash = 0 by default.
    With this formula BG-11 phosphorus supports only ≈ 0.5 g/L — real cells can lower their P quota; measure it.
14. **Maintenance respiration** (Pirt m_s) continues at night as biomass loss.
15. **DIC storage** in the culture is neglected: carbon must be transferred in the same hour it is used.
    BG-11 Na₂CO₃ carbon is neglected (≈ 33 mg CO₂/day at 4 L/day refill).
16. **pH** is an input (no carbonate chemistry); **dissolved O₂** is not simulated (no verified kLa).
17. **Harvest** is semi-continuous once per day; harvested volume is replaced with BG-11 made from condensate.
18. **Shortfalls** in reactor make-up are covered by an external (tap) source and counted.

## Design definitions (classification thresholds — not science)
| Item | Definition |
|---|---|
| Health – temperature | mean daylight f_T ≥ 0.7 Healthy; 0.3–0.7 Warning; < 0.3 Critical |
| Health – light | daily gross growth / maintenance ≥ 2 Healthy; 1–2 Warning; < 1 Critical |
| Health – pH | f_pH ≥ 0.8 and inside published 6–9 range → Healthy, else Warning |
| Health – N, P | end-of-day stock ≥ that day's need → Healthy; > 0 Warning; 0 Critical |
| Health – CO₂ | transferable / potential demand ≥ 1 Healthy; 0.5–1 Warning; < 0.5 Critical |
| Health – density | dark-zone fraction ≤ 0.5 Healthy; ≤ 0.8 Warning; > 0.8 Critical |
| Health – DO | measured DO > 30 mg/L → Warning (Kazbar, C. vulgaris; indicative) |
| Target 1 | Pass if every simulated day has condensate ≥ 1.2 × reactor need; Warning ≥ 90 % of days |
| Target 3 | Pass if ≥ 90 % of hours in range; Warning if ≥ 75 % |
| Target 4a | Fail if density declines ≥ 7 consecutive days after a 14-day start-up |
| Orifice flags | clogging if d < 2 mm; poor distribution if capacity > 20 × mean overflow |
| Bio limit | factor that binds most often during lit hours |
| Evaporative Cooling vs High Humidity Limited | which limit (water or ε(T−T_wb)) binds in most active hours |

## Scenario presets (physical, not hand-set savings)
| | Conservative | Reference | Optimistic |
|---|---|---|---|
| Media effectiveness | 0.43 (3-inch, EVAPCO) | 0.55 (Ahmed 2025) | 0.74 (6-inch, EVAPCO) |
| Outdoor-air fraction at coil | 0.05 | 0.10 | 0.20 |
| Indoor RH | 50 % | 55 % | 60 % |
| Credit for photons above 930 µmol | 0 | 0.5 | 1.0 |
