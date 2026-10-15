"""Unit and edge-case tests (Section 30). Run: pytest -q"""
import copy, math, os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config, climate_model as cm, simulation as sim, health, hvac_model as hv, overflow_hydraulics as oh
import carbon_oxygen as co, energy_model as em, psychrometrics as ps, algae_model as am

BASE = config.defaults()
WX = cm.build_noaa_year(BASE)


def run(**ov):
    p = copy.deepcopy(BASE)
    p.update(ov)
    wx = WX if not ({"rh_offset", "t_offset", "facade_az"} & set(ov)) else cm.build_noaa_year(p)
    return sim.run(p, wx)


@pytest.fixture(scope="module")
def ref():
    return run()


# ---------------------------------------------------------------- conservation
def test_tank_mass_balance(ref):
    assert abs(ref["tank"].closure_error()) < 1e-6


def test_reactor_and_overflow_not_double_counted(ref):
    a = ref["annual"]
    lhs = a["condensate_L"]
    rhs = (a["prefilter_loss_L"] + a["condensate_to_reactor_L"] + a["cooling_L"] + a["overflow_L"] + a["spill_L"] + a["tank_change_L"])
    assert abs(lhs - rhs) < 1e-6
    assert abs(a["overflow_L"] - (a["media_evap_L"] + a["media_drain_L"])) < 1e-6


def test_annual_is_sum_of_hours_not_ideal_day(ref):
    df = ref["hourly"]
    assert len(df) == 8760
    assert abs(ref["annual"]["condensate_L"] - df["condensate_L"].sum()) < 1e-9
    assert abs(ref["monthly"]["condensate_L"].sum() - df["condensate_L"].sum()) < 1e-6
    best_day = ref["daily"]["condensate_L"].max()
    assert ref["annual"]["condensate_L"] < best_day * 365        # not one ideal day x 365


def test_biomass_balance(ref):
    df = ref["hourly"]
    produced = ref["produced_g"]
    assert abs(produced - df["net_g"].sum()) < 1e-6 * max(1, abs(produced))


def test_net_energy_subtracts_reactor(ref):
    a = ref["annual"]
    assert abs(a["net_electricity_kWh"] - (a["hvac_gross_saving_kWh"] - a["fan_penalty_kWh"] - a["pbr_kWh"])) < 1e-6


def test_overflow_pump_is_zero():
    assert em.OVERFLOW_PUMP_W == 0.0
    assert em.hourly_loads_w(BASE, 20, 0.5, 12)["overflow_pump"] == 0.0


# ---------------------------------------------------------------- edge cases
def test_zero_condensate():
    r = run(cond_mode="measured", cond_meas_lph=0.0, tank_init=0.0)
    a = r["annual"]
    assert a["condensate_L"] == 0 and a["overflow_L"] == 0 and a["media_evap_L"] == 0
    assert a["external_L"] > 0 and a["coverage_pct"] < 1
    assert a["hvac_gross_saving_kWh"] == 0


def test_zero_growth_means_zero_co2_and_o2():
    r = run(y_ph=0.0)
    df = r["hourly"]
    assert df["gross_g"].sum() == 0
    a = r["annual"]
    assert a["co2_carbon_method_g"] == 0 and a["o2_stoich_g"] == 0 and a["o2_pq_g"] == 0


def test_zero_co2_means_no_growth():
    r = run(co2_ppm=0.0)
    assert r["hourly"]["gross_g"].sum() == 0
    assert r["annual"]["co2_carbon_method_g"] == 0


def test_co2_fixed_never_exceeds_available(ref):
    df = ref["hourly"]
    assert (df["co2_used_g"] <= df["co2_transferable_g"] + 1e-9).all()
    assert (df["co2_transferable_g"] <= df["co2_supplied_g"] + 1e-9).all()
    assert ref["annual"]["co2_carbon_method_g"] <= ref["annual"]["co2_supplied_g"] + 1e-9


def test_air_pump_off():
    r = run(vvm=0.0)
    assert r["annual"]["co2_supplied_g"] == 0
    assert r["hourly"]["gross_g"].sum() == 0
    hl = health.daily_health(r)
    assert (hl["Aeration"] == "Critical").all()


def test_zero_head_no_overflow_and_hydraulic_limit():
    r = run(ovf_head=0.0)
    a = r["annual"]
    assert a["overflow_L"] == 0
    assert a["spill_L"] > 0
    assert any(f == "Hydraulic Limited" for f, _ in health.limits(r)["system_flags"])


def test_blocked_orifice():
    r = run(orifice_d=0.0)
    assert r["annual"]["overflow_L"] == 0 and r["annual"]["spill_L"] > 0


def test_overflow_only_above_lip():
    p = copy.deepcopy(BASE)
    p.update(cond_mode="measured", cond_meas_lph=1.0, tank_init=0.0, dil_rate=0.0, sample_L=0.0)
    r = sim.run(p, WX)
    df = r["hourly"]
    lip = p["ovf_level"] * p["tank_L"]
    first = df.index[df["overflow_L"] > 0][0]
    assert df.loc[first - 1, "tank_L"] <= lip + 1e-9
    assert (df.loc[: first - 1, "overflow_L"] == 0).all()


