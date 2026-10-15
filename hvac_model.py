"""AC unit model: coil condensate, runtime, condenser pre-cooling and power.

Condensate (Psychrometric Mode):
    m_cond = m_da * (W_in - W_out) * RTF         [ASHRAE Fundamentals mass balance]
    W_in  = mix(return air, outdoor air, OA fraction)
    W_out = W(T_coil, RH_coil)
Measured Mode: m_cond = measured L/h during scheduled hours.

Evaporative media in front of the condenser (Section 17):
    dT_media = eff * (T_db - T_wb)                         (psychrometric media limit)
    dT_water = m_w_avail * h_fg / (m_air * cp_moist)        (water-quantity limit)
    dT = min(dT_media, dT_water);  T_in,after = T_db - dT  (never below T_wb)
    m_evap = m_air * cp_moist * dT / h_fg  <= m_w_avail

HVAC power (Section 18):
    P_before = Q_cap / COP(T) * RTF, COP(T) from a Carnot-fraction model calibrated
               to the rated COP at 35 C (physical temperature dependence).
    empirical saving  = P_before * slope * dT          (Ibrahim et al. 2017, linearised
                                                        -> 'Sensitivity Approximation')
    carnot saving     = P_before * (1 - COP(T)/COP(T - dT))  (cross-check)
    fan penalty       = V_cond * dp_media / eta_fan     (whenever media installed)
"""
from __future__ import annotations
import math
import psychrometrics as ps

CFM_TO_M3S = 0.00047194745


class ACUnit:
    def __init__(self, p: dict, P_atm: float):
        self.p = p
        self.P = P_atm
        self.cap_kw = p["ac_tr"] * p["kw_per_tr"]
        self.v_evap = p["evap_cfm_tr"] * p["ac_tr"] * CFM_TO_M3S        # m3/s
        self.v_cond = p["cond_cfm_tr"] * p["ac_tr"] * CFM_TO_M3S        # m3/s
        self.w_ret = ps.w_from_rh(p["t_in"], p["rh_in"] / 100, P_atm)
        self.w_coil = ps.w_from_rh(p["t_coil"], p["rh_coil"] / 100, P_atm)
        self.h_coil = ps.enthalpy(p["t_coil"], self.w_coil)
        te = p["t_evap"] + 273.15
        tc_rated = 35.0 + p["cond_approach"] + 273.15
        self.eta2 = p["cop_rated"] / (te / (tc_rated - te))           # second-law fraction
        self.te = te

    # ------------------------------------------------------------- schedule / load
    def on_schedule(self, hour: int) -> bool:
        on, off = self.p["sched_on"], self.p["sched_off"]
        return (on <= hour < off) if on <= off else (hour >= on or hour < off)

    def rtf(self, T: float, hour: int) -> float:
        if not self.on_schedule(hour):
            return 0.0
        p = self.p
        x = (T - p["t_bal"]) / max(p["t_des"] - p["t_bal"], 1e-6)
        return min(1.0, max(p["rtf_min"], p["rtf_min"] + (1 - p["rtf_min"]) * x))

    # ------------------------------------------------------------- condensate
    def condensate_lph(self, T_out: float, W_out: float, hour: int):
        """Returns (L/h, info dict)."""
        p = self.p
        r = self.rtf(T_out, hour)
        if p["cond_mode"] == "measured" and p.get("cond_meas_lph") is not None:
            lph = p["cond_meas_lph"] if self.on_schedule(hour) else 0.0
            return lph, dict(rtf=r, w_in=float("nan"), q_coil_kw=float("nan"), cap_limited=False, mode="measured")
        t_mix, w_mix = ps.mix(self.w_ret, p["t_in"], W_out, T_out, p["oa_frac"])
        v_spec = ps.specific_volume(t_mix, w_mix, self.P)
        m_da = self.v_evap / v_spec                                    # kg dry air / s
        q_coil = m_da * (ps.enthalpy(t_mix, w_mix) - self.h_coil)      # kW (total coil load at full flow)
        scale = 1.0
        cap_limited = False
        if q_coil > self.cap_kw and q_coil > 0:                        # coil cannot reach the set leaving state
            scale = self.cap_kw / q_coil
            cap_limited = True
        kg_s = ps.coil_condensate_kg_s(m_da, w_mix, self.w_coil) * scale
        lph = kg_s * 3600.0 * r                                        # 1 kg ~ 1 L
        return lph, dict(rtf=r, w_in=w_mix, t_mix=t_mix, m_da=m_da, q_coil_kw=q_coil * scale, cap_limited=cap_limited, mode="psychrometric")

    # ------------------------------------------------------------- COP / power
    def cop(self, t_air_in: float) -> float:
        tc = t_air_in + self.p["cond_approach"] + 273.15
        return self.eta2 * self.te / max(tc - self.te, 1.0)

    def power_kw(self, t_air_in: float, rtf: float) -> float:
        return self.cap_kw / self.cop(t_air_in) * rtf

    # ------------------------------------------------------------- media pre-cooling
    def precool(self, T: float, W: float, Twb: float, rtf: float, water_L: float):
        """Evaporative media in front of the condenser for one hour.
        water_L = overflow water delivered to the media in this hour."""
        p = self.p
        out = dict(dT=0.0, dT_media=0.0, dT_water=0.0, evap_L=0.0, drain_L=water_L, limit="none",
                   t_in_after=T, fan_penalty_kw=0.0)
        if not p["media_on"]:
            out["drain_L"] = water_L
            return out
        dp = p["media_dp_pa"] * (p["media_face_v"] / p["media_v_ref"]) ** 2     # quadratic scaling (assumption)
        out["fan_penalty_kw"] = self.v_cond * dp / max(p["fan_eff"], 1e-6) / 1000.0 * rtf
        out["media_area_m2"] = self.v_cond / max(p["media_face_v"], 1e-6)
        if rtf <= 0:
            out["limit"] = "AC off"
            return out
        rho = ps.moist_density(T, W, self.P)
        m_air_kg_h = self.v_cond * rho / (1 + W) * 3600.0 * rtf        # dry-air kg per hour through media
        cpm = ps.cp_moist(W)
        hfg = ps.latent_heat(Twb)
        dT_media = max(p["media_eff"] * (T - Twb), 0.0)
        dT_water = water_L * hfg / (m_air_kg_h * cpm) if m_air_kg_h > 0 else 0.0
        dT = min(dT_media, dT_water, max(T - Twb, 0.0))
        evap = m_air_kg_h * cpm * dT / hfg
        evap = min(evap, water_L)
        out.update(dT=dT, dT_media=dT_media, dT_water=dT_water, evap_L=evap, drain_L=water_L - evap,
                   t_in_after=T - dT, limit=("water" if dT_water < dT_media else "media/humidity"))
        return out

    def savings_kw(self, T: float, dT: float, rtf: float):
        p_before = self.power_kw(T, rtf)
        emp = p_before * self.p["slope_pct_per_K"] / 100.0 * dT
        car = p_before - self.power_kw(T - dT, rtf)
        return p_before, emp, car
