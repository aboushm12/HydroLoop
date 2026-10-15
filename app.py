"""HydroLoop | هايدرو لوب - integrated engineering simulation (Streamlit).
Run:  streamlit run app.py
"""
from __future__ import annotations
import copy, json
import pandas as pd
import streamlit as st

import config
import climate_model as cm
import simulation as sim
import health
import sensitivity as sens_mod
import charts as ch
import reporting as rp
import algae_model as am
import overflow_hydraulics as oh

st.set_page_config(page_title="HydroLoop simulation", page_icon="💧", layout="wide")
_PC = iter(range(10 ** 6))


def plot(fig, where=None):
    (where or st).plotly_chart(fig, width="stretch", key=f"pc{next(_PC)}")

TYPE_BADGE = {"Local Saudi Data": "🟢 Local Saudi", "Published Experimental Data": "🔵 Published exp.",
              "Literature Assumption": "🟡 Literature assumption", "Design Input": "⚪ Design input",
              "Measured Input": "🟢 Measured", "Manufacturer Data": "🔵 Manufacturer", "Calculated Value": "🟣 Calculated"}


def help_for(key):
    e = config.LEDGER[key]
    return f"{TYPE_BADGE.get(e['data_type'], e['data_type'])} | confidence: {e['confidence']}\n\nSource: {e['source'][:220]}\n\n{e['warning']}"


# ------------------------------------------------------------------ sidebar inputs
st.sidebar.title("HydroLoop · هايدرو لوب")
scenario = st.sidebar.selectbox("Scenario preset", ["Reference", "Conservative", "Optimistic"],
                                help="Presets change physical conditions/equipment (media depth, outdoor-air share, indoor RH, high-light credit, strain profile) - never a hand-typed saving %.")
st.sidebar.caption(config.SCENARIO_NOTES[scenario])
P = config.scenario_params(scenario)


def num(key, label=None, minv=None, maxv=None, step=None, fmt=None):
    e = config.LEDGER[key]
    lab = (label or e["name"]) + (f" [{e['unit']}]" if e["unit"] not in ("-", "") else "")
    v = P[key]
    if v is None:
        txt = st.text_input(lab, "", help=help_for(key), key="t_" + key)
        try:
            P[key] = float(txt) if txt.strip() else None
        except ValueError:
            st.warning(f"{lab}: not a number")
            P[key] = None
        return
    if isinstance(v, bool):
        P[key] = st.checkbox(lab, v, help=help_for(key), key="b_" + key)
        return
    if isinstance(v, int) and not isinstance(v, bool):
        P[key] = st.number_input(lab, value=int(v), min_value=minv, max_value=maxv, step=step or 1, help=help_for(key), key="n_" + key)
        return
    P[key] = st.number_input(lab, value=float(v), min_value=minv, max_value=maxv, step=step, format=fmt or "%.4g",
                             help=help_for(key), key="n_" + key)


with st.sidebar.expander("Period & climate", True):
    P["period"] = st.selectbox("Simulation period", ["annual", "summer", "winter", "month", "30d", "7d", "24h"],
                               help="Annual values are sums of simulated hours, not one day x 365.")
    if P["period"] == "month":
        P["period_month"] = st.selectbox("Month", list(range(1, 13)), index=7)
    if P["period"] in ("24h", "7d", "30d"):
        num("start_doy", "Start day of year", 1, 365)
    clim = st.radio("Climate data", ["NOAA 1991-2020 normals (built-in)", "NASA POWER hourly (internet)", "Upload CSV"],
                    help="NASA POWER needs internet access on this machine (21.49 N, 39.19 E).")
    year = st.number_input("NASA POWER year", 2001, 2025, 2023) if "NASA" in clim else None
    up = st.file_uploader("Weather CSV (month,day,hour,T,RH,GHI[,DHI,P])", type="csv") if clim == "Upload CSV" else None
    num("facade_az"); num("shade", minv=0.0, maxv=0.95); num("rh_offset"); num("t_offset")

with st.sidebar.expander("AC unit & condensate"):
    P["cond_mode"] = st.radio("Condensate mode", ["psychrometric", "measured"],
                              help="Measured Mode = highest confidence: enter the L/h measured during the 3-day test.")
    if P["cond_mode"] == "measured":
        num("cond_meas_lph")
    for k in ["ac_tr", "evap_cfm_tr", "oa_frac", "t_in", "rh_in", "t_coil", "rh_coil", "sched_on", "sched_off",
              "t_bal", "t_des", "rtf_min", "cop_rated", "cond_cfm_tr"]:
        num(k)

