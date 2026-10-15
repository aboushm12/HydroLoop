"""Psychrometrics (SI) - ASHRAE Fundamentals Ch.1 equations via PsychroLib.

Uses an installed `psychrolib` if available, else the vendored copy
(PsychroLib 2.5.0, MIT licence, vendor/psychrolib.py). Pressures in Pa,
temperatures in C, humidity ratio in kg water / kg dry air.
"""
from __future__ import annotations
import math

try:  # pragma: no cover
    import psychrolib as _pl
except ImportError:  # vendored fallback
    from vendor import psychrolib as _pl

_pl.SetUnitSystem(_pl.SI)

CP_DA = 1.006     # kJ/kg.K dry air (ASHRAE Fundamentals Ch.1)
CP_V = 1.86       # kJ/kg.K water vapour
H_G0 = 2501.0     # kJ/kg


def std_pressure(elev_m: float) -> float:
    return _pl.GetStandardAtmPressure(elev_m)


def w_from_rh(t: float, rh: float, p: float) -> float:
    """rh as fraction 0..1."""
    rh = min(max(rh, 0.0), 1.0)
    return _pl.GetHumRatioFromRelHum(t, rh, p)


def rh_from_w(t: float, w: float, p: float) -> float:
    w = max(w, 1e-7)
    return _pl.GetRelHumFromHumRatio(t, w, p)


def w_sat(t: float, p: float) -> float:
    return _pl.GetSatHumRatio(t, p)


def wet_bulb(t: float, w: float, p: float) -> float:
    w = max(w, 1e-7)
    return _pl.GetTWetBulbFromHumRatio(t, w, p)


def dew_point(t: float, w: float, p: float) -> float:
    return _pl.GetTDewPointFromHumRatio(t, max(w, 1e-7), p)


def enthalpy(t: float, w: float) -> float:
    """kJ/kg dry air."""
    return CP_DA * t + w * (H_G0 + CP_V * t)


def specific_volume(t: float, w: float, p: float) -> float:
    """m3 per kg dry air."""
    return _pl.GetMoistAirVolume(t, w, p)


def moist_density(t: float, w: float, p: float) -> float:
    return _pl.GetMoistAirDensity(t, w, p)


def cp_moist(w: float) -> float:
    """kJ/(kg dry air . K)."""
    return CP_DA + CP_V * w


def latent_heat(t: float) -> float:
    """Latent heat of vaporisation, kJ/kg, lambda = 2501 - 2.361 T (FAO-56 Annex 3, Harrison 1963)."""
    return 2501.0 - 2.361 * t


def coil_condensate_kg_s(m_da: float, w_in: float, w_out: float) -> float:
    """Condensate = dry-air mass flow x humidity-ratio drop (no negative condensation)."""
    return m_da * max(w_in - w_out, 0.0)


def mix(w1: float, t1: float, w2: float, t2: float, frac2: float):
    """Adiabatic mixing on dry-air mass basis (frac2 = share of stream 2)."""
    w = (1 - frac2) * w1 + frac2 * w2
    h = (1 - frac2) * enthalpy(t1, w1) + frac2 * enthalpy(t2, w2)
    t = (h - w * H_G0) / (CP_DA + w * CP_V)
    return t, w
