"""KPI calculations, aggregations, formatting and validation checks."""

import numpy as np
import pandas as pd

from utils.data_loader import DEEP_DISCOUNT, DISCOUNT_LABELS

# ---------------------------------------------------------------- formatting


def _finite(x) -> bool:
    try:
        return x is not None and np.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def fmt_money(x, decimals: int = 1) -> str:
    if not _finite(x):
        return "n/a"
    x = float(x)
    sign = "-" if x < 0 else ""
    a = abs(x)
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return "%s$%.*f%s" % (sign, decimals, a / div, suffix)
    return "%s$%s" % (sign, "{:,.0f}".format(a))


def fmt_pct(x, decimals: int = 1, signed: bool = False) -> str:
    if not _finite(x):
        return "n/a"
    return ("%+.*f%%" if signed else "%.*f%%") % (decimals, float(x) * 100)


def fmt_pp(x, decimals: int = 1) -> str:
    if not _finite(x):
        return "n/a"
    return "%+.*f pp" % (decimals, float(x) * 100)


def fmt_int(x) -> str:
    if not _finite(x):
        return "n/a"
    return "{:,.0f}".format(float(x))


# ---------------------------------------------------------------- safe math


def safe_div(num, den) -> float:
    if not _finite(num) or not _finite(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def safe_div_series(num: pd.Series, den: pd.Series) -> pd.Series:
    out = num / den.where(den != 0)
    return out.replace([np.inf, -np.inf], np.nan)


def calculate_growth(current, previous) -> float:
    """(Current - Previous) / |Previous|; NaN when previous is 0 or missing."""
    if not _finite(current) or not _finite(previous) or float(previous) == 0:
        return np.nan
    return (float(current) - float(previous)) / abs(float(previous))


def growth_series(s: pd.Series) -> pd.Series:
    prev = s.shift(1)
    return safe_div_series(s - prev, prev.abs())


def calculate_cagr(begin, end, periods) -> float:
    """CAGR = (End / Begin) ** (1 / periods) - 1; needs positive values and periods >= 1."""
    if not _finite(begin) or not _finite(end) or not _finite(periods):
        return np.nan
    if periods < 1 or begin <= 0 or end <= 0:
        return np.nan
    return (float(end) / float(begin)) ** (1.0 / float(periods)) - 1.0


def correlation(a: pd.Series, b: pd.Series) -> float:
    pair = pd.concat([a, b], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].std() == 0 or pair.iloc[:, 1].std() == 0:
        return np.nan
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))


def strength(r: float) -> str:
    if not _finite(r):
        return "no measurable"
    a = abs(r)
    word = "very strong" if a >= 0.8 else "strong" if a >= 0.6 else "moderate" if a >= 0.4 else "weak"
    return word + (" negative" if r < 0 else " positive")


# ---------------------------------------------------------------- summaries


def summarize(df: pd.DataFrame) -> dict:
    sales = float(df["Sales"].sum())
    profit = float(df["Profit"].sum())
    orders = int(df["Order Key"].nunique())
    deep = df["Deep Discount"]
    deep_sales = float(df.loc[deep, "Sales"].sum())
    deep_profit = float(df.loc[deep, "Profit"].sum())
    rest_sales = sales - deep_sales
    rest_profit = profit - deep_profit
    n = len(df)
    return {
        "sales": sales,
        "profit": profit,
        "margin": safe_div(profit, sales),
        "orders": orders,
        "aov": safe_div(sales, orders),
        "lines": n,
        "quantity": float(df["Quantity"].sum()),
        "avg_discount": float(df["Discount"].mean()) if n else np.nan,
        "deep_share": float(deep.mean()) if n else np.nan,
        "deep_sales": deep_sales,
        "deep_profit": deep_profit,
        "deep_margin": safe_div(deep_profit, deep_sales),
        "rest_sales": rest_sales,
        "rest_profit": rest_profit,
        "rest_margin": safe_div(rest_profit, rest_sales),
        "loss_line_share": float(df["Is Loss"].mean()) if n else np.nan,
    }


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Year", "Sales", "Profit", "Orders", "Margin", "AOV"])
    work = df.assign(_deep_profit=df["Profit"].where(df["Deep Discount"], 0.0))
    g = work.groupby("Year").agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum"),
        Orders=("Order Key", "nunique"), Lines=("Sales", "size"),
        DeepProfit=("_deep_profit", "sum"),
        DeepShare=("Deep Discount", "mean"),
    )
    g = g.reindex(range(int(g.index.min()), int(g.index.max()) + 1))
    g[["Sales", "Profit", "Orders", "Lines", "DeepProfit"]] = g[["Sales", "Profit", "Orders", "Lines", "DeepProfit"]].fillna(0)
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"])
    g["AOV"] = safe_div_series(g["Sales"], g["Orders"])
    g["Sales YoY"] = growth_series(g["Sales"])
    g["Profit YoY"] = growth_series(g["Profit"])
    g["Margin change"] = g["Margin"].diff()
    g.index.name = "Year"
    return g.reset_index()


