"""Plotly figure factories. Titles live in the Streamlit card, not in the figure."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.metrics import fmt_money, fmt_pct

BLUE = "#2373F4"
BLUE_MID = "#578EF5"
CYAN = "#65D0F4"
HIGHLIGHT = "#F2F7A0"
BLUE_SOFT = "#C9DBFC"
NAVY = "#1E3A8A"
RED = "#D64550"
RED_SOFT = "#F3B7BC"
GREY = "#94A3B8"
INK = "#1E293B"
MUTED = "#64748B"
GRID = "#EEF2F7"
NEUTRAL_MID = "#F1F5F9"

DIVERGING = [[0.0, RED], [0.5, NEUTRAL_MID], [1.0, BLUE]]
SEQUENTIAL = [[0.0, "#EFF5FE"], [0.5, BLUE_MID], [1.0, NAVY]]


def _base(fig: go.Figure, height: int = 340, legend: bool = False, t: int = 10, b: int = 10) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=6, r=6, t=t, b=b),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK),
        showlegend=legend,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=12)),
        bargap=0.35,
    )
    if legend:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                                      title=dict(text=""), font=dict(size=11, color=MUTED)))
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=GRID, ticks="",
                     tickfont=dict(color=MUTED, size=11), title=dict(text=""))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, ticks="",
                     tickfont=dict(color=MUTED, size=11), title=dict(text=""))
    return fig


def _money_ticks(fig: go.Figure, axis: str = "y", **kw) -> None:
    upd = fig.update_yaxes if axis == "y" else fig.update_xaxes
    upd(tickprefix="$", tickformat="~s", **kw)


# ---------------------------------------------------------------- trends


def create_sales_trend_chart(yearly: pd.DataFrame) -> go.Figure:
    """Annual sales bars with margin line on a fixed 0-based secondary axis."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    years = yearly["Year"].astype(int).astype(str)
    fig.add_bar(x=years, y=yearly["Sales"], name="Sales", marker_color=BLUE,
                text=[fmt_money(v) for v in yearly["Sales"]], textposition="outside",
                cliponaxis=False, hovertemplate="%{x}<br>Sales %{y:$,.0f}<extra></extra>")
    fig.add_scatter(x=years, y=yearly["Margin"], name="Profit margin", mode="lines+markers+text",
                    line=dict(color=NAVY, width=2.5), marker=dict(size=8, color=NAVY),
                    text=[fmt_pct(v) for v in yearly["Margin"]], textposition="top center",
                    textfont=dict(color=NAVY), secondary_y=True,
                    hovertemplate="%{x}<br>Margin %{y:.1%}<extra></extra>")
    _base(fig, legend=True, t=30)
    ymax = float(np.nanmax([yearly["Margin"].max(), 0.2])) * 1.6
    fig.update_yaxes(tickprefix="$", tickformat="~s", secondary_y=False,
                     range=[0, float(yearly["Sales"].max()) * 1.18])
    fig.update_yaxes(tickformat=".0%", range=[0, ymax], showgrid=False, secondary_y=True)
    return fig


def create_annual_sales_profit_chart(yearly: pd.DataFrame) -> go.Figure:
    years = yearly["Year"].astype(int).astype(str)
    fig = go.Figure()
    for col, color in (("Sales", BLUE), ("Profit", CYAN)):
        yoy = yearly[col + " YoY"]
        labels = [fmt_money(v) for v in yearly[col]]
        hover = ["%s<br>%s %s<br>YoY %s" % (y, col, fmt_money(v, 2), fmt_pct(g, signed=True))
                 for y, v, g in zip(years, yearly[col], yoy)]
        fig.add_bar(x=years, y=yearly[col], name=col, marker_color=color, text=labels,
                    textposition="outside", cliponaxis=False, hovertext=hover, hoverinfo="text")
    _base(fig, legend=True, t=30)
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    _money_ticks(fig, range=[0, float(yearly["Sales"].max()) * 1.18])
    return fig


