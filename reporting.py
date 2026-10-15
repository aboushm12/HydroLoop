"""Results packaging: confidence per output, equations list, CSV / Excel / PDF export."""
from __future__ import annotations
import io, datetime
import pandas as pd
import config
import health
import algae_model as am

EQUATIONS = [
    ("Coil condensate", "m_cond = m_da * (W_in - W_out) * RTF", "kg/h", "ASHRAE Fundamentals Ch.1 mass balance (PsychroLib)"),
    ("Coil inlet mixing", "W_in = (1-f_OA) W_return + f_OA W_out ; h likewise", "kg/kg", "Adiabatic mixing (ASHRAE)"),
    ("Runtime fraction", "RTF = min(1, max(RTF_min, RTF_min + (1-RTF_min)(T-T_bal)/(T_des-T_bal)))", "-", "Design assumption (bin-type)"),
    ("Tank", "dV/dt = Q_cond(1-loss) - Q_makeup - Q_cool - Q_overflow - Q_spill", "L/h", "Mass conservation"),
    ("Reactor makeup", "Q_makeup = E_aeration + V_harvest + V_sample + V_blowdown", "L/day", "Mass conservation"),
    ("Aeration evaporation", "E = m_air,dry * (W_sat(T_r) - W_amb)", "kg/h", "Gas exits saturated at culture temperature (assumption)"),
    ("Static pressure", "p = rho g h  (1 m H2O = 0.0978 bar at 997 kg/m3; 0.0981 bar at 1000 kg/m3)", "Pa", "Hydrostatics"),
    ("Torricelli", "v_t = sqrt(2 g h)", "m/s", "Bernoulli"),
    ("Orifice", "Q = Cd A_o sqrt(2 g h_net),  h_net = h - (f L/D + sum K) v^2/2g", "m3/s", "White, Fluid Mechanics; Darcy-Weisbach, Swamee-Jain"),
    ("Overflow delivered", "Q_ovf = min(V_tank - V_lip, Q_orifice * 1 h)", "L/h", "Hydraulic capacity limit"),
    ("Wet-bulb", "T_wb = f(T, W, P)", "C", "ASHRAE Fundamentals Ch.1 (PsychroLib)"),
    ("Media limit", "dT_media = eff (T_db - T_wb)", "K", "Saturation effectiveness definition"),
    ("Water limit", "dT_water = m_w * h_fg(T) / (m_air cp_moist),  h_fg = 2501 - 2.361 T", "K", "Energy balance; FAO-56 Annex 3"),
    ("Pre-cooling", "dT = min(dT_media, dT_water, T_db - T_wb);  m_evap = m_air cp dT / h_fg <= m_w", "K", "Section 17"),
    ("HVAC power", "P = Q_cap RTF / COP(T),  COP = eta_II T_e/(T_c - T_e),  T_c = T_air + approach", "kW", "Carnot fraction calibrated to rated COP"),
    ("HVAC saving (empirical)", "dP = P_before * s * dT,  s = 6.1%/4 K = 1.525 %/K", "kW", "Ibrahim et al. 2017 (Sensitivity Approximation)"),
    ("Fan penalty", "P_fan = V_cond dp_media(v) / eta_fan,  dp ~ dp_ref (v/v_ref)^2", "kW", "EVAPCO pad data + assumption"),
    ("Absorbed light", "I_abs = PPFD_eff A (1 - exp(-k_abs X L)) * 3600e-6", "mol/h", "Beer-Lambert"),
    ("Effective PPFD", "PPFD_eff = min(PPFD, 930) + hl_use * max(PPFD - 930, 0)", "umol/m2/s", "Zijffers 2010 validity range + design input"),
    ("Gross growth", "r_g = min(Y I_abs f_T f_pH, mu_max f_T f_pH X V/24 + m, C_avail/c, N_avail/n, P_avail/p)", "g/h", "Pirt model (Zijffers 2010) + stoichiometric caps"),
    ("Maintenance", "r_m = Y m_s X V", "g/h", "Zijffers 2010 (Pirt)"),
    ("Net growth", "dX/dt = (r_g - r_m)/V - D X (harvest), sampling", "g/L/h", "Mass balance"),
    ("Temperature factor", "f_T = interp(T; UTEX1230 points) or CTMI(Tmin, Topt, Tmax)", "-", "Silva-Benavides & Torzillo 2025 / Li 2013"),
    ("pH factor", "f_pH = interp(pH; 6:1.00, 7:0.985, 8:0.826, 9:0.711)", "-", "Huesemann et al. 2018"),
    ("CO2 supplied", "n = P Q y/(R T);  m_CO2 = n * 44.009", "g/h", "Ideal gas"),
    ("Achievable fixation", "CO2_fixed = min(biomass carbon demand, eta * CO2_supplied)", "g/h", "Section 12"),
    ("CO2 (carbon method)", "CO2 = X_prod * C_f * 44/12", "g", "Section 10"),
    ("CO2 (species stoichiometry)", "CO2 = X_prod * 1.88", "g", "Gabrielyan 2022 (cross-check only)"),
    ("O2 (elemental)", "O2 = X_prod * (gamma/4) * 32 / MW_cmol,  gamma_NO3 = 4 + H - 2 O + 5 N", "g", "Chisti 2007 formula, electron balance"),
    ("O2 (PQ)", "O2 = PQ * n_CO2 * 32", "g", "Williams & Robertson 1991 (cross-check only)"),
    ("O2 volume", "V = (m/32) R T / P", "L", "Ideal gas at site T and P"),
    ("Reactor temperature", "T_r(t+dt) = T_eq + (T_r - T_eq) exp(-dt/tau),  T_eq = T_a + (alpha G A - Q_evap - Q_cool)/UA", "C", "Lumped energy balance"),
    ("Net electricity", "E_net = (HVAC saving - fan penalty) - E_PBR - E_control (+ PV)", "kWh", "Section 20"),
    ("Net benefit", "B = E_saving*tariff + water value + biomass revenue(0) - OPEX", "SAR/yr", "Section 22"),
    ("Simple payback", "PB = CAPEX / B (only if CAPEX complete and B > 0)", "yr", "Section 22"),
]


