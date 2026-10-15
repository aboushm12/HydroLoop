"""Photobioreactor, strain responses, growth and nutrients (Sections 1, 6, 7, 8).

Growth (hourly), no invented kinetic constants:
  photons absorbed  I_abs = PPFD_eff * A * 3600e-6 * (1 - exp(-k_abs X L))       mol/h
  PPFD_eff          = min(PPFD, I_valid) + hl_use * max(PPFD - I_valid, 0)
                      (yield measured only up to I_valid = 930 umol/m2/s, Zijffers 2010)
  gross             = Y_x/ph * I_abs * f_T(T) * f_pH(pH)                         g/h
  maintenance       = Y_x/ph * m_s * X * V                                       g/h (day & night)
  caps on gross     : carbon transferable, N available, P available (stoichiometric availability)
  net               = gross - maintenance, also capped by mu_max f_T f_pH X V / 24
f_T, f_pH: linear interpolation between PUBLISHED points (no fitted curve), or the
CTMI cardinal model for the thermotolerant literature profile (labelled).
"""
from __future__ import annotations
import math
import numpy as np

# BG-11 (UTEX, improved recipe 2009): final concentrations in g/L of medium
BG11 = {
    "NaNO3": 1.5, "K2HPO4": 0.04, "MgSO4.7H2O": 0.075, "CaCl2.2H2O": 0.036,
    "Citric acid.H2O": 0.006, "Ferric ammonium citrate": 0.006, "Na2EDTA.2H2O": 0.001, "Na2CO3": 0.02,
    # trace metals solution: stock g/L x 1 mL/L
    "H3BO3": 2.86e-3, "MnCl2.4H2O": 1.81e-3, "ZnSO4.7H2O": 0.22e-3, "Na2MoO4.2H2O": 0.39e-3,
    "CuSO4.5H2O": 0.079e-3, "Co(NO3)2.6H2O": 0.0494e-3,
}
MW = {"NaNO3": 84.995, "K2HPO4": 174.18}
BG11_N_MG_L = BG11["NaNO3"] / MW["NaNO3"] * 14.007 * 1000          # ~247 mg N/L
BG11_P_MG_L = BG11["K2HPO4"] / MW["K2HPO4"] * 30.974 * 1000         # ~7.1 mg P/L


def bg11_table(volume_L: float) -> list:
    return [dict(component=k, g_per_L=v, grams=v * volume_L) for k, v in BG11.items()]


# --------------------------------------------------------------------- strain data
STRAINS = {
    "KAUST 111": dict(species="Chlorella sorokiniana", habitat="Freshwater", origin="Wastewater treatment plants, Makkah",
                      medium="BG-11", ident="ITS1/ITS2, 99.55% BLAST", growth_data="Not published (available under licence)",
                      verified=True),
    "KAUST 113": dict(species="Chlorella vulgaris", habitat="Freshwater", origin="Wastewater treatment plants, Makkah",
                      medium="BG-11", ident="18S rDNA, 100%", growth_data="Not published", verified=True),
    "KAUST 115": dict(species="(not found)", habitat="-", origin="-", medium="-",
                      ident="Not listed in the Sep-2024 KAUST catalogue (index ends at KAUST 114)",
                      growth_data="-", verified=False),
    "KAUST 013": dict(species="Chlorella sorokiniana", habitat="Freshwater", origin="Al Lith hot spring (20.46N, 40.47E)",
                      medium="BG-11", ident="18S rDNA, 100%", growth_data="Not published", verified=True),
    "KAUST 067": dict(species="Scenedesmus sp.", habitat="Freshwater", origin="Wadi Zee hot springs (22.72N, 39.81E)",
                      medium="BG-11", ident="18S rDNA, 99.13%", growth_data="Not published", verified=True),
    "KAUST 039/054": dict(species="Dunaliella sp. / D. polymorpha", habitat="Seawater", origin="NAQUA pond / Al Wahbah crater",
                          medium="F/2 with Red Sea water", ident="-", growth_data="Not published", verified=True),
}


def f_interp(x: float, pts) -> tuple[float, bool]:
    """Linear interpolation; returns (value, inside_data_range)."""
    xs = [a for a, _ in pts]
    ys = [b for _, b in pts]
    inside = xs[0] <= x <= xs[-1]
    return float(np.interp(x, xs, ys)), inside


def ctmi(T: float, tmin: float, topt: float, tmax: float) -> float:
    """Cardinal Temperature Model with Inflection (Rosso et al. 1993; Bernard & Remond 2012)."""
    if T <= tmin or T >= tmax:
        return 0.0
    num = (T - tmax) * (T - tmin) ** 2
    den = (topt - tmin) * ((topt - tmin) * (T - topt) - (topt - tmax) * (topt + tmin - 2 * T))
    return max(0.0, min(1.0, num / den)) if den != 0 else 0.0