with st.sidebar.expander("Evaporative media (condenser)"):
    for k in ["media_on", "media_eff", "media_face_v", "media_dp_pa", "fan_eff", "slope_pct_per_K"]:
        num(k)
    P["hvac_method"] = st.radio("Saving method", ["empirical", "carnot"],
                                help="empirical = Ibrahim et al. 2017 linear slope (Sensitivity Approximation); carnot = physical cross-check")

with st.sidebar.expander("Tank & gravity overflow"):
    for k in ["tank_L", "ovf_level", "tank_init", "prefilter_loss", "ovf_head", "pipe_L", "pipe_D", "n_elbows", "orifice_d"]:
        num(k)

with st.sidebar.expander("Photobioreactor"):
    for k in ["pbr_H", "pbr_W", "pbr_t", "wall_tau", "alpha_sol", "u_face", "x0", "ph", "vvm", "dil_rate", "harvest_hour",
              "sample_L", "blowdown_L", "circ_lpm", "circ_head", "pump_eff", "nutrient_strength", "cool_on", "cool_set", "light_on"]:
        num(k)

with st.sidebar.expander("Strain & growth"):
    P["strain_mode"] = st.radio("Strain mode", ["literature", "local"], format_func=lambda s: {
        "literature": "Literature Reference Mode (species level)", "local": "Local Saudi Candidate Mode (KAUST 111 - Estimated)"}[s])
    P["temp_profile"] = st.selectbox("Temperature response", ["UTEX1230", "THERMO_CTMI"],
                                     index=0 if P["temp_profile"] == "UTEX1230" else 1,
                                     help="UTEX1230 = published measured points; THERMO_CTMI = thermotolerant literature (Topt 37, Tmax 42, heterotrophic data).")
    for k in ["hl_use", "k_abs", "t_range_lo", "t_range_hi"]:
        num(k)

with st.sidebar.expander("Carbon & oxygen"):
    P["co2_source"] = st.selectbox("Carbon source", ["ambient", "enriched", "bicarbonate", "flue", "other"])
    for k in ["co2_ppm", "co2_enriched_pct", "eta_transfer", "bicarb_g_day", "other_co2_g_day", "cf_meas", "cf", "pq", "ash", "do_meas"]:
        num(k)
    P["biomass_fate"] = st.selectbox("Biomass fate", ["harvested", "stored", "product", "composted", "digested", "discarded"])

with st.sidebar.expander("Energy & economics"):
    for k in ["air_w_per_lpm", "sensor_w", "ctrl_w", "pv_on", "pv_kwp", "tariff", "water_tariff", "biomass_price", "eval_years",
              "opex_nutrient_sar_kg", "opex_maint", "opex_cleaning", "opex_filters", "opex_harvest", "opex_labour"] + \
             ["capex_tank", "capex_pbr", "capex_pipes", "capex_valves", "capex_filters", "capex_circpump", "capex_airpump",
              "capex_sensors", "capex_ctrl", "capex_media", "capex_pan", "capex_pv", "capex_install", "capex_frame"]:
        num(k)

with st.sidebar.expander("Validation inputs (experiment)"):
    num("vt2_meas")


# ------------------------------------------------------------------ run
@st.cache_data(show_spinner=False)
def weather(pjson, clim, year, upbytes):
    p = json.loads(pjson)
    if clim.startswith("NASA"):
        return cm.fetch_nasa_power(p, int(year))
    if clim == "Upload CSV" and upbytes:
        import io
        return cm.from_csv(io.BytesIO(upbytes), p)
    return cm.build_noaa_year(p)


@st.cache_data(show_spinner=False)
def run_cached(pjson, clim, year, upbytes):
    p = json.loads(pjson)
    wx = weather(json.dumps({k: p[k] for k in p}), clim, year, upbytes)
    r = sim.run(p, wx)
    return r


wkeys = ["lat", "lon", "elev_m", "noaa_tmax", "noaa_tmin", "noaa_rh", "noaa_sun", "ang_a", "ang_b", "albedo", "f_par",
         "umol_per_J", "facade_az", "rh_offset", "t_offset"]