def create_monthly_trend_chart(monthly: pd.DataFrame) -> go.Figure:
    m = monthly.copy()
    m["Rolling"] = m["Sales"].rolling(3, min_periods=1).mean()
    fig = go.Figure()
    fig.add_scatter(x=m["Month"], y=m["Sales"], name="Monthly sales", mode="lines",
                    line=dict(color=BLUE_SOFT, width=1.5),
                    hovertemplate="%{x|%b %Y}<br>Sales %{y:$,.0f}<extra></extra>")
    fig.add_scatter(x=m["Month"], y=m["Rolling"], name="3-month average", mode="lines",
                    line=dict(color=BLUE, width=3),
                    hovertemplate="%{x|%b %Y}<br>3-mo avg %{y:$,.0f}<extra></extra>")
    _base(fig, legend=True, t=30)
    _money_ticks(fig, rangemode="tozero")
    return fig


def create_margin_trend_chart(quarterly: pd.DataFrame, overall: float) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=quarterly["Quarter"], y=quarterly["Margin"], mode="lines+markers",
                    line=dict(color=BLUE, width=2.5), marker=dict(size=6),
                    hovertemplate="%{x|%Y Q%q}<br>Margin %{y:.1%}<extra></extra>")
    if np.isfinite(overall):
        fig.add_hline(y=overall, line=dict(color=GREY, dash="dot", width=1.5),
                      annotation_text="Period avg " + fmt_pct(overall),
                      annotation_position="top left", annotation_font=dict(color=MUTED, size=11))
    _base(fig)
    lo = min(0.0, float(quarterly["Margin"].min()) * 1.2)
    hi = max(0.2, float(quarterly["Margin"].max()) * 1.3)
    fig.update_yaxes(tickformat=".0%", range=[lo, hi])
    return fig


def create_seasonality_chart(profile: pd.DataFrame) -> go.Figure:
    top = profile["Share"].nlargest(3).index
    colors = [BLUE if i in top else BLUE_SOFT for i in profile.index]
    fig = go.Figure(go.Bar(x=profile["Month"], y=profile["Share"], marker_color=colors,
                           text=[fmt_pct(v) for v in profile["Share"]], textposition="outside",
                           cliponaxis=False, hovertemplate="%{x}<br>%{y:.1%} of annual sales<extra></extra>"))
    _base(fig, t=20)
    fig.update_yaxes(tickformat=".0%", range=[0, float(profile["Share"].max()) * 1.25])
    return fig


def create_deep_discount_trend_chart(yearly: pd.DataFrame) -> go.Figure:
    years = yearly["Year"].astype(int).astype(str)
    fig = go.Figure(go.Bar(
        x=years, y=yearly["DeepProfit"], marker_color=[RED if v < 0 else BLUE for v in yearly["DeepProfit"]],
        text=[fmt_money(v) for v in yearly["DeepProfit"]], textposition="outside", cliponaxis=False,
        customdata=yearly["DeepShare"],
        hovertemplate="%{x}<br>Net profit %{y:$,.0f}<br>%{customdata:.1%} of lines<extra></extra>"))
    _base(fig, t=20, b=20)
    lo = float(min(yearly["DeepProfit"].min(), 0)) * 1.25
    hi = float(max(yearly["DeepProfit"].max(), 0)) * 1.25
    _money_ticks(fig, range=[lo, hi if hi > 0 else abs(lo) * 0.08])
    fig.add_hline(y=0, line=dict(color=GREY, width=1))
    return fig


# ---------------------------------------------------------------- profitability


def create_profit_waterfall(bands: pd.DataFrame) -> go.Figure:
    labels = bands["Band"].astype(str).tolist()
    values = bands["Profit"].tolist()
    total = float(np.nansum(values))
    fig = go.Figure(go.Waterfall(
        x=labels + ["Total profit"], y=values + [0], measure=["relative"] * len(values) + ["total"],
        text=[fmt_money(v) for v in values] + [fmt_money(total)], textposition="outside",
        increasing=dict(marker=dict(color=BLUE)), decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=NAVY)), connector=dict(line=dict(color=GRID, width=1)),
        hovertemplate="%{x}<br>%{y:$,.0f}<extra></extra>", cliponaxis=False))
    _base(fig, t=20)
    peak = float(max(np.nancumsum(values).max(), total, 0))
    _money_ticks(fig, range=[0, peak * 1.15])
    fig.update_xaxes(title=dict(text="Discount band", font=dict(size=11, color=MUTED)))
    return fig


