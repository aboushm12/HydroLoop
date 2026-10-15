# Engineering audit (Section 34)

Independent checks run on the Reference case (annual, NOAA normals) and enforced by `tests/`.

| Budget | Check | Result |
|---|---|---|
| Water | Tank closure V0 + in − losses − makeup − cooling − overflow − spill − V_end | ≈ 1e-10 L |
| Water | Overflow = media evaporation + media drain; reactor and overflow counted once | exact (test) |
| Biomass | Produced = harvested + sampled + ΔX·V = Σ hourly net growth | exact (test) |
| Carbon | Fixed ≤ gross uptake ≤ transferable ≤ supplied, every hour | holds (test) |
| Oxygen | Elemental (γ/4) vs PQ = 1.36 differ < 1 % | not independent: both rest on nitrate stoichiometry |
| CO₂ methods | Carbon-content (Cf = 0.50) vs 1.88 g/g differ 2.6 % | not independent: both rest on the same formula |
| Energy | Net = HVAC gross saving − fan penalty − PBR − control | exact (test); negative shown |
| Hydraulics | ρgh at 997 kg/m³ = 0.0978 bar/m (0.0981 at 1000 kg/m³); Torricelli √(2gh) | tested |
| Psychrometrics | W(25 °C, 50 %) = 0.00988; Twb(35 °C, 19 g/kg) = 26.8 °C | tested |
| Evaporative cooling | Never below wet-bulb; evaporated ≤ delivered | tested |
| Units | L ≈ kg water; kW·h sums of hourly kW; g CO₂ from mol × 44.009 | reviewed |
| Annual values | Sum of 8760 h; monthly sums equal annual | tested |

## Exaggerations found and corrected during development
1. **Media fan penalty** first used EVAPCO Δp measured at 3 m/s face velocity → it alone made the system
   energy-negative. Corrected to scale Δp with (v/3.048)² and exposed `media_face_v` as a design input.
   It remains the #1 driver of net energy in the sensitivity analysis — a real design issue, not a bug.
2. **Earlier chat estimate** (condensate surplus cools ≈ 100 TR / 30 % of a building) was wrong. The
   physics in this model shows that a unit's own condensate covers only part of its own pad demand:
   2 TR Reference → mean 1.45 K pre-cooling (water-limited) against a media limit of ≈ 3–4 K.
   This agrees with Ahmed et al. 2025 (pad water 1.3–1.7 kg/h vs condensate 0.6–0.92 kg/h per TR).
3. **Optimistic preset** originally switched to the thermotolerant CTMI profile and produced *less*
   biomass than Reference (CTMI is lower than the UTEX 1230 data below 30 °C). Strain profile was
   removed from the presets; it is a separate, explicit user choice.
4. **The team's 1.83 g CO₂/g** equals 0.50 × 44/12 exactly, so it cannot cross-validate the carbon-content
   method; the original paper's values could not be read and are shown only as "NOT verified".
5. **Target 4a** first flagged the start-up wash-down as "persistent decline"; a 14-day commissioning
   window (design definition) is now excluded.
6. **Carnot-fraction saving** is ≈ 1.8× the empirical saving; the lower, measured (Ibrahim 2017) slope is
   the primary method and the Carnot value is a cross-check only.
7. **Capacity gain** from pre-cooling (COP +21.4 % in Ibrahim 2017) is **not credited** — only compressor
   power reduction.

## Engineering problems the model exposes in the idea (not fixed by the code — design decisions)
* **Carbon Limited:** ambient air at 0.2 vvm supplies ≈ 4 g CO₂/day to a 20 L panel; with 35 % transfer the
  culture settles near 0.05–0.1 g/L. CO₂-enriched air or bicarbonate is required for meaningful growth.
* **Reactor overheating:** with α = 0.8 and U = 15 W/m²K per face (Low-confidence inputs) the panel reaches
  ≈ 48 °C and is inside 25–35 °C only ≈ 45 % of the time (Target 3 = Fail). Panel cooling with clean
  condensate holds 35 °C but diverts ≈ 450 L/yr from the condenser pad.
* **Phosphorus Limited:** BG-11 has N:P ≈ 76:1 (molar); with a 1.3 % P quota it supports ≈ 0.5 g/L.
* **Orifice paradox:** the 3 mm restrictor passes ≈ 68 L/h at 1 m head while the mean overflow is ≈ 1.7 L/h
  → intermittent trickle and poor pad wetting; a smaller orifice risks clogging. A siphon/dosing chamber
  or pressure-compensated drip line is the engineering alternative to test.
* **Energy is marginal:** Reference net ≈ +48 kWh/yr; it turns negative in winter, with a 3 m/s pad, with
  a conservative pad, or when the measured condensate is ≈ 1.5 L/h.