def f_temp(T: float, p: dict) -> tuple[float, bool]:
    if p["temp_profile"] == "THERMO_CTMI":
        return ctmi(T, p["ctmi_tmin"], p["ctmi_topt"], p["ctmi_tmax"]), True
    return f_interp(T, p["t_pts_utex1230"])


def f_ph(pH: float, p: dict) -> tuple[float, bool]:
    return f_interp(pH, p["ph_pts"])


# --------------------------------------------------------------------- geometry
def geometry(p: dict) -> dict:
    A = p["pbr_H"] * p["pbr_W"]
    V = A * p["pbr_t"] * 1000.0
    return dict(A_m2=A, V_L=V, L_m=p["pbr_t"], A_total_m2=2 * A + 2 * (p["pbr_H"] + p["pbr_W"]) * p["pbr_t"])


def absorbed_fraction(X: float, p: dict) -> float:
    return 1.0 - math.exp(-p["k_abs"] * X * p["pbr_t"] * 1000.0)  # X g/L = 1000 g/m3


def dark_fraction(X: float, p: dict) -> float:
    """Share of the light path receiving <1% of the entering light (indicator only)."""
    if X <= 0:
        return 0.0
    z1 = math.log(100.0) / (p["k_abs"] * X * 1000.0)
    return max(0.0, 1.0 - z1 / p["pbr_t"])


# --------------------------------------------------------------------- thermal
def thermal_step(T_r: float, T_amb: float, G_facade: float, p: dict, geo: dict, q_evap_W: float,
                 dt_s: float = 3600.0, cool_W: float = 0.0) -> float:
    """Lumped panel energy balance, exact exponential solution over the step."""
    A = geo["A_m2"]
    UA = p["u_face"] * 2 * A
    C = geo["V_L"] * 4180.0            # J/K (culture water only)
    q_sol = p["alpha_sol"] * G_facade * (1 - p["shade"]) * A
    T_eq = T_amb + (q_sol - q_evap_W - cool_W) / UA
    tau = C / UA
    return T_eq + (T_r - T_eq) * math.exp(-dt_s / tau), T_eq, UA


# --------------------------------------------------------------------- growth step
def growth_step(X, N_mg_L, P_mg_L, T_r, ppfd_culture, p, geo, comp, co2_transferable_g, hours=1.0):
    """One hour. Returns dict with gross/net growth and the binding limits."""
    V, A = geo["V_L"], geo["A_m2"]
    fT, T_in = f_temp(T_r, p)
    fpH, pH_in = f_ph(p["ph"], p)
    ppfd_eff = min(ppfd_culture, p["i_valid"]) + p["hl_use"] * max(ppfd_culture - p["i_valid"], 0.0)
    absf = absorbed_fraction(X, p)
    I_abs = ppfd_eff * A * 3600e-6 * hours * absf                       # mol photons
    light_pot = p["y_ph"] * I_abs                                       # g, light-only potential
    gross_pot = light_pot * fT * fpH
    mu_cap = p["mu_max"] / 24.0 * hours * fT * fpH * X * V              # g
    maint = p["y_ph"] * p["m_s"] * X * V * hours                        # g
    # carbon / nutrient availability caps (stoichiometric, no Monod constants)
    c_need_per_g = comp["co2_g_per_g_cf"]
    cap_c = co2_transferable_g / c_need_per_g if c_need_per_g > 0 else 0.0
    cap_n = N_mg_L * V / 1000.0 / comp["n_frac"] if comp["n_frac"] > 0 else float("inf")
    cap_p = P_mg_L * V / 1000.0 / comp["p_frac"] if comp["p_frac"] > 0 else float("inf")
    # label of the light x temperature x pH bucket
    if fT < 0.9 and fT <= fpH:
        lab = "Temperature"
    elif fpH < 0.9:
        lab = "pH"
    else:
        lab = "Light"
    caps = {lab: gross_pot, "Max growth rate": mu_cap + maint,
            "Carbon": cap_c, "Nitrogen": cap_n, "Phosphorus": cap_p}
    gross = max(0.0, min(caps.values()))
    # which factor binds (for 'What limits HydroLoop')
    if light_pot <= 1e-12:
        limit = "Light (dark)"
    elif gross_pot <= 1e-12 and fT == 0:
        limit = "Temperature"
    else:
        limit = min(caps.items(), key=lambda kv: kv[1])[0]
    net = gross - maint
    return dict(gross=gross, maint=maint, net=net, fT=fT, fpH=fpH, T_in_data=T_in, pH_in_data=pH_in,
                I_abs=I_abs, absf=absf, light_pot=light_pot, caps=caps, limit=limit,
                co2_used_g=gross * c_need_per_g, n_used_mg=gross * comp["n_frac"] * 1000,
                p_used_mg=gross * comp["p_frac"] * 1000, ppfd_eff=ppfd_eff)
