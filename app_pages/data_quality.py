import pandas as pd
import streamlit as st

from utils import metrics as m
from utils import ui
from utils.data_loader import (DEEP_DISCOUNT, data_dictionary, derived_dictionary, get_filtered_data, load_data,
                               quality_report)

fd = get_filtered_data()
full = load_data()
rep = quality_report()
checks = m.run_validation_checks(full, rep)
n_pass = int((checks["Status"] == "Pass").sum())

headline = "%s order lines, %d columns, %s to %s - %d of %d validation checks pass" % (
    "{:,}".format(rep["raw_rows"]), rep["raw_cols"], rep["date_min"].strftime("%d %b %Y"),
    rep["date_max"].strftime("%d %b %Y"), n_pass, len(checks))
summary = ("Each row is one order line (a product within an order). The file has no duplicate rows and only one "
           "column with missing values (Postal Code, filled for US rows only). All checks below run on the full dataset.")
ui.page_header("Data and methodology", headline, summary, fd)

with st.container(horizontal=True):
    st.metric("Order lines", "{:,}".format(rep["raw_rows"]), border=True)
    st.metric("Orders", "{:,}".format(rep["order_keys"]), border=True, help="Distinct Order ID + Order Date.")
    st.metric("Countries", rep["countries"], border=True)
    st.metric("Markets", rep["markets"], border=True)
    st.metric("Products", "{:,}".format(rep["product_names"]), border=True, help="Distinct Product Name values.")
    st.metric("Rows removed in cleaning", rep["dropped_rows"], border=True)

tab1, tab2, tab3, tab4 = st.tabs(["Data dictionary", "Data quality", "KPI definitions", "Business questions"])

with tab1:
    st.dataframe(data_dictionary(full), hide_index=True, column_config={
        "Business meaning": st.column_config.TextColumn(width="large"),
        "Potential use": st.column_config.TextColumn(width="medium"),
    })
    st.markdown("**Derived fields created during cleaning**")
    st.dataframe(derived_dictionary(), hide_index=True)

with tab2:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("**Validation checks**")
        st.dataframe(checks, hide_index=True, column_config={
            "Result": st.column_config.TextColumn(width="large"),
        })
    with c2:
        st.markdown("**Missing values by column**")
        miss = rep["missing_table"]
        st.dataframe(miss[miss["Missing values"] > 0], hide_index=True, column_config={
            "Missing %": st.column_config.NumberColumn(format="percent"),
        })
        st.caption(ui.md("%s of missing postal codes are outside the United States, so the gap is structural "
                         "and the column is not used." % m.fmt_pct(rep["postal_missing_non_us_share"], 0)))
        st.markdown("**Identifier caveats**")
        st.markdown(ui.md(
            "- Order ID: %s distinct IDs but %s ID + date combinations, so orders are counted on both.\n"
            "- Customer ID: %s IDs for %s names (IDs are region-specific).\n"
            "- Product ID: %s IDs for %s names." % (
                "{:,}".format(rep["order_ids"]), "{:,}".format(rep["order_keys"]),
                "{:,}".format(rep["customer_ids"]), "{:,}".format(rep["customer_names"]),
                "{:,}".format(rep["product_ids"]), "{:,}".format(rep["product_names"]))))
    st.markdown("**Cleaning steps applied**")
    st.markdown(ui.md(
        "1. Read CSV as latin-1; trim whitespace in column names and text fields.\n"
        "2. Parse Order Date and Ship Date as day-month-year; coerce invalid values to missing.\n"
        "3. Convert numeric columns; drop exact duplicates and lines without date, sales or profit.\n"
        "4. Keep lines with positive sales; clip discount to 0-100%%.\n"
        "5. Derive Year, Quarter, Month, Order Key, Discount Band, Deep Discount (> %d%%), Line Margin, Is Loss.\n"
        "6. Replace infinite ratios with missing; ratios with a zero denominator return n/a instead of an error."
        % int(DEEP_DISCOUNT * 100)))

with tab3:
    kpi = pd.DataFrame([
        ("Sales", "Sum of Sales", "Revenue scale", "Higher is better"),
        ("Profit", "Sum of Profit", "Bottom-line contribution", "Higher is better"),
        ("Profit margin", "Profit / Sales", "Profit per dollar sold", "Higher is better"),
        ("Orders", "Distinct (Order ID + Order Date)", "Transaction volume", "Higher is better"),
        ("Avg order value", "Sales / Orders", "Basket size", "Higher is better"),
        ("YoY growth", "(Current - Previous) / |Previous|", "Momentum vs last year", "Higher is better"),
        ("Margin change", "Margin(t) - Margin(t-1), in pp", "Profitability trend", "Higher is better"),
        ("CAGR", "(End / Begin)^(1 / years) - 1", "Compound annual growth", "Higher is better"),
        ("Deep-discount share", "Lines with Discount > 30% / all lines", "Exposure to loss-making pricing", "Lower is better"),
        ("Deep-discount losses", "-(Sum of Profit on lines with Discount > 30%)", "Profit given away", "Lower is better"),
        ("Loss-line share", "Lines with Profit < 0 / all lines", "Breadth of losses", "Lower is better"),
        ("Pareto 80%", "Smallest share of products reaching 80% of sales", "Revenue concentration", "Context"),
    ], columns=["KPI", "Formula", "Business meaning", "Direction"])
    st.dataframe(kpi, hide_index=True, column_config={"Formula": st.column_config.TextColumn(width="large")})
    st.caption("Division by zero returns n/a. CAGR needs two or more years and positive start and end values.")

with tab4:
    qs = pd.DataFrame([
        ("WHAT", "How have sales, profit and margin performed?", "Executive overview, Trends"),
        ("WHEN", "Is growth consistent year on year, and is demand seasonal?", "Trends"),
        ("WHERE", "Which markets, countries and segments create or destroy profit?", "Markets and segments"),
        ("WHICH", "Which categories, sub-categories and products drive or drain profit?", "Products"),
        ("WHY", "What is associated with low or negative margin?", "Profitability root cause"),
        ("SO WHAT", "How much profit is at stake and what does it mean for the business?", "Strategic insights"),
        ("WHAT NEXT", "Which actions should management take first?", "Strategic insights"),
    ], columns=["Question type", "Business question", "Answered on page"])
    st.dataframe(qs, hide_index=True, column_config={"Business question": st.column_config.TextColumn(width="large")})
