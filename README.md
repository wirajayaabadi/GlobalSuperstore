# Global Superstore - Executive Business Analytics Dashboard

Board-level Streamlit dashboard built on `data/Global_Superstore2.csv` (51,290 order lines, Jan 2011 - Dec 2014).
Every number on screen is computed live from the dataset; nothing is estimated or invented.

## 1. Dataset assessment

| Item | Result |
|---|---|
| Dimensions | 51,290 rows x 24 columns; one row = one order line |
| Date range | 01 Jan 2011 - 31 Dec 2014 (4 full years) |
| Duplicates | 0 duplicate rows, 0 duplicate Row IDs |
| Missing values | Only `Postal Code` (41,296 = 80.5%); 100% of the gaps are non-US rows, so it is structural |
| Date validity | All dates parse (dd-mm-yyyy); no ship date before order date |
| Encoding | latin-1 (some product names contain accented characters) |
| Identifier caveats | 25,035 Order IDs but 25,752 Order ID + date combinations; 1,590 Customer IDs for 795 names; 10,292 Product IDs for 3,788 names |
| Shipping Cost | Present per line, but the data does not say whether it is already in Profit, so it is never deducted from Profit. It is reported as a share of Sales (freight burden), a ratio of two observed columns that needs no such assumption |

Variable roles: **time** (Order Date, Ship Date), **measures** (Sales, Profit, Quantity, Discount, Shipping Cost),
**dimensions** (Market, Region, Country, Segment, Category, Sub-Category, Ship Mode, Order Priority),
**identifiers** (Row ID, Order ID, Customer ID, Product ID). The full data dictionary is on the
*Data and methodology* page.

## 2. Business questions

| Type | Question | Page |
|---|---|---|
| WHAT | How have sales, profit and margin performed? | Executive overview, Trends |
| WHEN | Is growth consistent, and is demand seasonal? | Trends |
| WHERE | Which markets, countries and segments create or destroy profit? | Markets and segments |
| WHICH | Which categories and products drive or drain profit? | Products |
| WHY | What is associated with low or negative margin? | Profitability root cause |
| SO WHAT | How much profit is at stake? | Strategic insights |
| WHAT NEXT | Which actions come first? | Strategic insights |

## 3. Dashboard architecture

```
executive_dashboard/
  app.py                    entry point: page config, navigation, sidebar filters
  app_pages/
    overview.py             Executive overview (headline, 6 KPIs, 3 charts, key insight)
    trends.py               Annual, monthly, quarterly margin, seasonality, YoY scorecard
    markets.py              World map, market bubble, market ranking, segments, loss countries
    products.py             Treemap, sub-category ranking, Pareto, loss-making products
    root_cause.py           Discount bands, country scatter, market x discount heatmap, alternatives checked
    strategy.py             Value at stake, 5 findings (Fact / Interpretation / Recommendation), action plan
    data_quality.py         Data dictionary, validation checks, KPI definitions, business questions
  utils/
    data_loader.py          load_data, clean_data, quality_report, apply_filters (cached)
    metrics.py              calculate_kpis, calculate_growth, calculate_cagr, summaries, validation checks
    charts.py               Plotly factories (create_sales_trend_chart, create_profitability_chart, ...)
    ui.py                   page header, KPI row, chart card, insight boxes
  data/Global_Superstore2.csv
  .streamlit/config.toml    corporate theme (#2373F4 / #578EF5 / #65D0F4 / #F2F7A0)
  requirements.txt
```

## 4. KPI definitions

| KPI | Formula | Direction |
|---|---|---|
| Sales | Sum of Sales | Higher is better |
| Profit | Sum of Profit | Higher is better |
| Profit margin | Profit / Sales | Higher is better |
| Orders | Distinct (Order ID + Order Date) | Higher is better |
| Avg order value | Sales / Orders | Higher is better |
| YoY growth | (Current - Previous) / abs(Previous) | Higher is better |
| Margin change | Margin(t) - Margin(t-1), percentage points | Higher is better |
| CAGR | (End / Begin)^(1 / years) - 1 | Higher is better |
| Deep-discount share | Lines with Discount > 30% / all lines | Lower is better |
| Deep-discount losses | -(Sum of Profit on lines with Discount > 30%) | Lower is better |

