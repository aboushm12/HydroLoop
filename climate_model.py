"""Jeddah climate model -> hourly weather for one non-leap year (8760 h).

Sources (see sources.json):
* Default: NOAA 1991-2020 monthly normals for Jeddah (Tmax, Tmin, RH, sunshine).
  Hourly temperature from ASHRAE Fundamentals 'fraction of daily range';
  humidity ratio held constant through each day (ASHRAE design-day practice).
  Solar: FAO-56 Angstrom-Prescott from sunshine hours, Erbs monthly diffuse
  fraction, Collares-Pereira & Rabl / Liu & Jordan hourly split, isotropic sky
  on the vertical facade (Duffie & Beckman).
* Optional: NASA POWER hourly data (fetched on the user's machine) or a user CSV.
Time axis = local solar time (Jeddah solar noon is ~12:23 AST; not corrected).
"""
from __future__ import annotations
import json, math, os, urllib.request
import numpy as np
import pandas as pd
import psychrometrics as ps

DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
KLEIN_DAY = [17, 47, 75, 105, 135, 162, 198, 228, 258, 288, 318, 344]
# ASHRAE Fundamentals Ch.14: fraction of daily temperature range, hours 1..24
ASHRAE_DR_FRACTION = [0.88, 0.92, 0.95, 0.98, 1.00, 0.98, 0.91, 0.74, 0.55, 0.38, 0.23, 0.13,
                      0.05, 0.00, 0.00, 0.06, 0.14, 0.24, 0.39, 0.50, 0.59, 0.68, 0.75, 0.82]
GSC = 1367.0  # W/m2, solar constant used by Duffie & Beckman
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ----------------------------------------------------------------- solar geometry
def declination(doy):
    return math.radians(23.45 * math.sin(math.radians(360.0 * (284 + doy) / 365.0)))


def sunset_hour_angle(phi, delta):
    x = -math.tan(phi) * math.tan(delta)
    return math.acos(min(1.0, max(-1.0, x)))


def h0_daily(phi, doy):
    """Extraterrestrial daily irradiation on horizontal, J/m2."""
    d = declination(doy)
    ws = sunset_hour_angle(phi, d)
    return (24 * 3600 * GSC / math.pi) * (1 + 0.033 * math.cos(math.radians(360 * doy / 365))) * (
        math.cos(phi) * math.cos(d) * math.sin(ws) + ws * math.sin(phi) * math.sin(d))


def erbs_monthly_diffuse(kt, ws_deg):
    if ws_deg <= 81.4:
        return 1.391 - 3.560 * kt + 4.189 * kt ** 2 - 2.137 * kt ** 3
    return 1.311 - 3.022 * kt + 3.427 * kt ** 2 - 1.821 * kt ** 3


def facade_irradiance(ghi, dhi, phi, doy, hour_mid, az_deg, albedo, beta_deg=90.0):
    """Isotropic-sky irradiance on a tilted surface (W/m2). hour_mid in solar time."""
    d = declination(doy)
    w = math.radians(15.0 * (hour_mid - 12.0))
    beta, gam = math.radians(beta_deg), math.radians(az_deg)
    cz = math.cos(phi) * math.cos(d) * math.cos(w) + math.sin(phi) * math.sin(d)
    ct = (math.sin(d) * math.sin(phi) * math.cos(beta) - math.sin(d) * math.cos(phi) * math.sin(beta) * math.cos(gam)
          + math.cos(d) * math.cos(phi) * math.cos(beta) * math.cos(w)
          + math.cos(d) * math.sin(phi) * math.sin(beta) * math.cos(gam) * math.cos(w)
          + math.cos(d) * math.sin(beta) * math.sin(gam) * math.sin(w))
    ib = max(ghi - dhi, 0.0)
    beam_t = 0.0
    if cz > 0.0175 and ct > 0:
        dni = min(ib / cz, 1000.0)
        beam_t = dni * ct
    return beam_t + dhi * (1 + math.cos(beta)) / 2 + ghi * albedo * (1 - math.cos(beta)) / 2, max(cz, 0.0)


