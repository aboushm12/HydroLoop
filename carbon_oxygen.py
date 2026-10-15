"""Carbon supply, CO2 fixation and O2 production (Sections 9-15).

Biomass formula per C-mol (Chisti 2007): C H1.83 O0.48 N0.11 P0.01  (ash-free)
Electron balance (degree of reduction gamma, CO2/H2O/PO4 reference):
    gamma_NH4 = 4 + H - 2 O - 3 N        gamma_NO3 = 4 + H - 2 O + 5 N
    O2 released per C-mol = gamma / 4    (PQ_stoich = gamma/4 because 1 CO2 per C-mol)
Two O2 methods and two CO2 methods are computed for CROSS-CHECKING ONLY - never added.
Terminology: 'Gross Biological CO2 Fixation' (not offset, not avoided emissions).
"""
from __future__ import annotations

R = 8.314462618        # J/mol/K
M_C, M_CO2, M_O2, M_N, M_P, M_H, M_O = 12.011, 44.009, 31.998, 14.007, 30.974, 1.008, 15.999
M_NAHCO3 = 84.007


def cmol_mass(f: dict) -> float:
    return M_C + f["H"] * M_H + f["O"] * M_O + f["N"] * M_N + f["P"] * M_P


def composition(p: dict) -> dict:
    """Mass fractions per g dry weight (ash-corrected) and O2 stoichiometry."""
    f = p["formula"]
    mw = cmol_mass(f)
    ash = p["ash"]
    cf_formula = M_C / mw * (1 - ash)
    n_frac = f["N"] * M_N / mw * (1 - ash)
    p_frac = f["P"] * M_P / mw * (1 - ash)
    g_nh4 = 4 + f["H"] - 2 * f["O"] - 3 * f["N"]
    g_no3 = 4 + f["H"] - 2 * f["O"] + 5 * f["N"]
    gamma = g_no3 if p["n_source"] == "nitrate" else g_nh4
    pq_stoich = gamma / 4.0
    o2_g_per_g = pq_stoich * M_O2 / mw * (1 - ash)
    cf = p["cf_meas"] if p.get("cf_meas") is not None else p["cf"]
    return dict(mw_cmol=mw, cf_formula=cf_formula, cf_used=cf, n_frac=n_frac, p_frac=p_frac,
                gamma=gamma, pq_stoich=pq_stoich, o2_g_per_g=o2_g_per_g,
                co2_g_per_g_cf=cf * M_CO2 / M_C)


def gas_supply_g_per_h(p: dict, V_L: float, T_C: float, P_Pa: float, hour_on: bool = True) -> dict:
    """CO2 supplied and transferable (g CO2 per hour) for the chosen carbon source."""
    src = p["co2_source"]
    q_m3h = p["vvm"] * V_L * 60.0 / 1000.0 if hour_on else 0.0      # m3 gas per hour
    n_gas = P_Pa * q_m3h / (R * (T_C + 273.15))                       # mol gas per hour
    y = 0.0
    sup = 0.0
    eta = p["eta_transfer"]
    if src == "ambient":
        y = p["co2_ppm"] * 1e-6
        sup = n_gas * y * M_CO2
    elif src in ("enriched", "flue"):
        y = p["co2_enriched_pct"] / 100.0
        sup = n_gas * y * M_CO2
    elif src == "bicarbonate":
        sup = p["bicarb_g_day"] / M_NAHCO3 * M_CO2 / 24.0               # CO2-equivalent, spread over 24 h
        eta = p["eta_bicarb"]
    elif src == "other":
        sup = p["other_co2_g_day"] / 24.0
    if src == "bicarbonate" and p["vvm"] > 0:                         # aeration air still brings ambient CO2
        sup_air = n_gas * p["co2_ppm"] * 1e-6 * M_CO2
        return dict(supplied=sup + sup_air, transferable=sup * eta + sup_air * p["eta_transfer"],
                    gas_m3h=q_m3h, y=y)
    return dict(supplied=sup, transferable=sup * eta, gas_m3h=q_m3h, y=y)


def o2_volume_L(o2_g: float, T_C: float, P_Pa: float) -> float:
    """Ideal-gas volume at the stated temperature and pressure: V = nRT/P."""
    n = o2_g / M_O2
    return n * R * (T_C + 273.15) / P_Pa * 1000.0


def fixation_report(biomass_g: float, co2_fixed_capped_g: float, p: dict, T_C: float, P_Pa: float) -> dict:
    """Cross-checked CO2 / O2 numbers for a period's net biomass production."""
    c = composition(p)
    bm = max(biomass_g, 0.0)
    co2_cf = bm * c["co2_g_per_g_cf"]
    co2_st = bm * p["stoich_factor"]
    diff = abs(co2_cf - co2_st) / max(co2_st, 1e-12) * 100 if bm > 0 else 0.0
    o2_stoich = bm * c["o2_g_per_g"]
    o2_pq = co2_cf / M_CO2 * p["pq"] * M_O2
    o2_diff = abs(o2_stoich - o2_pq) / max(o2_stoich, 1e-12) * 100 if bm > 0 else 0.0
    return dict(
        biomass_g=bm, co2_carbon_method_g=co2_cf, co2_stoich_method_g=co2_st, co2_diff_pct=diff,
        co2_doi2014_unverified_g=bm * p["stoich_doi2014_co2"],
        o2_stoich_g=o2_stoich, o2_pq_g=o2_pq, o2_diff_pct=o2_diff,
        o2_doi2014_unverified_g=bm * p["stoich_doi2014_o2"],
        o2_L=o2_volume_L(o2_stoich, T_C, P_Pa), carbon_in_biomass_g=bm * c["cf_used"],
        warn_co2=diff > 10, warn_o2=o2_diff > 10,
    )