upb = up.getvalue() if up is not None else None
try:
    with st.spinner("Simulating..."):
        R = run_cached(json.dumps(P), clim, year, upb)
except Exception as ex:  # network failure for NASA POWER etc.
    st.error(f"Climate/simulation error: {ex}. Falling back to NOAA normals.")
    R = run_cached(json.dumps(P), "NOAA", None, None)

A, E = R["annual"], R["econ"]
LIM = health.limits(R)
VAL = health.validation(R)
HL = health.daily_health(R)
CONF = rp.output_confidence(R)
conf_of = {c["output"]: c["confidence"] for c in CONF}
per_label = {"annual": "per year", "summer": "Jun-Aug", "winter": "Dec-Feb", "month": "per month", "30d": "30 days", "7d": "7 days", "24h": "24 h"}[P["period"]]

# ------------------------------------------------------------------ header
st.title("HydroLoop · Integrated engineering simulation")
st.caption("Simulated · Estimated · Subject to Field Validation — not a marketing model. "
           f"Climate: {R['wx_source']} · Period: {P['period']} ({R['n_hours']} h) · Scenario: {scenario}")
flags_txt = " · ".join(f for f, _ in LIM["system_flags"]) or "none"
if LIM["system_flags"]:
    st.error(f"**What limits HydroLoop now:** bio loop → **{LIM['bio_limit']}** ({LIM['bio_share']*100:.0f}% of lit hours) · "
             f"system → **{flags_txt}**")
else:
    st.warning(f"**What limits HydroLoop now:** bio loop → **{LIM['bio_limit']}** ({LIM['bio_share']*100:.0f}% of lit hours)")

tabs = st.tabs(["Executive", "Sustainability", "Water", "Algae", "Carbon & O₂", "Cooling & HVAC", "Energy",
                "Economics", "Sensitivity", "Validation", "Engineering view", "Research audit", "Export"])

days = A["days"]
latest = HL.iloc[-1] if len(HL) else None

# ------------------------------------------------------------------ Executive
with tabs[0]:
    st.subheader(f"Executive dashboard ({per_label})")
    k = st.columns(4)
    k[0].metric("Water recovered / day", f"{A['condensate_L']/days:,.1f} L", help=conf_of["Condensate recovered"])
    k[1].metric(f"Water recovered ({per_label})", f"{A['condensate_L']/1000:,.2f} m³")
    k[2].metric("Reactor need covered by condensate", f"{A['coverage_pct']:.0f}%")
    k[3].metric("Water used in reactor", f"{A['condensate_to_reactor_L']:,.0f} L")
    k = st.columns(4)
    k[0].metric("Overflow to condenser media", f"{A['overflow_L']:,.0f} L")
    k[1].metric("Algae health (last day)", latest["status"] if latest is not None else "-",
                help=f"Limiting: {latest['limiting']}" if latest is not None else None)
    k[2].metric("Strain", "C. sorokiniana " + ("KAUST 111 (Estimated)" if P["strain_mode"] == "local" else "(species-level ref.)"))
    k[3].metric("Biomass produced", f"{A['biomass_produced_g']/1000:,.3f} kg")
    k = st.columns(4)
    k[0].metric("CO₂ fixed (gross biological)", f"{A['co2_carbon_method_g']/1000:,.3f} kg")
    k[1].metric("O₂ produced (stoichiometric)", f"{A['o2_stoich_g']/1000:,.3f} kg")
    k[2].metric("Condenser air drop (mean, AC on)", f"{A['mean_dT_cond_active']:.2f} K")
    k[3].metric("AC electricity saved (net of fan)", f"{A['hvac_net_saving_kWh']:,.0f} kWh")
    k = st.columns(4)
    k[0].metric("Reactor + control electricity", f"{A['pbr_kWh']:,.0f} kWh")
    k[1].metric("NET electricity", f"{A['net_electricity_kWh']:,.0f} kWh", delta="negative = system consumes more than it saves" if A["net_electricity_kWh"] < 0 else None,
                delta_color="inverse")
    k[2].metric("Operating cost", f"{E['annual_operating_cost_SAR']:,.0f} SAR", help="Only priced items; missing: " + ", ".join(E["opex_missing"]))
    k[3].metric("Net saving / payback", f"{E['net_annual_benefit_SAR']:,.0f} SAR",
                help=("Payback " + (f"{E['simple_payback_years']:.1f} yr" if E["simple_payback_years"] else "not computable: CAPEX incomplete")))
    st.markdown("**Confidence per result** (weakest-link of its inputs)")
    st.dataframe(pd.DataFrame(CONF), width="stretch", hide_index=True)
    st.markdown("**Scenario comparison** (same climate, physical presets)")
    rows = []
    for s in ["Conservative", "Reference", "Optimistic"]:
        q = config.scenario_params(s, None)
        for kk in ["period", "period_month", "start_doy", "cond_mode", "cond_meas_lph", "co2_source"]:
            q[kk] = P[kk]
        r = run_cached(json.dumps(q), clim, year, upb)
        a, e = r["annual"], r["econ"]
        rows.append(dict(scenario=s, condensate_L=a["condensate_L"], overflow_evap_L=a["media_evap_L"], dT_cond_K=a["mean_dT_cond_active"],
                         hvac_net_kWh=a["hvac_net_saving_kWh"], pbr_kWh=a["pbr_kWh"], net_kWh=a["net_electricity_kWh"],
                         biomass_g=a["biomass_produced_g"], co2_g=a["co2_carbon_method_g"], net_SAR=e["net_annual_benefit_SAR"]))
    st.dataframe(pd.DataFrame(rows).round(2), width="stretch", hide_index=True)
    plot(ch.architecture())

