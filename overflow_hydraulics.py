"""Gravity overflow line: tank overflow -> air break -> cleanable filter -> gravity
pipe -> flow restrictor (orifice) -> evaporative media -> drain pan.

No pump: the only driving energy is the hydraulic head (Section 16).
    static pressure        p = rho g h            (1 m of water = 9.78 kPa ~ 0.0978 bar at 997 kg/m3;
                                                    0.0981 bar is the value for rho = 1000 kg/m3)
    Torricelli velocity    v_t = sqrt(2 g h)
    orifice flow           Q = Cd A_o sqrt(2 g h_net)
    h_net = h - h_f - h_minor   (Darcy-Weisbach, Swamee-Jain / laminar 64/Re)
Reducing the outlet diameter does NOT add energy: it only lowers Q.
"""
from __future__ import annotations
import math

G = 9.80665


def friction_factor(re: float, rel_rough: float) -> float:
    if re <= 0:
        return 0.0
    if re < 2300:
        return 64.0 / re
    return 0.25 / (math.log10(rel_rough / 3.7 + 5.74 / re ** 0.9)) ** 2


def solve(p: dict) -> dict:
    """Steady gravity capacity of the overflow line (full-pipe/orifice-controlled)."""
    h = max(p["ovf_head"], 0.0)
    rho, mu = p["rho_w"], p["mu_w"]
    D, L = p["pipe_D"], p["pipe_L"]
    d = p["orifice_d"]
    A_p = math.pi * D ** 2 / 4
    A_o = math.pi * d ** 2 / 4
    K = p["k_entr"] + p["n_elbows"] * p["k_elbow"]
    res = dict(head_m=h, static_kpa=rho * G * h / 1000, static_bar=rho * G * h / 1e5,
               v_torricelli=math.sqrt(2 * G * h), Q_m3s=0.0, h_loss_m=0.0, h_net_m=0.0,
               v_pipe=0.0, v_orifice=0.0, Re=0.0, f=0.0, flags=[])
    if h <= 0 or d <= 0:
        res["flags"].append("No head or no orifice: overflow line cannot flow (Hydraulic Limited)")
        return res
    Q = p["cd"] * A_o * math.sqrt(2 * G * h)
    for _ in range(100):
        v = Q / A_p
        re = rho * v * D / mu
        f = friction_factor(re, p["pipe_rough"] / D)
        hl = (f * L / D + K) * v ** 2 / (2 * G)
        hn = max(h - hl, 0.0)
        Qn = p["cd"] * A_o * math.sqrt(2 * G * hn)
        if abs(Qn - Q) < 1e-12:
            break
        Q = 0.5 * (Q + Qn)
    res.update(Q_m3s=Q, Q_Lph=Q * 3.6e6, h_loss_m=hl, h_net_m=hn, v_pipe=v, Re=re, f=f,
               v_orifice=Q / A_o, net_kpa=rho * G * hn / 1000)
    if d < p["orifice_dmin"]:
        res["flags"].append(f"Orifice {d*1000:.1f} mm < {p['orifice_dmin']*1000:.1f} mm: clogging risk")
    return res


def assess(res: dict, overflow_series_Lph) -> list:
    """Compare capacity with simulated overflow demand."""
    flags = list(res["flags"])
    cap = res.get("Q_Lph", 0.0)
    pos = [x for x in overflow_series_Lph if x > 0]
    if not pos:
        return flags
    peak, mean = max(pos), sum(pos) / len(pos)
    if cap < peak:
        flags.append(f"Orifice capacity {cap:.1f} L/h < peak overflow {peak:.1f} L/h: tank level rises above the lip; excess goes to the emergency overflow (wasted)")
    if cap > 20 * mean:
        flags.append(f"Orifice capacity {cap:.0f} L/h is >20x the mean overflow ({mean:.2f} L/h): expect intermittent trickle and poor wetting/distribution on the media")
    return flags