def output_confidence(res: dict) -> list:
    p, a, e = res["params"], res["annual"], res["econ"]
    meas = p["cond_mode"] == "measured" and p.get("cond_meas_lph") is not None
    k_cond = ["cond_meas_lph"] if meas else ["noaa_rh", "noaa_tmax", "oa_frac", "rh_in", "t_coil", "rh_coil", "evap_cfm_tr", "ac_tr", "t_bal", "rtf_min"]
    k_bio = ["y_ph", "m_s", "k_abs", "hl_use", "ph_pts", "alpha_sol", "u_face", "eta_transfer", "co2_ppm", "formula", "ang_a", "f_par"]
    k_bio += ["t_pts_utex1230"] if p["temp_profile"] == "UTEX1230" else ["ctmi_topt", "ctmi_tmax", "ctmi_tmin"]
    local = p["strain_mode"] == "local"
    bio_extra = ["Low"] if local else ["Medium"]
    rows = [
        ("Condensate recovered", a["condensate_L"], "L", config.combine(k_cond, p)),
        ("Water used in reactor (from condensate)", a["condensate_to_reactor_L"], "L", config.combine(k_cond + ["dil_rate", "vvm"], p)),
        ("Overflow reused for condenser cooling (evaporated)", a["media_evap_L"], "L", config.combine(k_cond + ["media_eff", "cond_cfm_tr", "orifice_d"], p)),
        ("Biomass produced" + (" (Estimated - local strain)" if local else ""), a["biomass_produced_g"], "g", config.combine(k_bio, p, bio_extra)),
        ("Gross Biological CO2 Fixation", a["co2_carbon_method_g"], "g CO2", config.combine(k_bio + ["cf"], p, bio_extra)),
        ("Gross O2 produced (stoichiometric)", a["o2_stoich_g"], "g O2", config.combine(k_bio + ["formula", "ash"], p, bio_extra)),
        ("Condenser inlet air drop (mean, AC on)", a["mean_dT_cond_active"], "K", config.combine(k_cond + ["media_eff", "cond_cfm_tr"], p)),
        ("HVAC electricity saved (gross)", a["hvac_gross_saving_kWh"], "kWh", config.combine(k_cond + ["media_eff", "slope_pct_per_K", "cop_rated"], p)),
        ("PBR + control electricity", a["pbr_kWh"], "kWh", config.combine(["air_w_per_lpm", "pump_eff", "circ_lpm", "sensor_w", "ctrl_w"], p)),
        ("Net electricity impact", a["net_electricity_kWh"], "kWh", config.combine(k_cond + ["media_eff", "slope_pct_per_K", "cop_rated", "media_dp_pa", "fan_eff", "air_w_per_lpm", "pump_eff"], p)),
        ("Net annual benefit", e["net_annual_benefit_SAR"], "SAR/yr", config.combine(k_cond + ["tariff", "media_eff", "slope_pct_per_K", "cop_rated", "media_dp_pa", "fan_eff", "air_w_per_lpm", "pump_eff"], p)),
    ]
    keymap = {0: k_cond, 1: k_cond + ["dil_rate", "vvm"], 2: k_cond + ["media_eff", "cond_cfm_tr", "orifice_d"], 3: k_bio, 4: k_bio + ["cf"],
              5: k_bio + ["formula", "ash"], 6: k_cond + ["media_eff", "cond_cfm_tr"], 7: k_cond + ["media_eff", "slope_pct_per_K", "cop_rated"],
              8: ["air_w_per_lpm", "pump_eff", "circ_lpm", "sensor_w", "ctrl_w"],
              9: k_cond + ["media_eff", "slope_pct_per_K", "cop_rated", "media_dp_pa", "fan_eff", "air_w_per_lpm", "pump_eff"],
              10: k_cond + ["tariff", "media_eff", "slope_pct_per_K", "cop_rated", "media_dp_pa", "fan_eff", "air_w_per_lpm", "pump_eff"]}
    out = []
    for i, r in enumerate(rows):
        weak = [config.LEDGER[k]["name"] for k in keymap[i] if config.CONF_RANK[config.param_confidence(k, p)] <= 1][:4]
        out.append(dict(output=r[0], value=round(float(r[1]), 3), unit=r[2], confidence=r[3],
                        measure_first=("; ".join(weak) if weak else "-")))
    out.append(dict(output="Net Carbon Impact", value=None, unit="kg CO2e",
                    confidence="Not Yet Quantified", measure_first="embodied carbon of equipment, nutrients, maintenance, lifetime"))
    return out