# ------------------------------------------------------------------ Sustainability
with tabs[1]:
    st.subheader("Sustainability dashboard")
    rows = [("Condensate recovered", A["condensate_L"], "L"), ("Water reused in PBR", A["condensate_to_reactor_L"], "L"),
            ("Overflow reused for condenser cooling (evaporated)", A["media_evap_L"], "L"),
            ("Overflow drained (not evaporated)", A["media_drain_L"], "L"), ("Spilled (wasted)", A["spill_L"], "L"),
            ("Biomass produced", A["biomass_produced_g"], "g"), ("Gross CO2 fixed (carbon method)", A["co2_carbon_method_g"], "g"),
            ("Gross O2 produced", A["o2_stoich_g"], "g"), ("O2 volume at site T, P", A["o2_L"], "L"),
            ("HVAC electricity saved (net of fan)", A["hvac_net_saving_kWh"], "kWh"), ("PBR electricity used", A["pbr_kWh"], "kWh"),
            ("Net electricity impact", A["net_electricity_kWh"], "kWh"),
            ("Operational CO2 from net electricity (grid factor 0.568)", A["net_electricity_co2_kg"], "kg CO2")]
    st.dataframe(pd.DataFrame(rows, columns=["indicator", "value", "unit"]).round(2), width="stretch", hide_index=True)
    st.info("**Net Carbon Impact: Not Yet Quantified.** Embodied carbon of equipment, nutrients, maintenance and lifetime are not available. "
            "Biological fixation is reported as *Gross Biological CO₂ Fixation*; carbon in biomass can return to the air when it decomposes. "
            "No 'offset' or 'avoided emissions' claim is made. O₂ is a stoichiometric quantity tied to biomass growth, not a measured change in Jeddah air.")
    plot(ch.water_sankey(R))

# ------------------------------------------------------------------ Water
with tabs[2]:
    st.subheader("Water loop")
    plot(ch.water_sankey(R))
    nd = max(1, int(R["n_hours"] / 24))
    di = st.slider("Day to inspect (index from period start)", 0, nd - 1, 0)
    plot(ch.tank_day(R, di))
    plot(ch.tank_series(R))
    if P["period"] in ("annual", "summer", "winter"):
        plot(ch.monthly_bars(R, [("condensate_L", "Condensate"), ("reactor_L", "Reactor makeup"), ("overflow_L", "Overflow")],
                             "Monthly water flows", "L/month"))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Gravity overflow hydraulics** (no pump)")
        h = R["hydraulics"]
        st.dataframe(pd.DataFrame([("Elevation difference", h["head_m"], "m"), ("Static pressure", h["static_kpa"], "kPa"),
                                   ("Static pressure", h["static_bar"], "bar"), ("Torricelli velocity (theoretical)", h["v_torricelli"], "m/s"),
                                   ("Losses (friction+minor)", h["h_loss_m"], "m"), ("Net head", h["h_net_m"], "m"),
                                   ("Pipe velocity", h["v_pipe"], "m/s"), ("Orifice velocity", h["v_orifice"], "m/s"),
                                   ("Orifice capacity", h.get("Q_Lph", 0), "L/h"), ("Reynolds (pipe)", h["Re"], "-")],
                                  columns=["quantity", "value", "unit"]).round(4), hide_index=True, width="stretch")
        for f in oh.assess(h, R["hourly"]["overflow_L"].tolist()):
            st.warning(f)
        st.caption("A smaller outlet does not create energy: it only reduces the flow the available head can push.")
    with c2:
        st.markdown("**Order-of-magnitude check vs Jeddah 2024 field study** (AlGhamdi et al.)")
        st.dataframe(pd.DataFrame([("This simulation (annual-equivalent)", A["condensate_L"] / days * 365, f"{P['ac_tr']} TR, model"),
                                   ("Jeddah split AC (2019)", 20614, "capacity NOT reported"),
                                   ("Jeddah window AC (2019)", 8725, "capacity NOT reported")],
                                  columns=["case", "L/yr", "note"]).round(0), hide_index=True, width="stretch")
        st.caption("The study did not report unit capacity and extrapolated 8 h/day collection to 24 h, so it is not scaled to tonnage.")