def test_full_tank_spills_when_capacity_small():
    r = run(orifice_d=0.0005, tank_init=1.0)
    assert r["annual"]["spill_L"] > 0


def test_humidity_95():
    r = run(rh_offset=35.0)
    a = r["annual"]
    assert a["condensate_L"] > run()["annual"]["condensate_L"]
    assert r["hourly"]["dT_media"].mean() < run()["hourly"]["dT_media"].mean()


def test_outdoor_45C():
    p = copy.deepcopy(BASE)
    p["noaa_tmax"] = [45.0] * 12
    r = sim.run(p, cm.build_noaa_year(p))
    assert r["hourly"]["T"].max() >= 44.9
    assert r["hourly"]["hvac_before_kW"].max() > run()["hourly"]["hvac_before_kW"].max()


def test_reactor_above_strain_range_stops_growth():
    p = copy.deepcopy(BASE)
    g = am.growth_step(1.0, 200, 5, 46.0, 800, p, am.geometry(p), co.composition(p), 1e6)
    assert g["fT"] == 0 and g["gross"] == 0 and g["limit"] in ("Temperature",)


def test_zero_nutrients():
    r = run(nutrient_strength=0.0)
    assert r["hourly"]["gross_g"].sum() == 0
    assert r["hourly"]["N"].max() == 0


def test_cooling_never_below_wet_bulb():
    p = copy.deepcopy(BASE)
    ac = hv.ACUnit(p, 101325)
    T, W = 35.0, ps.w_from_rh(35, 0.5, 101325)
    twb = ps.wet_bulb(T, W, 101325)
    pc = ac.precool(T, W, twb, 1.0, 1e6)      # unlimited water
    assert pc["t_in_after"] >= twb - 1e-9
    assert pc["evap_L"] <= 1e6


def test_evaporated_never_exceeds_delivered(ref):
    df = ref["hourly"]
    assert (df["media_evap_L"] <= df["overflow_L"] + 1e-9).all()


def test_media_effectiveness_zero():
    r = run(media_eff=0.0)
    assert r["annual"]["media_evap_L"] == 0 and r["annual"]["hvac_gross_saving_kWh"] == 0
    assert r["annual"]["fan_penalty_kWh"] > 0          # pad still installed -> penalty, shown


def test_very_high_pump_power_gives_negative_net():
    r = run(pump_min_w=500.0)
    assert r["annual"]["net_electricity_kWh"] < 0
    assert any(f == "Energy Limited" for f, _ in health.limits(r)["system_flags"])


def test_water_used_not_more_than_available(ref):
    df = ref["hourly"]
    assert (df["makeup_from_tank_L"] <= df["makeup_demand_L"] + 1e-9).all()
    assert (df["tank_L"] >= -1e-9).all() and (df["tank_L"] <= BASE["tank_L"] + 1e-9).all()


# ---------------------------------------------------------------- physics checks
def test_static_pressure_per_metre():
    r = oh.solve(dict(BASE, ovf_head=1.0, rho_w=1000.0))
    assert abs(r["static_bar"] - 0.0981) < 1e-4
    assert abs(r["v_torricelli"] - math.sqrt(2 * 9.80665)) < 1e-9


def test_orifice_flow_limited_by_head():
    small = oh.solve(dict(BASE, orifice_d=0.002))["Q_Lph"]
    big = oh.solve(dict(BASE, orifice_d=0.004))["Q_Lph"]
    assert big > small        # smaller outlet = less flow, never more energy


def test_stoichiometry():
    c = co.composition(BASE)
    assert abs(c["co2_g_per_g_cf"] - 0.50 * 44.009 / 12.011) < 1e-9        # 1.832 g/g
    assert 1.30 < c["pq_stoich"] < 1.40                                     # nitrate-based
    nh4 = co.composition(dict(BASE, n_source="ammonium"))
    assert nh4["pq_stoich"] < c["pq_stoich"]


def test_o2_ideal_gas():
    v = co.o2_volume_L(31.998, 0.0, 101325)
    assert abs(v - 22.414) < 0.01


def test_psychrometrics_reference_points():
    P = 101325
    w = ps.w_from_rh(25, 0.5, P)
    assert abs(w - 0.00988) < 2e-4                   # ASHRAE chart
    assert abs(ps.wet_bulb(35, 0.019, P) - 26.8) < 0.3


def test_carbon_limit_flag(ref):
    assert health.limits(ref)["bio_limit"] in ("Carbon Limited", "Temperature Limited", "Phosphorus Limited", "Light Limited")


def test_validation_targets_have_status(ref):
    v = health.validation(ref)
    assert all(x["status"] in ("Pass", "Warning", "Fail") for x in v)
