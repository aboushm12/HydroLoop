"""Energy budget of the whole system (Section 20). Overflow pump = 0 W by design (gravity)."""
from __future__ import annotations

G = 9.80665
OVERFLOW_PUMP_W = 0.0   # gravity line - asserted in tests


def circulation_pump_w(p: dict) -> float:
    q = p["circ_lpm"] / 60000.0                                   # m3/s
    hyd = p["rho_w"] * G * q * p["circ_head"]
    return max(hyd / max(p["pump_eff"], 1e-6), p["pump_min_w"]) if p["circ_lpm"] > 0 else 0.0


def air_pump_w(p: dict, V_L: float) -> float:
    return p["vvm"] * V_L * p["air_w_per_lpm"]


def hourly_loads_w(p: dict, V_L: float, A_m2: float, hour: int) -> dict:
    circ_on = hour < p["circ_hours"] if p["circ_hours"] < 24 else True
    led = 0.0
    if p["light_on"]:
        # LEDs run during the first `led_hours` hours after 18:00 (night supplement)
        if 18 <= hour < 18 + p["led_hours"] or hour < max(0, 18 + p["led_hours"] - 24):
            led = p["led_ppfd"] * A_m2 / max(p["led_eff"], 1e-6)
    return dict(circ=circulation_pump_w(p) if circ_on else 0.0, air=air_pump_w(p, V_L),
                sensors=p["sensor_w"], ctrl=p["ctrl_w"], led=led, overflow_pump=OVERFLOW_PUMP_W)


def pv_w(p: dict, ghi: float) -> float:
    return p["pv_kwp"] * 1000.0 * ghi / 1000.0 * p["pv_pr"] if p["pv_on"] else 0.0