# ------------------------------------------------------------------ Algae
with tabs[3]:
    st.subheader("Bio loop - photobioreactor")
    g = R["geo"]
    st.caption(f"Panel {P['pbr_H']} x {P['pbr_W']} m, light path {P['pbr_t']*1000:.0f} mm → {g['V_L']:.1f} L, lit area {g['A_m2']:.2f} m² · "
               f"HRT {A['hrt_days']:.1f} d · volumetric productivity {A['vol_productivity_g_L_d']:.3f} g/L/d · areal {A['areal_productivity_g_m2_d']:.2f} g/m²/d")
    if P["strain_mode"] == "local":
        st.warning("Local Saudi Candidate Mode: KAUST 111 growth parameters are NOT published. Results are Estimated with Low confidence "
                   "and use species-level data from other strains.")
    plot(ch.growth_curve(R))
    plot(ch.cumulative(R))
    plot(ch.temp_vs_growth(R))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Algae Health Score (latest day)**")
        if latest is not None:
            st.markdown(f"Overall: **{latest['status']}** · limiting factor: **{latest['limiting']}**")
            st.dataframe(pd.DataFrame([(k, latest[k], v) for k, v in latest["detail"].items()], columns=["factor", "status", "why"]),
                         hide_index=True, width="stretch")
        st.caption("Status thresholds are design definitions (assumptions.md); the ratios behind them come from strain data and mass balances.")
        st.dataframe(HL["status"].value_counts().rename("days"), width="stretch")
    with c2:
        st.markdown("**Growth-limiting factor (share of lit hours)**")
        st.dataframe(pd.Series(LIM["bio_shares"]).rename("share").round(3), width="stretch")
        st.markdown(f"**BG-11 (UTEX) for one {g['V_L']:.0f} L fill** — nutrients go to the reactor loop only, never the clean tank")
        st.dataframe(pd.DataFrame(am.bg11_table(g["V_L"])).round(5), hide_index=True, width="stretch")
        st.caption(f"BG-11 supplies ≈{am.BG11_N_MG_L:.0f} mg N/L and ≈{am.BG11_P_MG_L:.1f} mg P/L. With the generic formula (P ≈1.3% of DW) "
                   "phosphorus limits biomass to ≈0.5 g/L - measure the real P quota.")
    st.markdown("**Saudi strain verification (KAUST Living Library, Sep 2024)**")
    st.dataframe(pd.DataFrame([dict(id=k, **v) for k, v in am.STRAINS.items()]), hide_index=True, width="stretch")