def create_profitability_chart(bands: pd.DataFrame) -> go.Figure:
    """Margin by discount band; loss-making share shown in labels."""
    colors = [RED if v < 0 else BLUE for v in bands["Margin"].fillna(0)]
    text = ["%s<br><span style='font-size:10px;color:%s'>%s lose money</span>" % (fmt_pct(m), MUTED, fmt_pct(ls, 0))
            for m, ls in zip(bands["Margin"], bands["LossShare"])]
    fig = go.Figure(go.Bar(
        x=bands["Band"].astype(str), y=bands["Margin"], marker_color=colors, text=text,
        textposition="outside", cliponaxis=False, customdata=np.stack([bands["Lines"], bands["LossShare"]], axis=1),
        hovertemplate="%{x}<br>Margin %{y:.1%}<br>%{customdata[0]:,} lines<br>%{customdata[1]:.0%} loss-making<extra></extra>"))
    _base(fig, t=30, b=10)
    lo = float(min(bands["Margin"].min(), 0)) * 1.3
    hi = float(max(bands["Margin"].max(), 0)) * 1.45
    fig.update_yaxes(tickformat=".0%", range=[lo, hi])
    fig.update_xaxes(title=dict(text="Discount band", font=dict(size=11, color=MUTED)))
    fig.add_hline(y=0, line=dict(color=GREY, width=1))
    return fig


def create_heatmap(matrix: pd.DataFrame) -> go.Figure:
    z = matrix.values.astype(float)
    text = [[fmt_pct(v, 0) if np.isfinite(v) else "" for v in row] for row in z]
    lim = float(np.nanmax(np.abs(z))) if np.isfinite(z).any() else 1.0
    fig = go.Figure(go.Heatmap(
        z=z, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index], text=text,
        texttemplate="%{text}", textfont=dict(size=12), colorscale=DIVERGING, zmid=0,
        zmin=-lim, zmax=lim, xgap=3, ygap=3, colorbar=dict(tickformat=".0%", thickness=10, outlinewidth=0),
        hovertemplate="%{y} | %{x}<br>Margin %{z:.1%}<extra></extra>"))
    _base(fig, height=320)
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(side="top", title=dict(text=""))
    return fig


def create_dumbbell(split: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for _, r in split.iterrows():
        fig.add_scatter(x=[r["Overall"], r["Excluding deep discounts"]], y=[r["Market"]] * 2, mode="lines",
                        line=dict(color=BLUE_SOFT, width=4), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=split["Overall"], y=split["Market"], mode="markers", name="Actual margin",
                    marker=dict(color=GREY, size=12), hovertemplate="%{y}<br>Actual %{x:.1%}<extra></extra>")
    fig.add_scatter(x=split["Excluding deep discounts"], y=split["Market"], mode="markers",
                    name="Margin on lines discounted 30% or less", marker=dict(color=BLUE, size=12),
                    hovertemplate="%{y}<br>Excl. deep discounts %{x:.1%}<extra></extra>")
    _base(fig, legend=True, t=30)
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=GRID, rangemode="tozero")
    fig.update_yaxes(showgrid=False)
    return fig


