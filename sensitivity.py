"""One-at-a-time sensitivity analysis and tornado data (Section 26)."""
from __future__ import annotations
import copy
import pandas as pd
import simulation as sim
import climate_model as cm

# key, label, low, high   (ranges are explicit design choices for the sweep)
SWEEP = [
    ("cond_scale", "Condensate rate (x)", 0.5, 1.5),
    ("rh_offset", "Outdoor RH (+/- 10 pts)", -10.0, 10.0),
    ("t_offset", "Outdoor air temperature (+/- 2 C)", -2.0, 2.0),
    ("u_face", "Reactor heat loss U (reactor temperature)", 8.0, 25.0),
    ("light_scale", "Light intensity (x)", 0.7, 1.3),
    ("pbr_W", "Reactor volume (panel width, m)", 0.25, 1.0),
    ("pbr_t", "Optical path length (m)", 0.02, 0.06),
    ("nutrient_strength", "Nutrient dosing (x BG-11)", 0.5, 2.0),
    ("eta_transfer", "CO2 transfer efficiency", 0.15, 0.60),
    ("vvm", "Aeration rate (vvm)", 0.1, 0.5),
    ("pump_eff", "Pump efficiency (pump consumption)", 0.15, 0.40),
    ("ovf_head", "Overflow head (m)", 0.3, 2.0),
    ("orifice_d", "Orifice diameter (m)", 0.002, 0.005),
    ("media_eff", "Media effectiveness", 0.43, 0.74),
    ("cond_cfm_tr", "Condenser air flow (cfm/TR)", 800.0, 1200.0),
    ("sched_off", "AC operating hours (end hour, start 0)", 12, 24),
    ("media_face_v", "Media face velocity (pressure drop)", 1.0, 3.0),
    ("tariff", "Electricity tariff (SAR/kWh)", 0.18, 0.32),
]
OUTPUTS = {
    "net_benefit_SAR": lambda r: r["econ"]["net_annual_benefit_SAR"],
    "biomass_kg": lambda r: r["annual"]["biomass_produced_g"] / 1000,
    "net_energy_kWh": lambda r: r["annual"]["net_electricity_kWh"],
    "payback_or_allowable_capex": lambda r: (r["econ"]["simple_payback_years"] if r["econ"]["simple_payback_years"] is not None
                                             else r["econ"]["allowable_capex_SAR"]),
}
WEATHER_KEYS = {"rh_offset", "t_offset"}


def run(p: dict, wx=None, sweep=SWEEP) -> pd.DataFrame:
    base_wx = wx if wx is not None else cm.build_noaa_year(p)
    base = sim.run(p, base_wx)
    b = {k: f(base) for k, f in OUTPUTS.items()}
    rows = []
    for key, label, lo, hi in sweep:
        vals = {}
        for tag, v in (("low", lo), ("high", hi)):
            q = copy.deepcopy(p)
            q[key] = v
            w = cm.build_noaa_year(q) if (key in WEATHER_KEYS and wx is None) else base_wx
            r = sim.run(q, w)
            vals[tag] = {k: f(r) for k, f in OUTPUTS.items()}
        for out in OUTPUTS:
            rows.append(dict(param=key, label=label, low=lo, high=hi, output=out, base=b[out],
                             at_low=vals["low"][out], at_high=vals["high"][out],
                             swing=abs(vals["high"][out] - vals["low"][out])))
    return pd.DataFrame(rows)