# ------------------------------------------------------------------ Carbon & O2
with tabs[4]:
    st.subheader("Carbon loop & oxygen production")
    plot(ch.carbon_sankey(R))
    comp = R["comp"]
    st.dataframe(pd.DataFrame([
        ("CO2 required (gross photosynthetic uptake)", A["co2_gross_uptake_g"], "g", "model"),
        ("CO2 supplied", A["co2_supplied_g"], "g", P["co2_source"]),
        ("CO2 transferable", A["co2_transferable_g"], "g", f"eta = {P['eta_transfer']}"),
        ("CO2 fixed - carbon-content method", A["co2_carbon_method_g"], "g", f"Cf = {comp['cf_used']:.3f}"),
        ("CO2 fixed - species stoichiometry (cross-check)", A["co2_stoich_method_g"], "g", f"{P['stoich_factor']} g/g"),
        ("Difference between methods", A["co2_diff_pct"], "%", "warning if >10%"),
        ("Team value 1.83 g/g (DOI 2014, NOT verified)", A["co2_doi2014_unverified_g"], "g", "comparison only"),
        ("Unused CO2", A["co2_unused_g"], "g", ""), ("Carbon utilisation efficiency", A["cue_pct"], "%", "fixed / supplied"),
        ("O2 - elemental stoichiometry", A["o2_stoich_g"], "g", f"PQ_stoich = {comp['pq_stoich']:.3f}, {comp['o2_g_per_g']:.3f} g/g"),
        ("O2 - PQ method (cross-check)", A["o2_pq_g"], "g", f"PQ = {P['pq']}"),
        ("O2 - team value 1.9 g/g (NOT verified)", A["o2_doi2014_unverified_g"], "g", "comparison only"),
        ("O2 volume (ideal gas at mean site T, P)", A["o2_L"], "L", f"{A['o2_L']/1000:.3f} m3"),
        ("O2 per day", A["o2_stoich_g"] / days, "g/day", f"{R['o2_check_L_per_day']:.2f} L/day"),
        ("Carbon stored in biomass (temporary)", A["carbon_in_biomass_g"], "g C", P["biomass_fate"]),
        ("Permanent sequestration", A["carbon_in_biomass_g"] if P["longterm_storage_proven"] else 0.0, "g C",
         "only if a long-term storage pathway is proven"),
    ], columns=["quantity", "value", "unit", "note"]).round(3), hide_index=True, width="stretch")
    st.caption("The two CO₂ methods and the two O₂ methods are cross-checks and are never added. The 1.83 factor equals 0.50 × 44/12 exactly "
               "(Chisti 2007), so it is not independent of the carbon-content method. O₂ figures are stoichiometric, not a change in city air.")
    if P.get("do_meas") is not None and P["do_meas"] > P["do_warn"]:
        st.warning(f"Measured DO {P['do_meas']} mg/L exceeds the literature 'high DO' level ({P['do_warn']} mg/L, C. vulgaris) - risk of photo-inhibition / photorespiration.")
    st.caption("Dissolved O₂ is not simulated (no verified kLa); enter a measured DO to check it.")

# ------------------------------------------------------------------ Cooling & HVAC
with tabs[5]:
    st.subheader("Cooling loop - evaporative media in front of the condenser")
    plot(ch.humidity_paradox(R))
    c1, c2 = st.columns(2)
    plot(ch.scatter_rh(R, "condensate_L", "Condensate (L/h)", "Humidity vs condensate (hourly, AC on)", ch.C[0]), where=c1)
    plot(ch.scatter_rh(R, "dT_media", "Media limit eff(T-Twb) (K)", "Humidity vs evaporative cooling potential", ch.C[1]), where=c2)
    plot(ch.humidity_vs_saving(R))
    st.dataframe(pd.DataFrame([
        ("Condenser inlet temperature BEFORE (mean, AC on)", A["mean_T_cond_before"], "C"),
        ("Condenser inlet temperature AFTER (mean, AC on)", A["mean_T_cond_after"], "C"),
        ("HVAC power/energy BEFORE", A["hvac_before_kWh"], "kWh"),
        ("HVAC energy AFTER", A["hvac_before_kWh"] - A["hvac_gross_saving_kWh"], "kWh"),
        ("Gross HVAC saving (empirical slope)", A["hvac_gross_saving_kWh"], "kWh"),
        ("Gross HVAC saving (Carnot cross-check)", A["hvac_saving_carnot_kWh"], "kWh"),
        ("Media fan penalty", A["fan_penalty_kWh"], "kWh"),
        ("Water evaporated on media", A["media_evap_L"], "L"),
    ], columns=["quantity", "value", "unit"]).round(2), hide_index=True, width="stretch")
    st.markdown("**Media before the coil (baseline) vs direct coil spray (alternative experimental option)**")
    st.dataframe(pd.DataFrame([
        ("Corrosion", "Lower: fins stay dry; only humidified air reaches them", "Higher: repeated wetting + coastal salts/dust on Al fins"),
        ("Scaling", "Deposits form on the replaceable pad", "Deposits form on the fins and reduce heat transfer"),
        ("Cleaning", "Pad is removable / replaceable", "Requires coil cleaning"),
        ("Maintenance", "Pad replacement, drain pan, filter", "Nozzles clog; coil cleaning"),
        ("Cost", "Pad + frame + drain pan (needs quotation)", "Nozzles/emitters (needs quotation)"),
        ("Safety", "Air break + no aerosol; keep pad from stagnant water (Legionella is reported in AC condensate)", "Aerosol generation - higher Legionella exposure risk"),
        ("Electrical wetting risk", "Low with drain pan and splash guard", "Higher near fan motor/terminals"),
        ("Warranty", "Check with manufacturer (external add-on)", "Likely to conflict with manufacturer warranty - verify"),
    ], columns=["criterion", "Evaporative media (baseline)", "Direct coil spray (alternative experimental)"]), hide_index=True, width="stretch")
    st.markdown("**Water quality: condensate vs Jeddah tap water** (published values)")
    st.dataframe(pd.DataFrame([
        ("TDS (mg/L)", "max 203 (AlGhamdi 2024, Jeddah)", "mean 194 ± 52 (Hussein & Magram 2012)", "190-240 (Khan 2023, preprint)"),
        ("EC (uS/cm)", "max 405", "mean 321 ± 94", "-"),
        ("Hardness (mg/L)", "not reported", "mean 43.7 ± 11.7", "-"),
        ("Chloride (mg/L)", "'almost non-existent'", "mean 85.7 ± 35.4", "27-36"),
    ], columns=["parameter", "AC condensate, Jeddah", "Jeddah tap (storage tanks)", "AC condensate, Bangladesh"]), hide_index=True, width="stretch")
    st.caption("In Jeddah the published condensate TDS maximum is similar to desalinated tap water, so a lower-salt advantage is NOT demonstrated. "
               "Low chloride may reduce scaling/corrosion potential, but corrosion is not impossible: coastal salt and dust accumulate on fins, "
               "and repeated wetting raises corrosion risk.")

