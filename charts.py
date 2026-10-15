"""Plotly figures. Palette: validated categorical order (blue, orange, aqua, yellow, magenta);
status colours reserved for health/validation. One y-axis per chart (no dual axes)."""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import algae_model as am

C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
STATUS = {"Healthy": "#0ca30c", "Pass": "#0ca30c", "Warning": "#fab219", "Critical": "#d03b3b", "Fail": "#d03b3b"}
GRID = "#e6e5e1"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _style(fig, title, h=380):
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)), template="plotly_white", height=h,
                      margin=dict(l=55, r=20, t=55, b=45), font=dict(family="Inter, Arial", size=12, color="#0b0b0b"),
                      legend=dict(orientation="h", y=-0.2), hovermode="x unified")
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def _t(df):
    return np.arange(len(df)) / 24.0  # days since period start


# --------------------------------------------------------------------- Sankeys
def water_sankey(res):
    a = res["annual"]
    labels = ["Condensate", "Tap water", "Filter loss", "Clean tank", "Reactor",
              "Panel cooling", "Overflow", "Spill (wasted)", "Evaporated", "Drain",
              "Storage change"]
    src, tgt, val = [], [], []
    def L(s, t, v):
        if v > 1e-6:
            src.append(s); tgt.append(t); val.append(v)
    L(0, 2, a["prefilter_loss_L"]); L(0, 3, a["condensate_L"] - a["prefilter_loss_L"])
    L(3, 4, a["condensate_to_reactor_L"]); L(1, 4, a["external_L"]); L(3, 5, a["cooling_L"])
    L(3, 6, a["overflow_L"]); L(3, 7, a["spill_L"]); L(6, 8, a["media_evap_L"]); L(6, 9, a["media_drain_L"])
    L(3, 10, max(a["tank_change_L"], 0))
    col = [C[0], C[3], "#b9b8b2", C[0], C[2], C[2], C[1], C[7], C[1], "#b9b8b2", "#b9b8b2"]
    fig = go.Figure(go.Sankey(node=dict(label=labels, color=col, pad=18, thickness=16),
                              link=dict(source=src, target=tgt, value=val, color="rgba(42,120,214,0.25)",
                                        hovertemplate="%{source.label} -> %{target.label}: %{value:,.0f} L<extra></extra>")))
    return _style(fig, f"Water balance over the period (L) - closure error {res['tank'].closure_error():.1e} L", 420)


def carbon_sankey(res):
    a = res["annual"]
    gross = a["co2_gross_uptake_g"]
    net = a["co2_carbon_method_g"]
    labels = ["CO2 supplied", "Vented", "Transferable", "Unused",
              "Gross uptake", "Respired", "Fixed in biomass"]
    v = [max(a["co2_supplied_g"] - a["co2_transferable_g"], 0), a["co2_transferable_g"],
         max(a["co2_transferable_g"] - gross, 0), gross, max(gross - net, 0), net]
    fig = go.Figure(go.Sankey(node=dict(label=labels, color=[C[0], "#b9b8b2", C[0], "#b9b8b2", C[2], C[1], C[5]], pad=18, thickness=16),
                              link=dict(source=[0, 0, 2, 2, 4, 4], target=[1, 2, 3, 4, 5, 6], value=v,
                                        color="rgba(27,175,122,0.25)",
                                        hovertemplate="%{source.label} -> %{target.label}: %{value:,.1f} g CO2<extra></extra>")))
    return _style(fig, "Carbon path (g CO2) - Gross Biological CO2 Fixation, not an offset", 380)


