import streamlit as st

from utils import charts as ch
from utils import metrics as m
from utils import ui
from utils.data_loader import get_filtered_data

fd = get_filtered_data()
ui.require_data(fd)

tot = m.summarize(fd.df)
yearly = m.yearly_summary(fd.df)
bands = m.discount_band_summary(fd.df)
kpis = m.calculate_kpis(fd)

summary = "Across the selection the business sold %s and earned %s in profit (%s margin). %s" % (
    m.fmt_money(tot["sales"]), m.fmt_money(tot["profit"]), m.fmt_pct(tot["margin"]),
    m.deep_discount_sentence(tot))
ui.page_header("Executive overview", m.growth_headline(yearly), summary, fd)

prev_note = ("KPI cards show %d; deltas compare with %d. Sparklines trace %s."
             % (fd.end, fd.end - 1, "%d-%d" % (fd.start, fd.end) if fd.n_years > 1 else "a single year (hidden)"))
ui.kpi_row(kpis, prev_note)

# ---- row 1: growth vs margin | where profit is made and lost
c1, c2 = st.columns(2)
with c1:
    if len(yearly) >= 2:
        f, l = yearly.iloc[0], yearly.iloc[-1]
        title = "Sales rose from %s to %s; margin moved from %s to %s" % (
            m.fmt_money(f["Sales"]), m.fmt_money(l["Sales"]), m.fmt_pct(f["Margin"]), m.fmt_pct(l["Margin"]))
    else:
        title = "Sales and margin for %d" % fd.end
    ui.chart_card(title, "Annual sales (bars, left axis) and profit margin (line, right axis, starts at 0%)",
                  ch.create_sales_trend_chart(yearly), key="ov_trend")
with c2:
    pos = bands.loc[bands["Profit"] > 0, "Profit"].sum()
    neg = bands.loc[bands["Profit"] < 0, "Profit"].sum()
    if neg < 0:
        title = "Discount bands that lose money give back %s of the %s earned elsewhere" % (
            m.fmt_pct(abs(neg) / pos if pos > 0 else float("nan"), 0), m.fmt_money(pos))
    else:
        title = "Every discount band is profitable in this selection"
    ui.chart_card(title, "Contribution of each discount band to total profit",
                  ch.create_profit_waterfall(bands), key="ov_waterfall")

# ---- row 2: deep-discount trend | key insight
c3, c4 = st.columns([3, 2])
with c3:
    if len(yearly) >= 2 and yearly["DeepProfit"].iloc[0] < 0 and yearly["DeepProfit"].iloc[-1] < 0:
        a, b = abs(yearly["DeepProfit"].iloc[0]), abs(yearly["DeepProfit"].iloc[-1])
        title = "Losses on deep-discount lines went from %s to %s a year (%sx)" % (
            m.fmt_money(a), m.fmt_money(b), "%.1f" % (b / a) if a else "n/a")
    else:
        title = "Net profit on lines discounted above 30%, by year"
    ui.chart_card(title, "Net profit on order lines discounted above 30%. Hover for share of lines.",
                  ch.create_deep_discount_trend_chart(yearly), key="ov_deep")
with c4:
    cagr = m.calculate_cagr(yearly["Sales"].iloc[0], yearly["Sales"].iloc[-1], len(yearly) - 1)
    growth_txt = ("Sales compounded %s a year" % m.fmt_pct(cagr)) if m._finite(cagr) else "Sales scale is shown for one year only"
    ui.insight_box(
        finding="%s, yet margin stayed near %s. Lines discounted above 30%% make up %s of volume and ran at a %s margin." % (
            growth_txt, m.fmt_pct(tot["margin"]), m.fmt_pct(tot["deep_share"]), m.fmt_pct(tot["deep_margin"])),
        implication="Growth adds revenue but not profitability per dollar: the loss-making slice grows in step with the "
                    "healthy business, so each extra dollar of sales carries the same drag.",
        action="Phase the response: eliminate discounts above 50% now, pilot a 20% ceiling with approval for exceptions "
               "in the heaviest-discounting markets, then scale globally if volume holds. See the root-cause and "
               "strategy pages for the evidence and the full plan.",
    )