def create_country_scatter(countries: pd.DataFrame, fit: bool = True) -> go.Figure:
    c = countries.copy()
    colors = np.where(c["Margin"] < 0, RED, BLUE)
    size = np.sqrt(c["Sales"].clip(lower=0))
    size = 6 + 30 * size / size.max() if size.max() > 0 else 10
    fig = go.Figure(go.Scatter(
        x=c["DeepShare"], y=c["Margin"], mode="markers", text=c["Country"],
        marker=dict(size=size, color=colors, opacity=0.65, line=dict(width=0.5, color="white")),
        customdata=np.stack([c["Sales"], c["Profit"]], axis=1),
        hovertemplate="%{text}<br>Deep-discount share %{x:.0%}<br>Margin %{y:.1%}<br>Sales %{customdata[0]:$,.0f}<br>Profit %{customdata[1]:$,.0f}<extra></extra>"))
    if fit and len(c) >= 3 and c["DeepShare"].std() > 0:
        slope, intercept = np.polyfit(c["DeepShare"], c["Margin"], 1)
        xs = np.linspace(c["DeepShare"].min(), c["DeepShare"].max(), 20)
        fig.add_scatter(x=xs, y=slope * xs + intercept, mode="lines", line=dict(color=NAVY, dash="dash", width=1.5),
                        hoverinfo="skip", showlegend=False)
    _base(fig)
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor=GRID,
                     title=dict(text="Share of lines discounted above 30%", font=dict(size=11, color=MUTED)))
    fig.update_yaxes(tickformat=".0%", title=dict(text="Profit margin", font=dict(size=11, color=MUTED)))
    fig.add_hline(y=0, line=dict(color=GREY, width=1))
    return fig