def energy_bars(res):
    a = res["annual"]
    items = [("HVAC saving (gross)", a["hvac_gross_saving_kWh"]), ("Media fan penalty", -a["fan_penalty_kWh"]),
             ("PBR pumps + air", -a["pbr_only_kWh"]), ("Sensors + controller", -a["control_kWh"])]
    if res["params"]["pv_on"]:
        items.append(("PV production", a["pv_kWh"]))
    items.append(("NET electricity impact", a["net_electricity_kWh"]))
    fig = go.Figure(go.Waterfall(x=[i[0] for i in items], y=[i[1] for i in items],
                                 measure=["relative"] * (len(items) - 1) + ["total"],
                                 increasing=dict(marker=dict(color=C[2])), decreasing=dict(marker=dict(color=C[1])),
                                 totals=dict(marker=dict(color=C[0] if a["net_electricity_kWh"] >= 0 else STATUS["Critical"])),
                                 text=[f"{i[1]:,.0f}" for i in items], textposition="outside",
                                 hovertemplate="%{x}: %{y:,.1f} kWh<extra></extra>"))
    return _style(fig, "Energy loop (kWh over the period) - negative net is shown, not hidden", 380)


# --------------------------------------------------------------------- architecture
def architecture():
    fig = go.Figure()
    boxes = {
        "AC indoor coil": (0.04, 0.82), "Pre-filter": (0.25, 0.82), "Clean condensate tank": (0.46, 0.82),
        "Reactor loop (nutrients only here)": (0.70, 0.82), "Harvest": (0.92, 0.82),
        "Overflow lip -> Air break": (0.46, 0.60), "Cleanable filter": (0.46, 0.40), "Gravity line + orifice": (0.46, 0.20),
        "Evaporative media": (0.70, 0.20), "AC condenser": (0.92, 0.20), "Drain pan": (0.70, 0.0),
        "Air / CO2 supply": (0.70, 0.55), "O2 + CO2 vent": (0.92, 0.62), "Electricity (pumps, sensors)": (0.92, 0.42),
    }
    for k, (x, y) in boxes.items():
        fig.add_shape(type="rect", x0=x - 0.085, x1=x + 0.085, y0=y - 0.055, y1=y + 0.055, line=dict(color="#52514e", width=1),
                      fillcolor="#fcfcfb")
        fig.add_annotation(x=x, y=y, text=k, showarrow=False, font=dict(size=10))
    arrows = [("AC indoor coil", "Pre-filter", C[0]), ("Pre-filter", "Clean condensate tank", C[0]),
              ("Clean condensate tank", "Reactor loop (nutrients only here)", C[0]), ("Reactor loop (nutrients only here)", "Harvest", C[2]),
              ("Clean condensate tank", "Overflow lip -> Air break", C[0]), ("Overflow lip -> Air break", "Cleanable filter", C[0]),
              ("Cleanable filter", "Gravity line + orifice", C[0]), ("Gravity line + orifice", "Evaporative media", C[0]),
              ("Evaporative media", "AC condenser", C[1]), ("Evaporative media", "Drain pan", C[0]),
              ("Air / CO2 supply", "Reactor loop (nutrients only here)", C[2]), ("Reactor loop (nutrients only here)", "O2 + CO2 vent", C[4]),
              ("Electricity (pumps, sensors)", "Reactor loop (nutrients only here)", C[3])]
    def edge(cx, cy, tx, ty, hw=0.085, hh=0.055):
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        s = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
        return cx + dx * s, cy + dy * s
    for a, b, col in arrows:
        (x0, y0), (x1, y1) = boxes[a], boxes[b]
        sx, sy = edge(x0, y0, x1, y1)
        ex, ey = edge(x1, y1, x0, y0)
        fig.add_annotation(x=ex, y=ey, ax=sx, ay=sy, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                           arrowhead=3, arrowsize=1.1, arrowwidth=2, arrowcolor=col, text="")
    for i, (lab, col) in enumerate([("Water", C[0]), ("Carbon / biomass", C[2]), ("Oxygen", C[4]), ("Energy", C[3]), ("Cooling", C[1])]):
        fig.add_annotation(x=0.02 + i * 0.19, y=1.0, text=f"<b style='color:{col}'>&#9632;</b> {lab}", showarrow=False, xanchor="left")
    fig.update_xaxes(visible=False, range=[-0.05, 1.03])
    fig.update_yaxes(visible=False, range=[-0.08, 1.05])
    return _style(fig, "System architecture: water, carbon, oxygen, energy and cooling paths", 400)


