"""Parameter registry: defaults come ONLY from sources.json (the Source Ledger)."""
from __future__ import annotations
import json, os, copy

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES_PATH = os.path.join(HERE, "sources.json")

with open(SOURCES_PATH, encoding="utf-8") as _f:
    SOURCES = json.load(_f)

LEDGER = {e["key"]: e for e in SOURCES["ledger"]}
CITATIONS = SOURCES["citations"]

CONF_RANK = {"High": 5, "High-Medium": 4, "Medium": 3, "Low-Medium": 2, "Low": 1}
RANK_CONF = {v: k for k, v in CONF_RANK.items()}

# Confidence implied by evidence type (Section 29 of the brief)
TYPE_CONF = {
    "Measured Input": "High",
    "Local Saudi Data": "High-Medium",
    "Published Experimental Data": "Medium",
    "Manufacturer Data": "Medium",
    "Literature Assumption": "Low-Medium",
    "Design Input": "Low",
}


def defaults() -> dict:
    """Flat dict key -> default value (deep copy)."""
    return {k: copy.deepcopy(e["value"]) for k, e in LEDGER.items()}


# Scenario presets: they change PHYSICAL conditions and equipment, never a hand-set saving %.
SCENARIOS = {
    "Conservative": {
        "media_eff": LEDGER["media_eff_cons"]["value"],   # 3-inch pad (EVAPCO)
        "oa_frac": 0.05,                                   # less outdoor air -> less condensate
        "rh_in": 50.0,
        "hl_use": 0.0,                                     # no credit for photons above 930 umol
        "temp_profile": "UTEX1230",
    },
    "Reference": {},
    "Optimistic": {
        "media_eff": LEDGER["media_eff_opt"]["value"],    # 6-inch pad (EVAPCO best)
        "oa_frac": 0.20,
        "rh_in": 60.0,
        "hl_use": 1.0,
    },
}

SCENARIO_NOTES = {
    "Conservative": "3-inch media (eff 0.43), OA 5%, indoor RH 50%, no growth credit above 930 umol/m2/s, UTEX 1230 temperature data",
    "Reference": "100 mm cellulose media (eff 0.55), OA 10%, indoor RH 55%, half credit above 930 umol/m2/s, UTEX 1230 temperature data",
    "Optimistic": "6-inch media (eff 0.74), OA 20%, indoor RH 60%, full credit above 930 umol/m2/s, UTEX 1230 temperature data (strain profile is a separate user choice)",
}


def scenario_params(name: str, base: dict | None = None) -> dict:
    p = defaults() if base is None else copy.deepcopy(base)
    p.update(copy.deepcopy(SCENARIOS[name]))
    return p


def param_confidence(key: str, params: dict | None = None) -> str:
    """Confidence of one input; a user-entered measured value upgrades to High."""
    e = LEDGER.get(key)
    if e is None:
        return "Low"
    if params is not None and e["data_type"] == "Measured Input" and params.get(key) is not None:
        return "High"
    if params is not None and params.get(key) != e["value"] and e["data_type"] != "Measured Input":
        return "Low"  # user override without a documented source -> treated as a Design Input
    return e["confidence"]


def combine(keys, params=None, extra=None) -> str:
    """Weakest-link confidence for a calculated output."""
    ranks = [CONF_RANK[param_confidence(k, params)] for k in keys]
    if extra:
        ranks += [CONF_RANK[c] for c in extra]
    return RANK_CONF[min(ranks)] if ranks else "Low"
