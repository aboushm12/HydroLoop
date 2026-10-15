"""Algae Health Score (Section 8), 'What limits HydroLoop' (Section 27) and
Validation Targets (Section 25).

Health is NOT a cosmetic number: each factor is a ratio computed from the model
state against strain data (temperature/pH points) or mass-balance needs (C, N, P,
light vs maintenance). The status thresholds below are explicit DESIGN DEFINITIONS
(they classify, they do not add science) and are listed in assumptions.md.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import algae_model as am

ORDER = {"Healthy": 0, "Warning": 1, "Critical": 2}
THRESH = {  # design definitions
    "temp": (0.7, 0.3), "light": (2.0, 1.0), "ph": (0.8,), "co2": (1.0, 0.5), "dark": (0.5, 0.8),
}


def _status(v, hi, lo, higher_is_better=True):
    if higher_is_better:
        return "Healthy" if v >= hi else ("Warning" if v >= lo else "Critical")
    return "Healthy" if v <= hi else ("Warning" if v <= lo else "Critical")


def daily_health(res: dict) -> pd.DataFrame:
    df, p = res["hourly"], res["params"]
    day = df[df["PPFD"] > 0]
    rows = []
    for (m, d), g in df.groupby(["month", "day"], sort=False):
        gd = day[(day["month"] == m) & (day["day"] == d)]
        f = {}
        fT = float(gd["fT"].mean()) if len(gd) else float(g["fT"].mean())
        f["Temperature"] = (_status(fT, *THRESH["temp"]), f"mean daylight f_T = {fT:.2f}; T_r max {g['T_r'].max():.1f} C")
        ratio = g["gross_g"].sum() / max(g["maint_g"].sum(), 1e-12)
        f["Light"] = (_status(ratio, *THRESH["light"]), f"daily gross/maintenance = {ratio:.2f}")
        fpH = float(g["fpH"].iloc[0])
        inside = p["ph_pts"][0][0] <= p["ph"] <= p["ph_pts"][-1][0]
        f["pH"] = ("Healthy" if (fpH >= THRESH["ph"][0] and inside) else "Warning",
                   f"pH {p['ph']} -> relative mu {fpH:.2f}" + ("" if inside else " (outside published data 6-9)"))
        nend, need = g["N"].iloc[-1], g["n_need_mg"].sum() / res["geo"]["V_L"]
        f["Nitrogen"] = ("Critical" if nend <= 1e-6 else ("Warning" if nend < need else "Healthy"), f"N end {nend:.1f} mg/L vs daily need {need:.1f}")
        pend, pneed = g["P_mgL"].iloc[-1], g["p_need_mg"].sum() / res["geo"]["V_L"]
        f["Phosphorus"] = ("Critical" if pend <= 1e-6 else ("Warning" if pend < pneed else "Healthy"), f"P end {pend:.2f} mg/L vs daily need {pneed:.2f}")
        dem = g["co2_demand_pot_g"].sum()
        cr = g["co2_transferable_g"].sum() / dem if dem > 0 else 9.9
        f["CO2"] = (_status(cr, *THRESH["co2"]), f"CO2 transferable/potential demand = {cr:.2f}")
        f["Aeration"] = ("Healthy" if p["vvm"] > 0 else "Critical", f"{p['vvm']} vvm")
        dk = am.dark_fraction(float(g["X"].mean()), p)
        f["Biomass density"] = (_status(dk, *THRESH["dark"], higher_is_better=False), f"dark-zone fraction {dk:.2f} (k_abs is a design input)")
        if p.get("do_meas") is not None:
            f["Dissolved O2"] = ("Warning" if p["do_meas"] > p["do_warn"] else "Healthy", f"DO {p['do_meas']} mg/L (flag {p['do_warn']})")
        worst = max(f.items(), key=lambda kv: ORDER[kv[1][0]])
        rows.append(dict(month=m, day=d, status=worst[1][0], limiting=worst[0] if worst[1][0] != "Healthy" else "-",
                         **{k: v[0] for k, v in f.items()}, detail={k: v[1] for k, v in f.items()}))
    return pd.DataFrame(rows)


def limits(res: dict) -> dict:
    """Automatic 'What limits HydroLoop' classification."""
    df, a, e, p = res["hourly"], res["annual"], res["econ"], res["params"]
    lit = df[df["PPFD"] > 0]
    bio_share = lit["limit"].value_counts(normalize=True).to_dict() if len(lit) else {}
    bio_main = max(bio_share.items(), key=lambda kv: kv[1]) if bio_share else ("Light", 1.0)
    name_map = {"Carbon": "Carbon Limited", "Nitrogen": "Nitrogen Limited", "Phosphorus": "Phosphorus Limited",
                "Temperature": "Temperature Limited", "Light": "Light Limited", "pH": "pH Limited",
                "Max growth rate": "Growth-rate Limited (mu_max)"}
    flags = []
    if a["external_L"] > 1e-6:
        flags.append(("Water Limited", f"{a['external_L']:.1f} L of reactor makeup needed external water; coverage {a['coverage_pct']:.1f}%"))
    if a["spill_L"] > 1e-6 or res["hydraulics"].get("Q_Lph", 0) <= 0:
        flags.append(("Hydraulic Limited", f"{a['spill_L']:.0f} L spilled to drain (orifice capacity {res['hydraulics'].get('Q_Lph',0):.1f} L/h)"))
    act = df[(df["rtf"] > 0) & (df["dT_cond"] > 0)]
    if p["media_on"] and len(act):
        share_w = (act["media_limit"] == "water").mean()
        if share_w >= 0.5:
            flags.append(("Evaporative Cooling Limited", f"water quantity limits the media in {share_w*100:.0f}% of active hours"))
        else:
            flags.append(("High Humidity Limited", f"wet-bulb depression x media effectiveness limits cooling in {(1-share_w)*100:.0f}% of active hours"))
    if a["net_electricity_kWh"] < 0:
        flags.append(("Energy Limited", f"net electricity impact {a['net_electricity_kWh']:.0f} kWh (system uses more than it saves)"))
    if e["cost_limited"]:
        flags.append(("Cost Limited", f"net annual benefit {e['net_annual_benefit_SAR']:.0f} SAR <= 0"))
    return dict(bio_limit=name_map.get(bio_main[0], bio_main[0]), bio_share=bio_main[1], bio_shares=bio_share,
                system_flags=flags, headline=(flags[0][0] if flags else name_map.get(bio_main[0], bio_main[0])))


def validation(res: dict) -> list:
    df, a, p, daily = res["hourly"], res["annual"], res["params"], res["daily"]
    out = []
    # Target 1 - condensate covers 100% of daily need with 20% margin
    need = daily["makeup_demand_L"] * (1 + p["vt1_margin"])
    ok = (daily["condensate_L"] >= need)
    share = ok.mean() if len(ok) else 0
    st = "Pass" if share >= 0.999 else ("Warning" if share >= 0.9 else "Fail")
    out.append(dict(target="T1 Condensate covers 100% of daily reactor need + 20% margin", status=st,
                    value=f"{share*100:.1f}% of days meet it; overall coverage {a['coverage_pct']:.1f}%",
                    basis="Simulated (Validation Target, not a guaranteed result)"))
    # Target 2 - growth in conditioned condensate >= 80% of control
    if p.get("vt2_meas") is not None:
        r = p["vt2_meas"]
        st = "Pass" if r >= p["vt2_ratio"] else ("Warning" if r >= p["vt2_ratio"] - 0.1 else "Fail")
        out.append(dict(target="T2 Growth in conditioned condensate >= 80% of control", status=st, value=f"measured ratio {r:.2f}", basis="Measured Input"))
    else:
        out.append(dict(target="T2 Growth in conditioned condensate >= 80% of control", status="Warning",
                        value="Not evaluable by simulation - requires the paired flask/panel experiment", basis="Experiment required"))
    # Target 3 - reactor temperature within strain range >= 90% of operating time
    inr = ((df["T_r"] >= p["t_range_lo"]) & (df["T_r"] <= p["t_range_hi"])).mean()
    tgt = p["vt3_frac"]
    st = "Pass" if inr >= tgt else ("Warning" if inr >= tgt - 0.15 else "Fail")
    out.append(dict(target=f"T3 Reactor temperature within {p['t_range_lo']:.0f}-{p['t_range_hi']:.0f} C for >= 90% of time", status=st,
                    value=f"{inr*100:.1f}% of hours (max {df['T_r'].max():.1f} C)", basis="Simulated with Low-confidence thermal inputs (alpha, U)"))
    # Target 4 - no persistent density decline / no visible contamination
    skip = 14 if len(daily) >= 30 else 0          # commissioning / start-up transient (design definition)
    xm = daily["X_mean"].values[skip:]
    dec = 0
    run = 0
    for i in range(1, len(xm)):
        run = run + 1 if xm[i] < xm[i - 1] * 0.995 else 0
        dec = max(dec, run)
    st = "Fail" if dec >= 7 else "Pass"
    out.append(dict(target="T4a No persistent decline in algae density (model)", status=st,
                    value=f"longest run of declining days = {dec}" + (f" (after a {skip}-day start-up)" if skip else ""), basis="Simulated"))
    out.append(dict(target="T4b No visible contamination", status="Warning", value="Not evaluable by simulation - requires observation/microscopy",
                    basis="Experiment required"))
    return out