# --------------------------------------------------------------------- time series
def growth_curve(res):
    df = res["hourly"]
    t = _t(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df["X"], name="Biomass concentration (g/L)", line=dict(color=C[2], width=2)))
    return _style(fig, "Algae growth curve - biomass concentration", 330).update_xaxes(title="days from start").update_yaxes(title="g/L")


def cumulative(res):
    df, p = res["hourly"], res["params"]
    t = _t(df)
    comp = res["comp"]
    V = res["geo"]["V_L"]
    prod = (df["harvest_g"] + df["sample_g"]).cumsum() + (df["X"] - p["x0"]) * V
    prod = prod.clip(lower=0)
    co2 = prod * comp["co2_g_per_g_cf"]
    o2 = prod * comp["o2_g_per_g"]
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Net biomass produced (g)", "CO2 fixed (g, carbon method)", "O2 produced (g, stoichiometric)"))
    for i, (y, col) in enumerate([(prod, C[2]), (co2, C[0]), (o2, C[4])]):
        fig.add_trace(go.Scatter(x=t, y=y, line=dict(color=col, width=2), showlegend=False), 1, i + 1)
    return _style(fig, "Cumulative production over time (derived from biomass - not entered independently)", 320)


def tank_day(res, day_index=0):
    df = res["hourly"].iloc[day_index * 24:(day_index + 1) * 24]
    p = res["params"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Tank level (L)", "Hourly flows (L/h)"))
    fig.add_trace(go.Scatter(x=df["hour"], y=df["tank_L"], name="Tank level", line=dict(color=C[0], width=2)), 1, 1)
    fig.add_hline(y=p["ovf_level"] * p["tank_L"], line=dict(color="#52514e", dash="dot"), annotation_text="overflow lip", row=1, col=1)
    for i, (k, lab) in enumerate([("condensate_L", "Condensate in"), ("makeup_from_tank_L", "Reactor makeup"), ("overflow_L", "Overflow")]):
        fig.add_trace(go.Bar(x=df["hour"], y=df[k], name=lab, marker=dict(color=C[i], line=dict(width=0))), 1, 2)
    fig.update_layout(barmode="group", bargap=0.25)
    return _style(fig, "Clean tank during one day", 330)


def tank_series(res):
    df = res["hourly"]
    t = _t(df)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Tank level (L)", "Daily overflow (L/day)"))
    fig.add_trace(go.Scatter(x=t, y=df["tank_L"], line=dict(color=C[0], width=1.5), showlegend=False), 1, 1)
    d = res["daily"]
    fig.add_trace(go.Bar(x=np.arange(len(d)), y=d["overflow_L"], marker=dict(color=C[1]), showlegend=False), 1, 2)
    return _style(fig, "Tank level and overflow over the period", 320)


# --------------------------------------------------------------------- climate / humidity paradox
def humidity_paradox(res):
    m = res["monthly"]
    x = [MONTHS[i - 1] for i in m["month"]]
    days = m["hours"] / 24
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Condensate produced (L/day)", "Media cooling potential eff x (T-Twb) (K)"))
    fig.add_trace(go.Bar(x=x, y=m["condensate_L"] / days, marker=dict(color=C[0]), name="Condensate"), 1, 1)
    eff = res["params"]["media_eff"]
    fig.add_trace(go.Bar(x=x, y=eff * m["dT_psy"], marker=dict(color=C[1]), name="Psychrometric limit"), 1, 2)
    fig.add_trace(go.Scatter(x=x, y=m["dT_cond_active"], mode="lines+markers", line=dict(color="#0b0b0b", width=2),
                             marker=dict(size=8), name="Achieved (water-limited)"), 1, 2)
    return _style(fig, "Jeddah paradox: humid months give more condensate but less evaporative cooling potential", 360)


def scatter_rh(res, ycol, ytitle, title, color):
    df = res["hourly"]
    d = df[df["rtf"] > 0]
    fig = go.Figure(go.Scattergl(x=d["RH"], y=d[ycol], mode="markers", marker=dict(size=4, color=color, opacity=0.35),
                                 name=ytitle, hovertemplate="RH %{x:.0f}%<br>%{y:.2f}<extra></extra>"))
    fig.update_xaxes(title="Outdoor RH (%)")
    fig.update_yaxes(title=ytitle)
    return _style(fig, title, 330)


def humidity_vs_saving(res):
    m = res["monthly"]
    fig = go.Figure(go.Scatter(x=m["RH"], y=m["hvac_saving_kWh"] - m["fan_kWh"], mode="markers+text",
                               text=[MONTHS[i - 1] for i in m["month"]], textposition="top center",
                               marker=dict(size=10, color=C[1]), name="Monthly net HVAC saving"))
    fig.update_xaxes(title="Monthly mean outdoor RH (%)")
    fig.update_yaxes(title="Net HVAC saving (kWh/month)")
    return _style(fig, "Humidity vs AC electricity saved (after media fan penalty)", 340)


def temp_vs_growth(res):
    p = res["params"]
    T = np.linspace(15, 50, 141)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Temperature response used (relative)", "Simulated reactor temperature (share of hours)"))
    fig.add_trace(go.Scatter(x=T, y=[am.f_temp(t, p)[0] for t in T], line=dict(color=C[2], width=2), name=p["temp_profile"]), 1, 1)
    if p["temp_profile"] == "UTEX1230":
        pts = p["t_pts_utex1230"]
        fig.add_trace(go.Scatter(x=[a for a, _ in pts], y=[b for _, b in pts], mode="markers", marker=dict(size=9, color=C[0]),
                                 name="Published points (UTEX 1230)"), 1, 1)
    fig.add_vrect(x0=p["t_range_lo"], x1=p["t_range_hi"], fillcolor="rgba(12,163,12,0.08)", line_width=0, row=1, col=1)
    fig.add_trace(go.Histogram(x=res["hourly"]["T_r"], histnorm="probability", marker=dict(color=C[1]), name="Reactor T"), 1, 2)
    return _style(fig, "Temperature vs algae growth", 340)


# --------------------------------------------------------------------- tornado
def tornado(sens: pd.DataFrame, output: str, title: str):
    d = sens[sens["output"] == output].sort_values("swing")
    base = d["base"].iloc[0] if len(d) else 0
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["label"], x=d["at_low"] - base, base=base, orientation="h", name="parameter at LOW",
                         marker=dict(color=C[0]), hovertemplate="%{y}<br>low: %{x:+.2f}<extra></extra>"))
    fig.add_trace(go.Bar(y=d["label"], x=d["at_high"] - base, base=base, orientation="h", name="parameter at HIGH",
                         marker=dict(color=C[1]), hovertemplate="%{y}<br>high: %{x:+.2f}<extra></extra>"))
    fig.add_vline(x=base, line=dict(color="#0b0b0b", width=1))
    fig.update_layout(barmode="group", bargap=0.25, hovermode="closest")
    return _style(fig, title, 560)


def monthly_bars(res, cols, title, ytitle):
    m = res["monthly"]
    x = [MONTHS[i - 1] for i in m["month"]]
    fig = go.Figure()
    for i, (k, lab) in enumerate(cols):
        fig.add_trace(go.Bar(x=x, y=m[k], name=lab, marker=dict(color=C[i])))
    fig.update_layout(barmode="group", bargap=0.2)
    fig.update_yaxes(title=ytitle)
    return _style(fig, title, 340)