# ------------------------------------------------------------------ Energy
with tabs[6]:
    st.subheader("Energy loop")
    plot(ch.energy_bars(R))
    st.dataframe(pd.DataFrame([("HVAC compressor & fans BEFORE", A["hvac_before_kWh"]), ("Gross HVAC saving", A["hvac_gross_saving_kWh"]),
                               ("Media fan penalty", A["fan_penalty_kWh"]), ("PBR circulation pump + air pump (+LED)", A["pbr_only_kWh"]),
                               ("Sensors + controller", A["control_kWh"]), ("Overflow water pump (gravity)", 0.0),
                               ("PV production (separate)", A["pv_kWh"]), ("NET electricity impact", A["net_electricity_kWh"])],
                              columns=["item", "kWh"]).round(2), hide_index=True, width="stretch")
    if A["net_electricity_kWh"] < 0:
        st.error("NEGATIVE net electricity: the reactor and media penalty consume more than the condenser pre-cooling saves under these inputs.")

# ------------------------------------------------------------------ Economics
with tabs[7]:
    st.subheader("Techno-economic analysis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Annual electricity saving value", f"{E['annual_electricity_saving_SAR']:,.0f} SAR")
    c2.metric("Annual operating cost (priced items)", f"{E['annual_operating_cost_SAR']:,.0f} SAR")
    c3.metric("Net annual benefit", f"{E['net_annual_benefit_SAR']:,.0f} SAR")
    c1.metric("Water reuse value", f"{E['water_reuse_value_SAR']:,.0f} SAR" if E["water_valued"] else "not valued (no tariff entered)")
    c2.metric("Biomass revenue", "0 SAR (no documented product/market/price)" if not P.get("biomass_price") else f"{E['biomass_revenue_SAR']:,.0f} SAR")
    c3.metric("Simple payback", f"{E['simple_payback_years']:.1f} yr" if E["simple_payback_years"] else "not computable")
    st.info(f"Allowable CAPEX for payback within {P['eval_years']} years: **{E['allowable_capex_SAR']:,.0f} SAR** "
            "(0 means the system never pays back under these inputs). Missing CAPEX items: " + (", ".join(E["capex_missing"]) or "none") +
            ". No prices were invented: enter dated quotations in the sidebar.")
    st.caption(f"Tariff {P['tariff']} SAR/kWh (government sector, ECRA 2018; confirm on the current SERA/SEC page). "
               f"BG-11 chemicals used: {E['nutrient_kg']:.2f} kg over the period.")

