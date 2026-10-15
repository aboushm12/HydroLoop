"""Techno-economic analysis (Section 22). No prices are invented: blank inputs stay blank,
and the model reports 'allowable CAPEX' instead of a payback when CAPEX is unknown.
Biomass revenue is 0 unless a documented product price is entered."""
from __future__ import annotations
from algae_model import BG11

CAPEX_KEYS = ["capex_tank", "capex_pbr", "capex_pipes", "capex_valves", "capex_filters", "capex_circpump",
              "capex_airpump", "capex_sensors", "capex_ctrl", "capex_media", "capex_pan", "capex_pv",
              "capex_install", "capex_frame"]
OPEX_KEYS = ["opex_cleaning", "opex_filters", "opex_harvest", "opex_maint", "opex_labour"]


def evaluate(p: dict, annual: dict) -> dict:
    t = p["tariff"]
    capex_known = {k: p[k] for k in CAPEX_KEYS if p.get(k) is not None}
    capex_missing = [k for k in CAPEX_KEYS if p.get(k) is None and not (k == "capex_pv" and not p["pv_on"])]
    capex = sum(capex_known.values()) if capex_known else None

    hvac_saving_sar = annual["hvac_net_saving_kWh"] * t
    pbr_elec_sar = annual["pbr_kWh"] * t
    pv_sar = annual["pv_kWh"] * t if p["pv_on"] else 0.0
    nutrient_kg = annual["bg11_chem_g"] / 1000.0
    nutrient_sar = nutrient_kg * p["opex_nutrient_sar_kg"] if p.get("opex_nutrient_sar_kg") is not None else None
    other_opex = {k: p[k] for k in OPEX_KEYS if p.get(k) is not None}
    opex_missing = [k for k in OPEX_KEYS if p.get(k) is None] + ([] if nutrient_sar is not None else ["opex_nutrient_sar_kg"])
    opex = pbr_elec_sar + (nutrient_sar or 0.0) + sum(other_opex.values())

    water_m3 = annual["condensate_to_reactor_L"] / 1000.0      # only condensate that displaces tap water
    water_value = water_m3 * p["water_tariff"] if p.get("water_tariff") is not None else 0.0
    biomass_rev = annual["biomass_harvested_g"] / 1000.0 * p["biomass_price"] if p.get("biomass_price") else 0.0

    net = hvac_saving_sar + pv_sar + water_value + biomass_rev - opex
    payback = None
    if capex is not None and not capex_missing and net > 0:
        payback = capex / net
    allowable = net * p["eval_years"] if net > 0 else 0.0
    return dict(capex_SAR=capex, capex_missing=capex_missing, capex_items=capex_known,
                annual_electricity_saving_SAR=hvac_saving_sar, pbr_electricity_cost_SAR=pbr_elec_sar,
                pv_value_SAR=pv_sar, nutrient_kg=nutrient_kg, nutrient_cost_SAR=nutrient_sar,
                other_opex_SAR=other_opex, opex_missing=opex_missing, annual_operating_cost_SAR=opex,
                water_reuse_value_SAR=water_value, water_valued=p.get("water_tariff") is not None,
                biomass_revenue_SAR=biomass_rev, net_annual_benefit_SAR=net,
                simple_payback_years=payback, allowable_capex_SAR=allowable,
                cost_limited=net <= 0)