KPI cards show the last selected year and compare it with the year before (the year filter is relaxed for the
comparison; market/segment/category filters still apply). Division by zero returns n/a.

## 5. Visualization plan

| Chart | Question answered | Type | X | Y | Purpose |
|---|---|---|---|---|---|
| Sales and margin | Is growth translating into margin? | Bar + line (0-based right axis) | Year | Sales, Margin | Growth vs profitability |
| Profit waterfall | Where is profit made and lost? | Waterfall | Discount band | Profit contribution | Show value destruction |
| Deep-discount trend | Is the problem growing? | Bar | Year | Net profit on >30% lines | Urgency |
| Annual sales and profit | How fast are we growing? | Grouped bar | Year | Sales, Profit | Momentum |
| Monthly trend | What is the run-rate and seasonality? | Line + 3-month average | Month | Sales | Trend |
| Quarterly margin | Is margin improving? | Line + average line | Quarter | Margin | Stability check |
| Seasonality | Which months matter most? | Bar | Month | Share of annual sales | Planning |
| World map | Where are profit and losses? | Choropleth (tabs) | Country | Profit / Sales / Margin | Geography |
| Market bubble | Which markets are big vs profitable? | Scatter | Sales | Margin | Portfolio view |
| Loss countries | Which countries lose money? | Ranked bar | Profit | Country | Fix-or-exit list |
| Treemap | Which product families matter? | Treemap | - | Sales (size), Margin (colour) | Portfolio mix |
| Pareto | How concentrated are sales? | Cumulative line | Share of products | Share of sales | Range focus |
| Margin by discount | How does discount affect margin? | Bar | Discount band | Margin | Root cause |
| Country scatter | Do heavy discounters earn less? | Scatter + fit | Deep-discount share | Margin | Association test |
| Heatmap | Does the pattern hold in every market? | Heatmap | Discount band | Market | Robustness |
| Dumbbell | What would markets earn without deep discounts? | Dumbbell | Margin | Market | Upside (not a forecast) |
| Factor bars | Could ops or segment explain it? | Bar | Margin | Ship mode / priority / segment | Rule out alternatives |

All charts respond to the sidebar filters (year range, market, segment, category).

## 6. Insight framework

Every page ends with **Finding / Implication / Action**; the strategy page uses **Fact / Interpretation /
Recommendation**. Text is generated from the filtered data, so headlines change with the filters. Language is
associative ("is associated with", "consistent with") because the dataset has no experimental or cost data.

The strategy page presents a phased response: (1) eliminate discounts above 50% and add margin, deep-discount share
and discount exceptions to the monthly Board review; (2) pilot a 20% discount ceiling with approval for exceptions in
the two heaviest-discounting markets; (3) reprice the largest loss-making countries and products instead of exiting or
delisting; (4) scale the ceiling globally if the pilot retains at least 80% of volume, targeting a 15-18% margin.

## 7. Run locally

```bash
cd executive_dashboard
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501.

## 8. Deploy to Streamlit Community Cloud

1. Create a GitHub repository and push the contents of `executive_dashboard/` (keep `data/Global_Superstore2.csv`,
   about 12 MB, inside the repo; the app reads it with a relative path).
2. Go to https://share.streamlit.io, sign in with GitHub and click **Create app**.
3. Choose the repository and branch, set **Main file path** to `app.py` (or `executive_dashboard/app.py` if the
   folder is not the repo root) and pick Python 3.10+ under *Advanced settings*.
4. Click **Deploy**. `requirements.txt` and `.streamlit/config.toml` are picked up automatically.

Common issues: `ModuleNotFoundError` means a package is missing from `requirements.txt`; `FileNotFoundError` means
the CSV was not committed or the folder layout changed; a blank map usually means no internet access for map tiles.

## 9. Validation

The *Data and methodology* page runs 10 checks on every load: row reconciliation, duplicates, date logic, market
and discount-band totals adding up to company totals, margin consistency, CAGR reproducing end-year sales, discount
range, positive sales and finite line margins.