# ------------------------------------------------------------------ Sensitivity
with tabs[8]:
    st.subheader("Sensitivity analysis (one-at-a-time)")
    st.caption("Each parameter is moved to its low and high value with everything else fixed. ~37 full simulations.")
    if st.button("Run sensitivity analysis"):
        with st.spinner("Running..."):
            q = copy.deepcopy(P); q["period"] = "annual"
            st.session_state["sens"] = sens_mod.run(q)
    if "sens" in st.session_state:
        S = st.session_state["sens"]
        for out, t in [("net_benefit_SAR", "Net annual benefit (SAR)"), ("biomass_kg", "Biomass produced (kg/yr)"),
                       ("net_energy_kWh", "Net electricity (kWh/yr)"),
                       ("payback_or_allowable_capex", "Payback (yr) - or allowable CAPEX (SAR) when CAPEX is blank")]:
            plot(ch.tornado(S, out, t))
        st.dataframe(S.round(3), width="stretch", hide_index=True)

# ------------------------------------------------------------------ Validation
with tabs[9]:
    st.subheader("Validation targets (from the submission - treated as targets, not facts)")
    for v in VAL:
        icon = {"Pass": "✅", "Warning": "⚠️", "Fail": "❌"}[v["status"]]
        st.markdown(f"{icon} **{v['status']}** — {v['target']}  \n{v['value']} · _{v['basis']}_")

# ------------------------------------------------------------------ Engineering view
with tabs[10]:
    st.subheader("Engineering view - equations, intermediate values, confidence")
    st.dataframe(pd.DataFrame(rp.EQUATIONS, columns=["name", "equation", "unit", "source"]), hide_index=True, width="stretch")
    comp = R["comp"]
    st.markdown("**Biomass composition (from formula CH1.83O0.48N0.11P0.01)**")
    st.json({k: round(v, 4) for k, v in comp.items()})
    st.markdown("**Annual/period totals (all intermediate values)**")
    st.dataframe(rp.summary_table(R).astype({"value": "str"}), hide_index=True, width="stretch")
    st.markdown("**Monthly table**")
    st.dataframe(R["monthly"].round(3), hide_index=True, width="stretch")
    st.markdown(f"Tank mass-balance closure error: `{R['tank'].closure_error():.2e} L`")

# ------------------------------------------------------------------ Research audit
with tabs[11]:
    st.subheader("Research audit - source ledger")
    L = rp.ledger_table()
    f1, f2 = st.columns(2)
    types = f1.multiselect("Evidence type", sorted(L["data_type"].unique()), default=sorted(L["data_type"].unique()))
    grp = f2.multiselect("Group", sorted({e["group"] for e in config.LEDGER.values()}))
    view = L[L["data_type"].isin(types)]
    if grp:
        view = view[view["key"].map(lambda k: config.LEDGER[k]["group"]).isin(grp)]
    st.dataframe(view, hide_index=True, width="stretch")
    st.markdown("**Citations**")
    for kk, c in config.CITATIONS.items():
        st.markdown(f"- **[{kk}]** {c['text']} " + (f"doi:{c['doi']} " if c["doi"] else "") + (f"[link]({c['url']})" if c["url"] else ""))

# ------------------------------------------------------------------ Export
with tabs[12]:
    st.subheader("Export")
    st.download_button("Hourly results (CSV)", R["hourly"].to_csv(index=False).encode(), "hydroloop_hourly.csv", "text/csv")
    if st.button("Prepare Excel + PDF report"):
        with st.spinner("Building files..."):
            st.session_state["xlsx"] = rp.excel_bytes(R, st.session_state.get("sens"))
            try:
                st.session_state["pdf"] = rp.pdf_bytes(R, scenario)
            except Exception as ex:
                st.session_state["pdf"] = None
                st.warning(f"PDF export unavailable ({ex}); install fpdf2.")
    if st.session_state.get("xlsx"):
        st.download_button("Full workbook (Excel)", st.session_state["xlsx"], "hydroloop_results.xlsx")
    if st.session_state.get("pdf"):
        st.download_button("Report (PDF, English)", st.session_state["pdf"], "hydroloop_report.pdf", "application/pdf")
    st.caption("Exports reflect the inputs at the moment you press the button.")
