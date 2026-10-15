"""HydroLoop integrated hourly simulation: Water Loop + Bio Loop + Carbon Loop +
Oxygen production + Energy Loop + Cooling Loop + Economic Loop, in one model.

All annual values are SUMS OF SIMULATED HOURS (never one ideal day x 365).
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

import psychrometrics as ps
import climate_model as cm
import hvac_model as hv
import overflow_hydraulics as oh
import algae_model as am
import carbon_oxygen as co
import energy_model as em
import economic_model as ec
import water_balance as wb
import config

R_DA = 287.055


def period_index(p: dict, n_hours: int) -> np.ndarray:
    per = p["period"]
    hours = np.arange(n_hours)
    month = np.repeat(np.concatenate([np.full(d * 24, m + 1) for m, d in enumerate(cm.DAYS_IN_MONTH)]), 1)[:n_hours]
    if per == "annual":
        return hours
    if per == "summer":
        return hours[np.isin(month, [6, 7, 8])]
    if per == "winter":
        return np.concatenate([hours[month == 12], hours[np.isin(month, [1, 2])]])
    if per == "month":
        return hours[month == int(p["period_month"])]
    length = {"24h": 24, "7d": 168, "30d": 720}[per]
    start = (int(p["start_doy"]) - 1) * 24
    return np.arange(start, start + length) % n_hours


def run(p: dict, wx: pd.DataFrame | None = None) -> dict:
    if wx is None:
        wx = cm.build_noaa_year(p)
    idx = period_index(p, len(wx))
    P0 = float(wx["P"].iloc[0])
    geo = am.geometry(p)
    V, A = geo["V_L"], geo["A_m2"]
    comp = co.composition(p)
    ac = hv.ACUnit(p, P0)
    hyd = oh.solve(p)
    cap_Lph = hyd.get("Q_Lph", 0.0)
    tank = wb.Tank(p)

    n_bg = p["nutrient_strength"]
    N_feed, P_feed = am.BG11_N_MG_L * n_bg, am.BG11_P_MG_L * n_bg
    X, N, Pp = p["x0"], N_feed, P_feed
    T_r = float(wx["T"].iloc[idx[0]])
    harvested_g = sampled_g = 0.0
    bg11_chem_g = sum(am.BG11.values()) * n_bg * V        # initial fill
    X_start = X
    rec = []
    harvest_vol = p["dil_rate"] * V

    records = wx.to_dict("records")
    for i in idx:
        r = records[i]
        T, W, P, Twb, hour = r["T"], r["W"], r["P"], r["Twb"], int(r["hour"])
        # ---------------- condensate
        lph, info = ac.condensate_lph(T, W, hour)
        lph *= p["cond_scale"]
        rtf = info["rtf"]
        # ---------------- reactor water demand
        air_m3h = p["vvm"] * V * 0.06
        m_da = air_m3h * P / (R_DA * (T + 273.15))                         # kg dry air / h
        evap_kg = m_da * max(ps.w_sat(T_r, P) - W, 0.0)                    # exits saturated at T_r
        hfg_r = ps.latent_heat(T_r)
        q_evap_W = evap_kg * hfg_r * 1000.0 / 3600.0
        is_harvest = hour == int(p["harvest_hour"]) and p["dil_rate"] > 0
        makeup = evap_kg + p["sample_L"] / 24.0 + p["blowdown_L"] / 168.0 + (harvest_vol if is_harvest else 0.0)
        # optional evaporative panel cooling (clean condensate)
        G_f = r["GT"]
        _, T_eq0, UA = am.thermal_step(T_r, T, G_f, p, geo, q_evap_W)
        cool_req_L = 0.0
        if p["cool_on"] and T_eq0 > p["cool_set"]:
            cool_req_L = UA * (T_eq0 - p["cool_set"]) * 3600.0 / (hfg_r * 1000.0)
        # ---------------- tank
        t = tank.step(lph, makeup, cool_req_L, cap_Lph)
        cool_W = t["cooling_L"] * hfg_r * 1000.0 / 3600.0
        T_r, T_eq, _ = am.thermal_step(T_r, T, G_f, p, geo, q_evap_W, cool_W=cool_W)
        # ---------------- condenser pre-cooling with the overflow
        pc = ac.precool(T, W, Twb, rtf, t["overflow_L"])
        p_before, s_emp, s_car = ac.savings_kw(T, pc["dT"], rtf)
        saving = s_emp if p["hvac_method"] == "empirical" else s_car
        # ---------------- light & growth
        ppfd = r["PPFD_T"] * p["wall_tau"] * (1 - p["shade"]) * p["light_scale"]
        loads = em.hourly_loads_w(p, V, A, hour)
        if loads["led"] > 0:
            ppfd += p["led_ppfd"]
        gas = co.gas_supply_g_per_h(p, V, T_r, P)
        g = am.growth_step(X, N, Pp, T_r, ppfd, p, geo, comp, gas["transferable"])
        X = max(X + g["net"] / V, 0.0)
        N = max(N - g["n_used_mg"] / V, 0.0)
        Pp = max(Pp - g["p_used_mg"] / V, 0.0)
        # sampling removes culture (replaced by makeup water)
        s_g = X * p["sample_L"] / 24.0
        sampled_g += s_g
        X = max(X - s_g / V, 0.0)
        h_g = 0.0
        if is_harvest:
            h_g = X * harvest_vol
            harvested_g += h_g
            f = harvest_vol / V
            X *= (1 - f)
            N += (N_feed - N) * f
            Pp += (P_feed - Pp) * f
            bg11_chem_g += sum(am.BG11.values()) * n_bg * harvest_vol
        pv = em.pv_w(p, r["GHI"])
        pbr_w = loads["circ"] + loads["air"] + loads["led"]
        ctrl_w = loads["sensors"] + loads["ctrl"]
        rec.append(dict(
            month=int(r["month"]), day=int(r["day"]), hour=hour, doy=int(r["doy"]),
            T=T, RH=r["RH"] * 100, W_gkg=W * 1000, Twb=Twb, dT_psy=T - Twb, GT=G_f, PPFD=ppfd,
            rtf=rtf, condensate_L=lph, w_in_gkg=info.get("w_in", float("nan")) * 1000,
            cap_limited=info.get("cap_limited", False),
            makeup_demand_L=makeup, makeup_from_tank_L=t["makeup_L"], external_L=t["external_L"],
            evap_reactor_L=evap_kg, cooling_req_L=cool_req_L, cooling_L=t["cooling_L"],
            tank_L=t["level_L"], overflow_L=t["overflow_L"], spill_L=t["spill_L"],
            prefilter_loss_L=t["prefilter_loss_L"],
            media_evap_L=pc["evap_L"], media_drain_L=pc["drain_L"], dT_cond=pc["dT"],
            dT_media=pc["dT_media"], dT_water=pc["dT_water"], media_limit=pc["limit"],
            T_cond_in_after=pc["t_in_after"], hvac_before_kW=p_before, hvac_after_kW=p_before - saving,
            saving_emp_kW=s_emp, saving_carnot_kW=s_car, fan_penalty_kW=pc["fan_penalty_kw"],
            T_r=T_r, T_eq=T_eq, X=X, N=N, P_mgL=Pp, gross_g=g["gross"], maint_g=g["maint"], net_g=g["net"],
            fT=g["fT"], fpH=g["fpH"], T_in_data=g["T_in_data"], limit=g["limit"], light_pot_g=g["light_pot"],
            absf=g["absf"], co2_supplied_g=gas["supplied"], co2_transferable_g=gas["transferable"],
            co2_used_g=g["co2_used_g"], co2_demand_pot_g=g["light_pot"] * g["fT"] * g["fpH"] * comp["co2_g_per_g_cf"],
            harvest_g=h_g, sample_g=s_g, n_need_mg=g["n_used_mg"], p_need_mg=g["p_used_mg"],
            pbr_W=pbr_w, ctrl_W=ctrl_w, pv_W=pv, P_Pa=P,
        ))
    df = pd.DataFrame(rec)
    produced_g = harvested_g + sampled_g + (X - X_start) * V
    res = dict(hourly=df, params=p, geo=geo, comp=comp, hydraulics=hyd, tank=tank,
               X_end=X, N_end=N, P_end=Pp, produced_g=produced_g, harvested_g=harvested_g, sampled_g=sampled_g,
               bg11_chem_g=bg11_chem_g, n_hours=len(df), wx_source=wx.attrs.get("source", ""))
    res.update(summarise(res))
    return res


# ------------------------------------------------------------------- aggregation
def summarise(res: dict) -> dict:
    df, p, geo = res["hourly"], res["params"], res["geo"]
    V = geo["V_L"]
    days = len(df) / 24.0
    T_mean = float(df["T"].mean())
    P_mean = float(df["P_Pa"].mean())
    fix = co.fixation_report(res["produced_g"], df["co2_used_g"].sum(), p, T_mean, P_mean)
    hvac_gross = df["hvac_before_kW"].sum() - df["hvac_after_kW"].sum()
    fan = df["fan_penalty_kW"].sum()
    pbr = df["pbr_W"].sum() / 1000.0
    ctrl = df["ctrl_W"].sum() / 1000.0
    pv = df["pv_W"].sum() / 1000.0
    hvac_net = hvac_gross - fan
    net_elec = hvac_net - pbr - ctrl + (pv if p["pv_on"] else 0.0)
    annual = dict(
        days=days,
        condensate_L=df["condensate_L"].sum(),
        condensate_to_reactor_L=df["makeup_from_tank_L"].sum(),
        reactor_demand_L=df["makeup_demand_L"].sum(),
        external_L=df["external_L"].sum(),
        cooling_L=df["cooling_L"].sum(),
        overflow_L=df["overflow_L"].sum(),
        media_evap_L=df["media_evap_L"].sum(),
        media_drain_L=df["media_drain_L"].sum(),
        spill_L=df["spill_L"].sum(),
        prefilter_loss_L=df["prefilter_loss_L"].sum(),
        tank_change_L=res["tank"].V - res["tank"].V0,
        shortage_hours=int((df["external_L"] > 1e-9).sum()),
        hvac_before_kWh=df["hvac_before_kW"].sum(), hvac_gross_saving_kWh=hvac_gross,
        hvac_saving_carnot_kWh=df["saving_carnot_kW"].sum(), fan_penalty_kWh=fan,
        hvac_net_saving_kWh=hvac_net, pbr_kWh=pbr + ctrl, pbr_only_kWh=pbr, control_kWh=ctrl, pv_kWh=pv,
        net_electricity_kWh=net_elec,
        biomass_produced_g=res["produced_g"], biomass_harvested_g=res["harvested_g"],
        bg11_chem_g=res["bg11_chem_g"],
        co2_supplied_g=df["co2_supplied_g"].sum(), co2_transferable_g=df["co2_transferable_g"].sum(),
        co2_gross_uptake_g=df["co2_used_g"].sum(), **{k: v for k, v in fix.items()},
    )
    annual["coverage_pct"] = 100.0 * annual["condensate_to_reactor_L"] / max(annual["reactor_demand_L"], 1e-9)
    annual["cue_pct"] = 100.0 * annual["co2_carbon_method_g"] / max(annual["co2_supplied_g"], 1e-9)
    annual["co2_unused_g"] = max(annual["co2_supplied_g"] - annual["co2_carbon_method_g"], 0.0)
    annual["vol_productivity_g_L_d"] = res["produced_g"] / V / max(days, 1e-9)
    annual["areal_productivity_g_m2_d"] = res["produced_g"] / geo["A_m2"] / max(days, 1e-9)
    annual["net_electricity_co2_kg"] = net_elec * p["grid_ef"]   # positive = avoided operational CO2 from electricity
    act = df[df["rtf"] > 0]
    annual["mean_dT_cond_active"] = float(act["dT_cond"].mean()) if len(act) else 0.0
    annual["mean_T_cond_before"] = float(act["T"].mean()) if len(act) else float("nan")
    annual["mean_T_cond_after"] = float(act["T_cond_in_after"].mean()) if len(act) else float("nan")
    annual["hrt_days"] = 1.0 / p["dil_rate"] if p["dil_rate"] > 0 else float("inf")
    econ = ec.evaluate(p, annual)
    daily = daily_table(df)
    monthly = monthly_table(df)
    return dict(annual=annual, econ=econ, daily=daily, monthly=monthly,
                o2_check_L_per_day=fix["o2_L"] / max(days, 1e-9))


def daily_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["month", "day"], sort=False)
    d = g.agg(condensate_L=("condensate_L", "sum"), makeup_demand_L=("makeup_demand_L", "sum"),
              makeup_from_tank_L=("makeup_from_tank_L", "sum"), external_L=("external_L", "sum"),
              overflow_L=("overflow_L", "sum"), spill_L=("spill_L", "sum"), media_evap_L=("media_evap_L", "sum"),
              tank_end_L=("tank_L", "last"), X_mean=("X", "mean"), X_end=("X", "last"), net_g=("net_g", "sum"),
              gross_g=("gross_g", "sum"), maint_g=("maint_g", "sum"), harvest_g=("harvest_g", "sum"),
              T_r_max=("T_r", "max"), T_r_mean=("T_r", "mean"), hvac_saving_kWh=("saving_emp_kW", "sum"),
              fan_kWh=("fan_penalty_kW", "sum"), pbr_Wh=("pbr_W", "sum"), ctrl_Wh=("ctrl_W", "sum"),
              co2_transferable_g=("co2_transferable_g", "sum"), co2_demand_pot_g=("co2_demand_pot_g", "sum"),
              N_end=("N", "last"), P_end=("P_mgL", "last"), n_need_mg=("n_need_mg", "sum"), p_need_mg=("p_need_mg", "sum"),
              doy=("doy", "first")).reset_index()
    return d


def monthly_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("month", sort=False)
    m = g.agg(T=("T", "mean"), RH=("RH", "mean"), dT_psy=("dT_psy", "mean"), condensate_L=("condensate_L", "sum"),
              reactor_L=("makeup_from_tank_L", "sum"), external_L=("external_L", "sum"), overflow_L=("overflow_L", "sum"),
              media_evap_L=("media_evap_L", "sum"), spill_L=("spill_L", "sum"), net_biomass_g=("net_g", "sum"),
              harvest_g=("harvest_g", "sum"), T_r_mean=("T_r", "mean"), T_r_max=("T_r", "max"),
              hvac_before_kWh=("hvac_before_kW", "sum"), hvac_saving_kWh=("saving_emp_kW", "sum"),
              hvac_saving_carnot_kWh=("saving_carnot_kW", "sum"), fan_kWh=("fan_penalty_kW", "sum"),
              pbr_kWh=("pbr_W", "sum"), ctrl_kWh=("ctrl_W", "sum"), co2_used_g=("co2_used_g", "sum"),
              hours=("hour", "count")).reset_index()
    m["pbr_kWh"] /= 1000.0
    m["ctrl_kWh"] /= 1000.0
    act = df[df["rtf"] > 0].groupby("month")["dT_cond"].mean()
    m["dT_cond_active"] = m["month"].map(act).fillna(0.0)
    return m