def summary_table(res: dict) -> pd.DataFrame:
    a, e = res["annual"], res["econ"]
    rows = [(k, v) for k, v in a.items() if isinstance(v, (int, float))]
    rows += [("econ_" + k, v) for k, v in e.items() if isinstance(v, (int, float)) or v is None]
    return pd.DataFrame(rows, columns=["metric", "value"])


def ledger_table() -> pd.DataFrame:
    cols = ["key", "name", "value", "unit", "data_type", "location", "strain", "conditions", "confidence", "used_as",
            "warning", "source", "url", "doi", "year"]
    return pd.DataFrame([{c: (str(e[c]) if (c == "value" or isinstance(e[c], (list, dict))) and e[c] is not None else e[c]) for c in cols} for e in config.SOURCES["ledger"]])


def excel_bytes(res: dict, sens: pd.DataFrame | None = None) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        summary_table(res).to_excel(xw, sheet_name="Summary", index=False)
        pd.DataFrame(output_confidence(res)).to_excel(xw, sheet_name="Confidence", index=False)
        pd.DataFrame(health.validation(res)).to_excel(xw, sheet_name="Validation", index=False)
        lim = health.limits(res)
        pd.DataFrame(lim["system_flags"], columns=["flag", "detail"]).to_excel(xw, sheet_name="Limits", index=False)
        res["monthly"].to_excel(xw, sheet_name="Monthly", index=False)
        res["daily"].to_excel(xw, sheet_name="Daily", index=False)
        res["hourly"].to_excel(xw, sheet_name="Hourly", index=False)
        pd.DataFrame(am.bg11_table(res["geo"]["V_L"])).to_excel(xw, sheet_name="BG-11 per fill", index=False)
        ledger_table().to_excel(xw, sheet_name="Source ledger", index=False)
        pd.DataFrame(EQUATIONS, columns=["name", "equation", "unit", "source"]).to_excel(xw, sheet_name="Equations", index=False)
        if sens is not None:
            sens.to_excel(xw, sheet_name="Sensitivity", index=False)
    return buf.getvalue()


