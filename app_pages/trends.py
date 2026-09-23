import streamlit as st

from utils import charts as ch
from utils import metrics as m
from utils import ui
from utils.data_loader import get_filtered_data

fd = get_filtered_data()
ui.require_data(fd)

tot = m.summarize(fd.df)
yearly = m.yearly_summary(fd.df)
monthly = m.period_summary(fd.df, "Month")
quarterly = m.period_summary(fd.df, "Quarter")
season = m.seasonality_profile(fd.df)

yoy = yearly["Sales YoY"].dropna()
if len(yoy):
    headline = "Sales grew in %d of %d years; growth ranged from %s to %s" % (
        int((yoy > 0).sum()), len(yoy), m.fmt_pct(yoy.min()), m.fmt_pct(yoy.max()))
else:
    headline = "Sales pattern within %d" % fd.end

peak = season.nlargest(3, "Share")
low = season.nsmallest(1, "Share").iloc[0]
q4 = season.loc[season["Month Num"] >= 10, "Share"].sum()
summary = ("Demand is seasonal: %s are the three strongest months and Q4 carries %s of annual sales on average, "
           "while %s is the weakest month (%s)." % (
               ", ".join(peak["Month"]), m.fmt_pct(q4), low["Month"], m.fmt_pct(low["Share"])))
ui.page_header("Performance trends", headline, summary, fd)

c1, c2 = st.columns([3, 2])
with c1:
    ui.chart_card("Sales and profit rose each year" if len(yoy) and (yoy > 0).all() else "Annual sales and profit",
                  "Annual totals; hover for year-on-year growth",
                  ch.create_annual_sales_profit_chart(yearly), key="tr_annual")
with c2:
    with st.container(border=True):
        st.markdown("**Year-on-year scorecard**")
        st.caption("Growth vs prior year; margin change in percentage points")
        tbl = yearly[["Year", "Sales", "Sales YoY", "Profit", "Profit YoY", "Margin", "Margin change", "Orders"]].copy()
        tbl["Margin change"] = tbl["Margin change"] * 100
        st.dataframe(
            tbl, hide_index=True,
            column_config={
                "Year": st.column_config.NumberColumn(format="%d"),
                "Sales": st.column_config.NumberColumn(format="dollar"),
                "Sales YoY": st.column_config.NumberColumn(format="percent"),
                "Profit": st.column_config.NumberColumn(format="dollar"),
                "Profit YoY": st.column_config.NumberColumn(format="percent"),
                "Margin": st.column_config.NumberColumn(format="percent"),
                "Margin change": st.column_config.NumberColumn("Margin chg (pp)", format="%+.1f"),
                "Orders": st.column_config.NumberColumn(format="localized"),
            },
        )
        cagr_s = m.calculate_cagr(yearly["Sales"].iloc[0], yearly["Sales"].iloc[-1], len(yearly) - 1)
        cagr_p = m.calculate_cagr(yearly["Profit"].iloc[0], yearly["Profit"].iloc[-1], len(yearly) - 1)
        st.caption(ui.md("CAGR %s: sales %s, profit %s. CAGR = (End / Begin)^(1 / years) - 1." % (
            "%d-%d" % (fd.start, fd.end), m.fmt_pct(cagr_s), m.fmt_pct(cagr_p))))

ui.chart_card(
    "Monthly sales climb through the year and peak in the fourth quarter" if q4 > 0.30
    else "Monthly sales with 3-month moving average",
    "Monthly sales (light line) and 3-month moving average (bold line)",
    ch.create_monthly_trend_chart(monthly), key="tr_monthly")

c3, c4 = st.columns(2)
with c3:
    qm = quarterly["Margin"]
    title = "Quarterly margin stays in a %s-%s band with no upward drift" % (m.fmt_pct(qm.min(), 0), m.fmt_pct(qm.max(), 0)) \
        if len(qm) >= 4 else "Quarterly profit margin"
    ui.chart_card(title, "Profit / Sales by quarter; dotted line = period average",
                  ch.create_margin_trend_chart(quarterly, tot["margin"]), key="tr_margin")
with c4:
    ui.chart_card("Peak months: " + ", ".join(peak["Month"]),
                  "Average share of each year's sales by calendar month (top 3 highlighted)",
                  ch.create_seasonality_chart(season), key="tr_season")

dm = yearly["Margin"].iloc[-1] - yearly["Margin"].iloc[0] if len(yearly) >= 2 else float("nan")
if len(yoy) and (yoy > 0).all():
    growth_part = "Sales grew in every year of the selection"
elif len(yoy):
    growth_part = "Sales grew in %d of %d years" % (int((yoy > 0).sum()), len(yoy))
else:
    growth_part = "Only one year is selected"
ui.insight_box(
    finding="%s, while margin changed %s between the first and last year and quarterly margin oscillated around %s." % (
        growth_part, m.fmt_pp(dm), m.fmt_pct(tot["margin"])),
    implication="Scale economies are not reaching the bottom line; volume growth alone will not lift profitability. "
                "Q4 concentration also means pricing decisions made in Q4 have an outsized effect on the full year.",
    action="Track margin, not just sales, as a monthly board KPI, and apply the discount guardrail before the Q4 peak.",
)