def create_factor_chart(summary: pd.DataFrame, label_col: str, overall: float) -> go.Figure:
    s = summary.sort_values("Margin")
    fig = go.Figure(go.Bar(
        y=s[label_col].astype(str), x=s["Margin"], orientation="h", marker_color=BLUE_MID,
        text=[fmt_pct(v) for v in s["Margin"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>Margin %{x:.1%}<extra></extra>"))
    if np.isfinite(overall):
        fig.add_vline(x=overall, line=dict(color=NAVY, dash="dot", width=1.5))
    _base(fig, height=220)
    fig.update_xaxes(tickformat=".0%", range=[0, max(float(s["Margin"].max()), 0.05) * 1.35], showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return fig


# ---------------------------------------------------------------- markets and products


def create_ranked_bar(df: pd.DataFrame, label_col: str, value_col: str, kind: str = "money",
                      height: int = 360) -> go.Figure:
    d = df.sort_values(value_col)
    fmt = fmt_money if kind == "money" else fmt_pct
    colors = [RED if v < 0 else BLUE for v in d[value_col]]
    fig = go.Figure(go.Bar(
        y=d[label_col].astype(str), x=d[value_col], orientation="h", marker_color=colors,
        text=[fmt(v) for v in d[value_col]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x:" + ("$,.0f" if kind == "money" else ".1%") + "}<extra></extra>"))
    _base(fig, height=height)
    lo, hi = float(min(d[value_col].min(), 0)), float(max(d[value_col].max(), 0))
    pad = (hi - lo) * 0.18 or 1
    rng = [lo - (pad if lo < 0 else 0), hi + (pad if hi > 0 else 0)]
    if kind == "money":
        _money_ticks(fig, axis="x", range=rng, showgrid=True, gridcolor=GRID)
    else:
        fig.update_xaxes(tickformat=".0%", range=rng, showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return fig


def create_market_bubble(markets: pd.DataFrame, overall: float) -> go.Figure:
    size = np.sqrt(markets["Profit"].abs())
    size = 14 + 40 * size / size.max() if size.max() > 0 else 20
    colors = [RED if m < 0 else BLUE for m in markets["Margin"]]
    fig = go.Figure(go.Scatter(
        x=markets["Sales"], y=markets["Margin"], mode="markers+text", text=markets["Market"],
        textposition="top center", textfont=dict(size=12, color=INK),
        marker=dict(size=size, color=colors, opacity=0.75, line=dict(width=1, color="white")),
        customdata=np.stack([markets["Profit"], markets["DeepShare"]], axis=1),
        hovertemplate="%{text}<br>Sales %{x:$,.0f}<br>Margin %{y:.1%}<br>Profit %{customdata[0]:$,.0f}<br>Deep-discount lines %{customdata[1]:.0%}<extra></extra>"))
    if np.isfinite(overall):
        fig.add_hline(y=overall, line=dict(color=GREY, dash="dot", width=1.5),
                      annotation_text="Company margin " + fmt_pct(overall), annotation_position="bottom right",
                      annotation_font=dict(color=MUTED, size=11))
    _base(fig, t=20)
    _money_ticks(fig, axis="x", showgrid=True, gridcolor=GRID,
                 title=dict(text="Sales", font=dict(size=11, color=MUTED)))
    hi = max(float(markets["Margin"].max()), 0.05) * 1.25
    lo = min(float(markets["Margin"].min()), 0) * 1.25
    fig.update_yaxes(tickformat=".0%", range=[lo, hi], title=dict(text="Profit margin", font=dict(size=11, color=MUTED)))
    return fig


def create_choropleth(countries: pd.DataFrame, metric: str) -> go.Figure:
    c = countries.copy()
    if metric == "Sales":
        scale, mid, fmt = SEQUENTIAL, None, "$,.0f"
    elif metric == "Profit":
        scale, mid, fmt = DIVERGING, 0, "$,.0f"
    else:
        scale, mid, fmt = DIVERGING, 0, ".1%"
    fig = px.choropleth(c, locations="Country", locationmode="country names", color=metric,
                        color_continuous_scale=scale, color_continuous_midpoint=mid,
                        hover_name="Country",
                        hover_data={"Country": False, "Market": True, "Sales": ":$,.0f",
                                    "Profit": ":$,.0f", "Margin": ":.1%"})
    fig.update_geos(showframe=False, showcoastlines=False, showcountries=True, countrycolor="white",
                    showland=True, landcolor="#E9EEF5", projection_type="natural earth",
                    bgcolor="rgba(0,0,0,0)", lataxis_range=[-58, 85])
    _base(fig, height=430)
    fig.update_layout(coloraxis_colorbar=dict(thickness=10, outlinewidth=0, title=dict(text=""),
                                              tickformat=fmt.replace("$", "").replace(",", "") if metric == "Margin" else "~s",
                                              tickprefix="" if metric == "Margin" else "$"))
    return fig


def create_treemap(subcats: pd.DataFrame) -> go.Figure:
    lim = float(np.nanmax(np.abs(subcats["Margin"]))) if len(subcats) else 0.3
    fig = px.treemap(subcats, path=[px.Constant("All products"), "Category", "Sub-Category"],
                     values="Sales", color="Margin", color_continuous_scale=DIVERGING,
                     range_color=[-lim, lim], custom_data=["Profit", "Margin"])
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{value:$,.3s}<br>%{color:.1%}",
        hovertemplate="<b>%{label}</b><br>Sales %{value:$,.0f}<br>Margin %{color:.1%}<extra></extra>",
        marker=dict(line=dict(color="white", width=2)), root_color="#F4F7FC", tiling=dict(pad=3))
    _base(fig, height=440)
    fig.update_layout(coloraxis_colorbar=dict(thickness=10, outlinewidth=0, tickformat=".0%", title=dict(text="")))
    return fig


def create_pareto_chart(pareto: pd.DataFrame, n80, share80) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=pareto["Item share"], y=pareto["Cum share"], mode="lines", fill="tozeroy",
                    line=dict(color=BLUE, width=2.5), fillcolor="rgba(35,115,244,0.10)",
                    hovertemplate="Top %{x:.0%} of products<br>%{y:.0%} of sales<extra></extra>")
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=GREY, dash="dot", width=1),
                    hoverinfo="skip")
    if np.isfinite(share80):
        fig.add_scatter(x=[share80], y=[0.8], mode="markers", marker=dict(color=NAVY, size=10),
                        hoverinfo="skip")
        fig.add_annotation(x=share80, y=0.8, ax=50, ay=40, text="%s of products = 80%% of sales" % fmt_pct(share80, 0),
                           showarrow=True, arrowcolor=MUTED, font=dict(color=INK, size=12),
                           bgcolor=HIGHLIGHT, borderpad=4)
    _base(fig)
    fig.update_xaxes(tickformat=".0%", range=[0, 1], showgrid=True, gridcolor=GRID,
                     title=dict(text="Share of products (ranked by sales)", font=dict(size=11, color=MUTED)))
    fig.update_yaxes(tickformat=".0%", range=[0, 1.02],
                     title=dict(text="Cumulative share of sales", font=dict(size=11, color=MUTED)))
    return fig
