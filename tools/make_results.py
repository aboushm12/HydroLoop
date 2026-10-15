"""Regenerates results/ (reference outputs, scenarios, design variants, sensitivity)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config, simulation as sim, health, sensitivity as sm, reporting as rp, climate_model as cm

def pack(r):
    a, e = r["annual"], r["econ"]; L = health.limits(r); V = health.validation(r); HL = health.daily_health(r)
    keys = ["days", "condensate_L", "condensate_to_reactor_L", "reactor_demand_L", "external_L", "coverage_pct", "overflow_L", "media_evap_L",
            "media_drain_L", "spill_L", "mean_T_cond_before", "mean_T_cond_after", "mean_dT_cond_active", "hvac_before_kWh", "hvac_gross_saving_kWh",
            "hvac_saving_carnot_kWh", "fan_penalty_kWh", "hvac_net_saving_kWh", "pbr_only_kWh", "control_kWh", "pbr_kWh", "net_electricity_kWh",
            "biomass_produced_g", "biomass_harvested_g", "vol_productivity_g_L_d", "areal_productivity_g_m2_d", "co2_supplied_g", "co2_transferable_g",
            "co2_gross_uptake_g", "co2_carbon_method_g", "co2_stoich_method_g", "co2_diff_pct", "o2_stoich_g", "o2_pq_g", "o2_diff_pct", "o2_L",
            "cue_pct", "carbon_in_biomass_g", "net_electricity_co2_kg", "bg11_chem_g", "cooling_L"]
    d = {k: float(a[k]) for k in keys}
    h = r["hourly"]
    d.update(net_SAR=float(e["net_annual_benefit_SAR"]), elec_SAR=float(e["annual_electricity_saving_SAR"]), opex_SAR=float(e["annual_operating_cost_SAR"]),
             allowable_capex=float(e["allowable_capex_SAR"]), bio_limit=L["bio_limit"], bio_share=float(L["bio_share"]),
             bio_shares={k: float(v) for k, v in L["bio_shares"].items()}, flags=L["system_flags"], validation=V,
             health_counts=HL["status"].value_counts().to_dict(), Tr_max=float(h["T_r"].max()),
             Tr_in_range=float(((h["T_r"] >= r["params"]["t_range_lo"]) & (h["T_r"] <= r["params"]["t_range_hi"])).mean()),
             X_end=float(r["X_end"]), X_mean=float(h["X"].mean()),
             hyd=dict(Q_Lph=r["hydraulics"].get("Q_Lph", 0), static_bar=r["hydraulics"]["static_bar"], v_t=r["hydraulics"]["v_torricelli"],
                      h_net=r["hydraulics"]["h_net_m"], v_o=r["hydraulics"]["v_orifice"], h_loss=r["hydraulics"]["h_loss_m"]),
             mean_overflow_Lph=float(h.loc[h["overflow_L"] > 0, "overflow_L"].mean()) if (h["overflow_L"] > 0).any() else 0.0,
             conf=rp.output_confidence(r),
             monthly=r["monthly"][["month", "T", "RH", "dT_psy", "condensate_L", "overflow_L", "media_evap_L", "dT_cond_active", "hvac_saving_kWh",
                                   "fan_kWh", "pbr_kWh", "ctrl_kWh", "T_r_max", "net_biomass_g", "hours"]].round(3).to_dict("records"))
    return d

VARIANTS = {
    "Ref + CO2-enriched air 1.5%": {"co2_source": "enriched"},
    "Ref + enriched + panel cooling with condensate": {"co2_source": "enriched", "cool_on": True},
    "Ref + enriched + cooling + 2x BG-11": {"co2_source": "enriched", "cool_on": True, "nutrient_strength": 2.0},
    "Ref + east facade": {"facade_az": -90.0},
    "Ref, AC 5 TR": {"ac_tr": 5.0},
    "Ref, media at 3 m/s face velocity": {"media_face_v": 3.0},
    "Ref, measured 1.5 L/h (example)": {"cond_mode": "measured", "cond_meas_lph": 1.5},
    "Ref, summer (Jun-Aug)": {"period": "summer"},
    "Ref, winter (Dec-Feb)": {"period": "winter"},
}
if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    out = {}
    for s in ["Conservative", "Reference", "Optimistic"]:
        out[s] = pack(sim.run(config.scenario_params(s)))
    for k, ov in VARIANTS.items():
        p = config.defaults(); p.update(ov); out[k] = pack(sim.run(p))
    S = sm.run(config.defaults())
    S.to_csv("results/sensitivity_reference.csv", index=False)
    out["sens_rank"] = {o: S[S.output == o].sort_values("swing", ascending=False)[["label", "low", "high", "at_low", "at_high", "base", "swing"]].to_dict("records")
                        for o in S.output.unique()}
    r = sim.run(config.defaults())
    out["comp"] = {k: float(v) for k, v in r["comp"].items()}
    out["climate"] = cm.monthly_summary(cm.build_noaa_year(config.defaults())).round(3).reset_index().to_dict("records")
    json.dump(out, open("results/results_summary.json", "w"), indent=1, default=str)
    open("results/hydroloop_reference.xlsx", "wb").write(rp.excel_bytes(r, S))
    open("results/hydroloop_reference_report.pdf", "wb").write(rp.pdf_bytes(r, "Reference"))
    r["hourly"].to_csv("results/hourly_reference.csv", index=False)
    print("results written")