# ----------------------------------------------------------------- NOAA-normals year
def build_noaa_year(p: dict) -> pd.DataFrame:
    phi = math.radians(p["lat"])
    P = ps.std_pressure(p["elev_m"])
    rows = []
    prof = {}
    for m in range(12):
        tmax = p["noaa_tmax"][m] + p["t_offset"]
        tmin = p["noaa_tmin"][m] + p["t_offset"]
        rh = min(max(p["noaa_rh"][m] + p["rh_offset"], 1.0), 100.0) / 100.0
        tmean = 0.5 * (tmax + tmin)
        w_day = ps.w_from_rh(tmean, rh, P)
        n = KLEIN_DAY[m]
        d = declination(n)
        ws = sunset_hour_angle(phi, d)
        H0 = h0_daily(phi, n)
        N = 2 * math.degrees(ws) / 15.0
        nsun = p["noaa_sun"][m] / DAYS_IN_MONTH[m]
        H = H0 * (p["ang_a"] + p["ang_b"] * min(nsun / N, 1.0))
        kt = H / H0
        Hd = H * erbs_monthly_diffuse(kt, math.degrees(ws))
        a = 0.409 + 0.5016 * math.sin(ws - math.radians(60))
        b = 0.6609 - 0.4767 * math.sin(ws - math.radians(60))
        den = math.sin(ws) - ws * math.cos(ws)
        hours = []
        for h in range(24):
            hm = h + 0.5
            w = math.radians(15.0 * (hm - 12.0))
            if math.cos(w) > math.cos(ws):
                rt = (math.pi / 24) * (a + b * math.cos(w)) * (math.cos(w) - math.cos(ws)) / den
                rd = (math.pi / 24) * (math.cos(w) - math.cos(ws)) / den
            else:
                rt = rd = 0.0
            ghi = rt * H / 3600.0
            dhi = min(rd * Hd / 3600.0, ghi)
            gt, cz = facade_irradiance(ghi, dhi, phi, n, hm, p["facade_az"], p["albedo"])
            T = tmax - ASHRAE_DR_FRACTION[h] * (tmax - tmin)
            W = min(w_day, ps.w_sat(T, P) * 0.999)
            hours.append(dict(T=T, W=W, RH=ps.rh_from_w(T, W, P), P=P, Twb=ps.wet_bulb(T, W, P),
                              GHI=ghi, DHI=dhi, GT=gt))
        prof[m] = dict(H_MJ=H / 1e6, KT=kt, Hd_frac=Hd / H, day_len=N, W=w_day)
        for day in range(DAYS_IN_MONTH[m]):
            for h in range(24):
                r = dict(hours[h]); r.update(month=m + 1, day=day + 1, hour=h)
                rows.append(r)
    df = pd.DataFrame(rows)
    df.attrs["source"] = "NOAA 1991-2020 normals + ASHRAE/FAO-56/Duffie-Beckman derivation"
    df.attrs["monthly_solar"] = prof
    return _finish(df, p)


