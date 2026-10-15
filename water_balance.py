"""Clean condensate tank (Sections 4-5).

dV/dt = Q_condensate(after pre-filter) - Q_makeup_reactor - Q_panel_cooling - Q_overflow - Q_spill - Q_other
Priorities each hour: (1) reactor makeup, (2) optional panel cooling, (3) overflow above the lip
through the gravity line (limited by orifice capacity), (4) emergency spill when the tank is full.
Nutrients are NEVER added to this tank; they are dosed only into the reactor loop.
Shortfalls in reactor makeup are met by an external (tap) source and counted separately.
"""
from __future__ import annotations


class Tank:
    def __init__(self, p: dict):
        self.Vmax = p["tank_L"]
        self.V_lip = p["ovf_level"] * p["tank_L"]
        self.V = p["tank_init"] * p["tank_L"]
        self.V0 = self.V
        self.loss_frac = p["prefilter_loss"]
        self.totals = dict(inflow=0.0, prefilter_loss=0.0, makeup=0.0, external=0.0, cooling=0.0,
                           cooling_short=0.0, overflow=0.0, spill=0.0)

    def step(self, inflow_L: float, makeup_L: float, cooling_L: float, ovf_cap_L: float) -> dict:
        loss = inflow_L * self.loss_frac
        self.V += inflow_L - loss
        # 1. reactor makeup
        mk = min(makeup_L, self.V)
        ext = makeup_L - mk
        self.V -= mk
        # 2. optional panel cooling (clean water only)
        cl = min(cooling_L, self.V)
        self.V -= cl
        # 3. overflow above the lip, limited by the gravity line capacity
        ovf = 0.0
        if self.V > self.V_lip:
            ovf = min(self.V - self.V_lip, max(ovf_cap_L, 0.0))
            self.V -= ovf
        # 4. emergency spill (tank full; water wasted)
        spill = 0.0
        if self.V > self.Vmax:
            spill = self.V - self.Vmax
            self.V = self.Vmax
        t = self.totals
        t["inflow"] += inflow_L; t["prefilter_loss"] += loss; t["makeup"] += mk; t["external"] += ext
        t["cooling"] += cl; t["cooling_short"] += cooling_L - cl; t["overflow"] += ovf; t["spill"] += spill
        return dict(level_L=self.V, makeup_L=mk, external_L=ext, cooling_L=cl, overflow_L=ovf, spill_L=spill,
                    prefilter_loss_L=loss, shortage=ext > 1e-9)

    def closure_error(self) -> float:
        """Mass-balance residual (should be ~0)."""
        t = self.totals
        return (self.V0 + t["inflow"] - t["prefilter_loss"] - t["makeup"] - t["cooling"]
                - t["overflow"] - t["spill"] - self.V)