def _ascii(s) -> str:
    return str(s).encode("latin-1", "replace").decode("latin-1")


def pdf_bytes(res: dict, scenario: str = "") -> bytes:
    from fpdf import FPDF
    a, e, p = res["annual"], res["econ"], res["params"]
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, 12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, "HydroLoop - integrated simulation report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, new_x="LMARGIN", new_y="NEXT", text=_ascii(f"Generated {datetime.date.today()} | scenario: {scenario} | period: {p['period']} | climate: {res['wx_source']}\n"
                                "All results are SIMULATED and ESTIMATED; Subject to Field Validation. CO2 values are Gross Biological "
                                "Fixation (not offsets); O2 values are stoichiometric (not a change in city air)."))
    def section(t):
        pdf.ln(2); pdf.set_font("Helvetica", "B", 11); pdf.cell(0, 7, _ascii(t), new_x="LMARGIN", new_y="NEXT"); pdf.set_font("Helvetica", "", 8.5)
    def row(k, v):
        pdf.cell(95, 5, _ascii(k)); pdf.cell(0, 5, _ascii(v), new_x="LMARGIN", new_y="NEXT")
    lim = health.limits(res)
    section("What limits HydroLoop")
    row("Bio loop", f"{lim['bio_limit']} ({lim['bio_share']*100:.0f}% of lit hours)")
    for f, d in lim["system_flags"]:
        row(f, d[:80])
    section("Results with confidence")
    for o in output_confidence(res):
        v = "-" if o["value"] is None else f"{o['value']:,.2f} {o['unit']}"
        row(o["output"][:55], f"{v} | {o['confidence']}"[:95])
    section("Validation targets")
    for v in health.validation(res):
        row(v["target"][:60], f"{v['status']}: {v['value']}"[:95])
    section("Economics")
    row("Net annual benefit", f"{e['net_annual_benefit_SAR']:,.1f} SAR/yr")
    row("Allowable CAPEX for payback within evaluation period", f"{e['allowable_capex_SAR']:,.0f} SAR ({p['eval_years']} yr)")
    row("Simple payback", "not computable (CAPEX incomplete)" if e["simple_payback_years"] is None else f"{e['simple_payback_years']:.1f} yr")
    row("Biomass revenue", "0 (no documented product/market/price)")
    section("Key assumptions (Design Inputs to replace with measurements)")
    for ent in config.SOURCES["ledger"]:
        if ent["data_type"] == "Design Input" and ent["confidence"] in ("Low", "Low-Medium") and ent["value"] is not None and ent["group"] != "Economics":
            row(ent["name"][:60], f"{ent['value']} {ent['unit']}"[:60])
    pdf.add_page()
    section("Sources")
    for k, c in config.CITATIONS.items():
        pdf.multi_cell(0, 4, new_x="LMARGIN", new_y="NEXT", text=_ascii(f"[{k}] {c['text']} {('doi:' + c['doi']) if c['doi'] else ''} {c['url']}"))
    section("Warnings")
    for ent in config.SOURCES["ledger"]:
        if ent["warning"]:
            pdf.multi_cell(0, 4, new_x="LMARGIN", new_y="NEXT", text=_ascii(f"- {ent['name']}: {ent['warning']}"))
    return bytes(pdf.output())