def period_summary(df: pd.DataFrame, freq_col: str) -> pd.DataFrame:
    g = df.groupby(freq_col).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).sort_index()
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"])
    return g.reset_index()


def seasonality_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Average share of each year's sales that falls in each calendar month."""
    m = df.groupby(["Year", "Month Num"])["Sales"].sum().reset_index()
    m["Share"] = safe_div_series(m["Sales"], m.groupby("Year")["Sales"].transform("sum"))
    prof = m.groupby("Month Num")["Share"].mean().reindex(range(1, 13))
    out = prof.reset_index()
    out["Month"] = pd.to_datetime(out["Month Num"], format="%m").dt.strftime("%b")
    return out


def group_summary(df: pd.DataFrame, by) -> pd.DataFrame:
    g = df.groupby(by, observed=True).agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum"),
        Orders=("Order Key", "nunique"), Lines=("Sales", "size"),
        AvgDiscount=("Discount", "mean"), DeepShare=("Deep Discount", "mean"),
    )
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"])
    g["Sales share"] = safe_div_series(g["Sales"], pd.Series(g["Sales"].sum(), index=g.index))
    g["Profit share"] = safe_div_series(g["Profit"], pd.Series(g["Profit"].sum(), index=g.index))
    return g.reset_index()


def shipping_summary(df: pd.DataFrame, by) -> pd.DataFrame:
    """Freight burden by dimension. Shipping Cost is reported per line, but the data does not
    say whether Profit already nets it off, so burden is expressed as a share of Sales - a ratio
    of two observed columns that needs no assumption about how Profit was built."""
    g = df.groupby(by, observed=True).agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum"),
        ShipCost=("Shipping Cost", "sum"), Lines=("Sales", "size"),
    )
    g["ShipBurden"] = safe_div_series(g["ShipCost"], g["Sales"])
    g["ShipPerLine"] = safe_div_series(g["ShipCost"], g["Lines"])
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"])
    g["Line share"] = safe_div_series(g["Lines"], pd.Series(g["Lines"].sum(), index=g.index))
    return g.reset_index()


def discount_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("Discount Band", observed=False).agg(
        Lines=("Sales", "size"), Sales=("Sales", "sum"), Profit=("Profit", "sum"),
        LossShare=("Is Loss", "mean"),
    ).reindex(DISCOUNT_LABELS)
    g[["Lines", "Sales", "Profit"]] = g[["Lines", "Sales", "Profit"]].fillna(0)
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"])
    g["Line share"] = safe_div_series(g["Lines"], pd.Series(g["Lines"].sum(), index=g.index))
    g.index.name = "Band"
    return g.reset_index()


def market_band_matrix(df: pd.DataFrame, min_lines: int = 30) -> pd.DataFrame:
    g = df.groupby(["Market", "Discount Band"], observed=False).agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum"), Lines=("Sales", "size"))
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"]).where(g["Lines"] >= min_lines)
    mat = g["Margin"].unstack("Discount Band").reindex(columns=DISCOUNT_LABELS)
    order = group_summary(df, "Market").set_index("Market")["Margin"].sort_values().index
    return mat.reindex(order)


def market_margin_split(df: pd.DataFrame) -> pd.DataFrame:
    """Overall margin vs margin on lines discounted at or below the deep-discount threshold."""
    allm = group_summary(df, "Market").set_index("Market")
    rest = group_summary(df[~df["Deep Discount"]], "Market").set_index("Market")
    out = pd.DataFrame({
        "Overall": allm["Margin"],
        "Excluding deep discounts": rest["Margin"].reindex(allm.index),
        "Deep share": allm["DeepShare"],
    }).sort_values("Overall")
    return out.reset_index()


