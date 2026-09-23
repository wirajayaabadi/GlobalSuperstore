import streamlit as st

from utils import charts as ch
from utils import metrics as m
from utils import ui
from utils.data_loader import get_filtered_data

fd = get_filtered_data()
ui.require_data(fd)

tot = m.summarize(fd.df)
subcats = m.group_summary(fd.df, ["Category", "Sub-Category"])
cats = m.group_summary(fd.df, "Category").sort_values("Profit", ascending=False)
pareto = m.pareto_table(fd.df)
n80, share80 = m.items_for_share(pareto, 0.8)
losses = m.loss_products(fd.df, top=15)
all_loss = m.group_summary(fd.df, "Product Name")
loss_items = all_loss[all_loss["Profit"] < 0]

best = subcats.sort_values("Profit", ascending=False).iloc[0]
worst = subcats.sort_values("Profit").iloc[0]
if worst["Profit"] < 0:
    headline = "%s earns the most profit (%s); %s loses %s" % (
        best["Sub-Category"], m.fmt_money(best["Profit"]), worst["Sub-Category"], m.fmt_money(abs(worst["Profit"])))
else:
    headline = "%s earns the most profit (%s); every sub-category is profitable" % (
        best["Sub-Category"], m.fmt_money(best["Profit"]))
summary = ("%s of products (%s of %s) generate 80%% of sales. %s products are loss-making in aggregate, "
           "costing %s." % (m.fmt_pct(share80, 0), m.fmt_int(n80), m.fmt_int(len(pareto)),
                            m.fmt_int(len(loss_items)), m.fmt_money(abs(loss_items["Profit"].sum()))))
ui.page_header("Product analysis", headline, summary, fd)

low_cat = cats.sort_values("Margin").iloc[0]
ui.chart_card(
    "%s is %s of sales but runs a %s margin" % (low_cat["Category"], m.fmt_pct(low_cat["Sales share"], 0),
                                              m.fmt_pct(low_cat["Margin"])),
    "Box size = sales; colour = profit margin (red = loss, blue = healthy). Click a category to zoom.",
    ch.create_treemap(subcats), key="pr_treemap")

c1, c2 = st.columns(2)
with c1:
    ui.chart_card("Profit by sub-category, ranked", "Total profit; red bars lose money",
                  ch.create_ranked_bar(subcats, "Sub-Category", "Profit", height=460), key="pr_rank")
with c2:
    ui.chart_card("Sales are concentrated: %s of products bring 80%% of revenue" % m.fmt_pct(share80, 0),
                  "Pareto curve of product sales; dotted line = perfectly even distribution",
                  ch.create_pareto_chart(pareto, n80, share80), key="pr_pareto")

with st.container(border=True):
    if len(losses):
        st.markdown("**Top %d loss-making products lose %s at an average discount of %s**" % (
            len(losses), ui.md(m.fmt_money(abs(losses["Profit"].sum()))), m.fmt_pct(losses["AvgDiscount"].mean(), 0)))
        st.caption("Products ranked by total loss in the selection")
        st.dataframe(
            losses[["Product Name", "Sub-Category", "Sales", "Profit", "Margin", "AvgDiscount", "Lines"]],
            hide_index=True,
            column_config={
                "Product Name": st.column_config.TextColumn(width="large"),
                "Sales": st.column_config.NumberColumn(format="dollar"),
                "Profit": st.column_config.NumberColumn(format="dollar"),
                "Margin": st.column_config.NumberColumn(format="percent"),
                "AvgDiscount": st.column_config.NumberColumn("Avg discount", format="percent"),
            },
        )
    else:
        st.success("No loss-making products in the current selection.", icon=":material/check_circle:")

w_lines = fd.df[fd.df["Sub-Category"] == worst["Sub-Category"]]
w_deep = w_lines.loc[w_lines["Deep Discount"], "Profit"].sum()
w_rest = w_lines.loc[~w_lines["Deep Discount"], "Profit"].sum()
ui.insight_box(
    finding="%s runs at %s with an average discount of %s (company margin %s). Its lines discounted above 30%% "
            "net %s, while its other lines net %s." % (
                worst["Sub-Category"], m.fmt_pct(worst["Margin"]), m.fmt_pct(worst["AvgDiscount"], 0),
                m.fmt_pct(tot["margin"]), m.fmt_money(w_deep), m.fmt_money(w_rest)),
    implication=("Product-level losses sit where discounts are heaviest, so the weakest products are a pricing problem "
                 "before they are a range problem (see the root-cause page).") if w_rest > 0 else
                ("%s loses money even without deep discounts, which points to a cost or range issue on top of "
                 "pricing." % worst["Sub-Category"]),
    action="Remove deep-discount eligibility from %s and the listed loss-makers first, and review the long tail of "
           "products outside the top %s for range rationalisation." % (worst["Sub-Category"], m.fmt_int(n80)),
)