def _finish(df, p):
    df["doy"] = np.repeat(np.arange(1, len(df) // 24 + 1), 24)[: len(df)]
    df["PPFD_T"] = df["GT"] * p["f_par"] * p["umol_per_J"]          # incident on facade, umol/m2/s
    df["PPFD_H"] = df["GHI"] * p["f_par"] * p["umol_per_J"]
    df["dT_psy"] = df["T"] - df["Twb"]
    return df


# ----------------------------------------------------------------- NASA POWER (user machine)
def nasa_power_url(lat, lon, year):
    params = "T2M,RH2M,QV2M,PS,ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF"
    return ("https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=" + params +
            f"&community=RE&longitude={lon}&latitude={lat}&start={year}0101&end={year}1231"
            "&format=JSON&time-standard=LST")


def fetch_nasa_power(p: dict, year: int = 2023, timeout=60) -> pd.DataFrame:
    """Download (or read cached) NASA POWER hourly data and convert to the model format."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, f"nasa_power_{p['lat']}_{p['lon']}_{year}.json")
    if os.path.exists(cache):
        with open(cache) as f:
            js = json.load(f)
    else:
        with urllib.request.urlopen(nasa_power_url(p["lat"], p["lon"], year), timeout=timeout) as r:
            js = json.loads(r.read().decode())
        with open(cache, "w") as f:
            json.dump(js, f)
    par = js["properties"]["parameter"]
    keys = sorted(par["T2M"].keys())
    rows = []
    phi = math.radians(p["lat"])
    for k in keys:
        mo, dd, hh = int(k[4:6]), int(k[6:8]), int(k[8:10])
        if mo == 2 and dd == 29:
            continue
        T = par["T2M"][k] + p["t_offset"]
        q = par["QV2M"][k] / 1000.0
        W = q / (1 - q)
        P = par["PS"][k] * 1000.0
        if p["rh_offset"]:
            rh = min(max(ps.rh_from_w(T, W, P) + p["rh_offset"] / 100, 0.01), 1.0)
            W = ps.w_from_rh(T, rh, P)
        W = min(W, ps.w_sat(T, P) * 0.999)
        ghi = max(par["ALLSKY_SFC_SW_DWN"][k], 0.0)
        dhi = min(max(par["ALLSKY_SFC_SW_DIFF"][k], 0.0), ghi)
        rows.append(dict(month=mo, day=dd, hour=hh, T=T, W=W, P=P, GHI=ghi, DHI=dhi))
    df = pd.DataFrame(rows).iloc[:8760].reset_index(drop=True)
    doy = np.repeat(np.arange(1, 366), 24)[: len(df)]
    df["RH"] = [ps.rh_from_w(t, w, pp) for t, w, pp in zip(df["T"], df["W"], df["P"])]
    df["Twb"] = [ps.wet_bulb(t, w, pp) for t, w, pp in zip(df["T"], df["W"], df["P"])]
    df["GT"] = [facade_irradiance(g, d, phi, n, h + 0.5, p["facade_az"], p["albedo"])[0]
                for g, d, n, h in zip(df["GHI"], df["DHI"], doy, df["hour"])]
    df.attrs["source"] = f"NASA POWER hourly {year} (LST) at {p['lat']},{p['lon']}"
    return _finish(df, p)


def from_csv(path_or_buf, p: dict) -> pd.DataFrame:
    """User weather CSV: month, day, hour, T (C), RH (%), GHI (W/m2) [, DHI, P (Pa)]."""
    u = pd.read_csv(path_or_buf)
    P0 = ps.std_pressure(p["elev_m"])
    phi = math.radians(p["lat"])
    if "P" not in u:
        u["P"] = P0
    if "DHI" not in u:
        u["DHI"] = 0.3 * u["GHI"]   # placeholder split flagged in attrs
    u = u.iloc[:8760].reset_index(drop=True)
    u["T"] = u["T"] + p["t_offset"]
    u["RH"] = (u["RH"] + p["rh_offset"]).clip(1, 100) / 100
    u["W"] = [min(ps.w_from_rh(t, r, pp), ps.w_sat(t, pp) * 0.999) for t, r, pp in zip(u["T"], u["RH"], u["P"])]
    u["Twb"] = [ps.wet_bulb(t, w, pp) for t, w, pp in zip(u["T"], u["W"], u["P"])]
    doy = np.repeat(np.arange(1, 366), 24)[: len(u)]
    u["GT"] = [facade_irradiance(g, d, phi, n, h + 0.5, p["facade_az"], p["albedo"])[0]
               for g, d, n, h in zip(u["GHI"], u["DHI"], doy, u["hour"])]
    u.attrs["source"] = "User CSV" + ("" if "DHI" in u else " (DHI assumed 30% of GHI)")
    return _finish(u, p)


def monthly_summary(wx: pd.DataFrame) -> pd.DataFrame:
    g = wx.groupby("month")
    return pd.DataFrame({
        "T_mean": g["T"].mean(), "T_max": g["T"].max(), "RH_mean_%": g["RH"].mean() * 100,
        "W_g_kg": g["W"].mean() * 1000, "Twb_mean": g["Twb"].mean(), "Wet-bulb depression_mean": g["dT_psy"].mean(),
        "GHI_kWh_m2_day": g["GHI"].sum() / 1000 / g["day"].nunique(),
        "Facade_kWh_m2_day": g["GT"].sum() / 1000 / g["day"].nunique(),
    })