def country_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per country; a few countries appear in two markets, so Market = the dominant one by sales."""
    g = group_summary(df, "Country")
    main_market = (df.groupby(["Country", "Market"])["Sales"].sum().reset_index()
                   .sort_values("Sales", ascending=False).drop_duplicates("Country")
                   .set_index("Country")["Market"])
    g.insert(1, "Market", g["Country"].map(main_market))
    return g.sort_values("Profit")


def pareto_table(df: pd.DataFrame, by: str = "Product Name", value: str = "Sales") -> pd.DataFrame:
    s = df.groupby(by)[value].sum().sort_values(ascending=False)
    s = s[s > 0]
    out = s.reset_index()
    out["Cum share"] = safe_div_series(out[value].cumsum(), pd.Series(s.sum(), index=out.index))
    out["Item share"] = (np.arange(1, len(out) + 1)) / max(len(out), 1)
    return out


def items_for_share(pareto: pd.DataFrame, share: float = 0.8):
    if pareto.empty:
        return np.nan, np.nan
    n = int((pareto["Cum share"] < share).sum()) + 1
    n = min(n, len(pareto))
    return n, n / len(pareto)


def loss_products(df: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    g = df.groupby(["Product Name", "Category", "Sub-Category"]).agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum"),
        AvgDiscount=("Discount", "mean"), Lines=("Sales", "size")).reset_index()
    g["Margin"] = safe_div_series(g["Profit"], g["Sales"])
    return g[g["Profit"] < 0].sort_values("Profit").head(top)


# ---------------------------------------------------------------- KPI cards


def calculate_kpis(fd) -> list:
    """Latest selected year vs the year before (dimension filters applied, year filter relaxed)."""
    cur_df = fd.dims[fd.dims["Year"] == fd.end]
    prev_df = fd.dims[fd.dims["Year"] == fd.end - 1]
    cur = summarize(cur_df)
    prev = summarize(prev_df) if not prev_df.empty else None
    trend = yearly_summary(fd.df)

    def delta(key, kind="growth"):
        if prev is None:
            return None
        if kind == "pp":
            d = cur[key] - prev[key] if _finite(cur[key]) and _finite(prev[key]) else np.nan
            return None if not _finite(d) else fmt_pp(d) + " vs %d" % (fd.end - 1)
        g = calculate_growth(cur[key], prev[key])
        return None if not _finite(g) else fmt_pct(g, signed=True) + " vs %d" % (fd.end - 1)

    def spark(col, transform=None):
        if len(trend) < 2:
            return None
        vals = trend[col].fillna(0)
        if transform is not None:
            vals = transform(vals)
        return [float(v) for v in vals]

    deep_loss = -cur["deep_profit"]
    prev_loss = -prev["deep_profit"] if prev is not None else np.nan
    loss_delta = None
    if prev is not None:
        g = calculate_growth(deep_loss, prev_loss)
        loss_delta = None if not _finite(g) else fmt_pct(g, signed=True) + " vs %d" % (fd.end - 1)

    return [
        dict(label="Sales", value=fmt_money(cur["sales"], 2), delta=delta("sales"),
             spark=spark("Sales"), color="normal",
             help="Sum of Sales for %d." % fd.end),
        dict(label="Profit", value=fmt_money(cur["profit"], 2), delta=delta("profit"),
             spark=spark("Profit"), color="normal",
             help="Sum of Profit for %d." % fd.end),
        dict(label="Profit margin", value=fmt_pct(cur["margin"]), delta=delta("margin", "pp"),
             spark=spark("Margin"), color="normal",
             help="Profit / Sales. Delta in percentage points."),
        dict(label="Orders", value=fmt_int(cur["orders"]), delta=delta("orders"),
             spark=spark("Orders"), color="normal",
             help="Distinct Order ID + Order Date combinations."),
        dict(label="Avg order value", value=fmt_money(cur["aov"], 0), delta=delta("aov"),
             spark=spark("AOV"), color="normal",
             help="Sales / Orders."),
        dict(label="Deep-discount losses", value=fmt_money(deep_loss, 0), delta=loss_delta,
             spark=spark("DeepProfit", lambda v: -v), color="inverse",
             help="Net profit given away on lines discounted above %d%%. Rising is bad." % int(DEEP_DISCOUNT * 100)),
    ]


# ---------------------------------------------------------------- narrative helpers


def growth_headline(yearly: pd.DataFrame) -> str:
    if yearly.empty:
        return "No data for the current selection"
    if len(yearly) < 2:
        r = yearly.iloc[0]
        return "%d: %s in sales at a %s profit margin" % (r["Year"], fmt_money(r["Sales"]), fmt_pct(r["Margin"]))
    first, last = yearly.iloc[0], yearly.iloc[-1]
    cagr = calculate_cagr(first["Sales"], last["Sales"], len(yearly) - 1)
    dm = last["Margin"] - first["Margin"] if _finite(last["Margin"]) and _finite(first["Margin"]) else np.nan
    if not _finite(cagr):
        return "Sales moved from %s to %s" % (fmt_money(first["Sales"]), fmt_money(last["Sales"]))
    if cagr < 0:
        return "Sales shrank %s a year to %s" % (fmt_pct(abs(cagr)), fmt_money(last["Sales"]))
    if _finite(dm) and abs(dm) < 0.015:
        return "Sales grew %s a year, but profit margin has barely moved (%s to %s)" % (
            fmt_pct(cagr), fmt_pct(first["Margin"]), fmt_pct(last["Margin"]))
    if _finite(dm) and dm > 0:
        return "Sales grew %s a year and profit margin improved %s" % (fmt_pct(cagr), fmt_pp(dm))
    return "Sales grew %s a year while profit margin fell %s" % (fmt_pct(cagr), fmt_pp(abs(dm)).lstrip("+"))


def deep_discount_sentence(tot: dict) -> str:
    if tot["lines"] == 0 or not _finite(tot["deep_share"]) or tot["deep_share"] == 0:
        return "No order lines in this selection were discounted above %d%%." % int(DEEP_DISCOUNT * 100)
    verb = "lost" if tot["deep_profit"] < 0 else "earned"
    return ("Lines discounted above %d%% were %s of all lines and %s %s; every other line earned %s at a %s margin."
            % (int(DEEP_DISCOUNT * 100), fmt_pct(tot["deep_share"]), verb, fmt_money(abs(tot["deep_profit"])),
               fmt_money(tot["rest_profit"]), fmt_pct(tot["rest_margin"])))


# ---------------------------------------------------------------- validation


def run_validation_checks(df: pd.DataFrame, report: dict) -> pd.DataFrame:
    checks = []

    def add(name, ok, detail):
        checks.append({"Check": name, "Result": detail, "Status": "Pass" if ok else "Review"})

    tot = summarize(df)
    add("Row count reconciles", report["raw_rows"] == report["clean_rows"] + report["dropped_rows"],
        "%s raw = %s clean + %s dropped" % (fmt_int(report["raw_rows"]), fmt_int(report["clean_rows"]), fmt_int(report["dropped_rows"])))
    add("No duplicate order lines", report["duplicate_rows"] == 0 and report["duplicate_row_ids"] == 0,
        "%d duplicate rows, %d duplicate Row IDs" % (report["duplicate_rows"], report["duplicate_row_ids"]))
    add("Dates parse and ship after order", report["invalid_dates"] == 0 and report["ship_before_order"] == 0,
        "%d unparseable dates, %d ship-before-order lines" % (report["invalid_dates"], report["ship_before_order"]))
    mk = df.groupby("Market")["Sales"].sum().sum()
    add("Market sales add up to total", abs(mk - tot["sales"]) < 0.01, "%s vs %s" % (fmt_money(mk, 3), fmt_money(tot["sales"], 3)))
    bp = discount_band_summary(df)["Profit"].sum()
    add("Discount-band profit adds up to total", abs(bp - tot["profit"]) < 0.01, "%s vs %s" % (fmt_money(bp, 3), fmt_money(tot["profit"], 3)))
    y = yearly_summary(df)
    w = safe_div((y["Margin"] * y["Sales"]).sum(), y["Sales"].sum())
    add("Margin = total profit / total sales", _finite(w) and abs(w - tot["margin"]) < 1e-9,
        "Sales-weighted yearly margin %s = overall %s" % (fmt_pct(w, 3), fmt_pct(tot["margin"], 3)))
    if len(y) >= 2:
        c = calculate_cagr(y["Sales"].iloc[0], y["Sales"].iloc[-1], len(y) - 1)
        rebuilt = y["Sales"].iloc[0] * (1 + c) ** (len(y) - 1)
        add("CAGR reproduces end-year sales", abs(rebuilt - y["Sales"].iloc[-1]) < 0.01,
            "%s x (1 + %s)^%d = %s" % (fmt_money(y["Sales"].iloc[0]), fmt_pct(c, 2), len(y) - 1, fmt_money(rebuilt)))
    add("Discounts within 0-100%", bool(df["Discount"].between(0, 1).all()),
        "Range %s to %s" % (fmt_pct(df["Discount"].min(), 0), fmt_pct(df["Discount"].max(), 0)))
    add("Sales strictly positive", bool((df["Sales"] > 0).all()), "Minimum line sale %s" % fmt_money(df["Sales"].min(), 2))
    add("No infinite or missing margins", bool(np.isfinite(df["Line Margin"]).all()),
        "%d invalid line margins" % int((~np.isfinite(df["Line Margin"])).sum()))
    return pd.DataFrame(checks)
