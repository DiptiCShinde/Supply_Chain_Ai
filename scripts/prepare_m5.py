"""Prepare a small M5 subset: 2 CA stores, ~200 SKUs, last 730 days."""

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/m5")
OUT = Path("data/processed")
SAMPLE = Path("data/sample")
STORES = ["CA_1", "CA_2"]
DAYS = 730
ITEMS_PER_CATEGORY = 67


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SAMPLE.mkdir(parents=True, exist_ok=True)

    calendar = pd.read_csv(RAW / "calendar.csv", parse_dates=["date"])

    sales_path = RAW / "sales_train_evaluation.csv"
    if not sales_path.exists():
        sales_path = RAW / "sales_train_validation.csv"
    header = pd.read_csv(sales_path, nrows=0).columns
    id_cols = ["item_id", "dept_id", "cat_id", "store_id"]
    d_cols = [c for c in header if c.startswith("d_")][-DAYS:]
    sales = pd.read_csv(
        sales_path, usecols=id_cols + d_cols, dtype={c: "int16" for c in d_cols}
    )
    sales = sales[sales["store_id"].isin(STORES)]

    # choose a spread of fast and slow items in each category
    total = sales.copy()
    total["total"] = total[d_cols].sum(axis=1).astype("int64")
    total = total.groupby(["item_id", "dept_id", "cat_id"], as_index=False)[
        "total"
    ].sum()
    total = total[total["total"] >= 200]
    picked = []
    for _, grp in total.groupby("cat_id"):
        grp = grp.sort_values("total", ascending=False).reset_index(drop=True)
        idx = np.linspace(0, len(grp) - 1, min(ITEMS_PER_CATEGORY, len(grp)))
        picked.append(grp.iloc[np.unique(idx.round().astype(int))])
    picked = pd.concat(picked)
    items = set(picked["item_id"])
    sales = sales[sales["item_id"].isin(items)]

    prices = pd.read_csv(RAW / "sell_prices.csv")
    prices = prices[prices["store_id"].isin(STORES) & prices["item_id"].isin(items)]

    # wide -> long
    long = sales.melt(
        id_vars=id_cols, value_vars=d_cols, var_name="d", value_name="units"
    )
    cal = calendar[["d", "date", "wm_yr_wk", "event_name_1", "snap_CA"]].copy()
    cal["is_event"] = cal["event_name_1"].notna().astype("int8")
    cal = cal.rename(columns={"snap_CA": "snap"})
    long = long.merge(
        cal[["d", "date", "wm_yr_wk", "is_event", "snap"]], on="d", how="left"
    )
    long = long.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")
    long = long.sort_values(["item_id", "store_id", "date"])
    long["sell_price"] = long.groupby(["item_id", "store_id"])["sell_price"].transform(
        lambda s: s.ffill().bfill()
    )
    long["sell_price"] = long["sell_price"].fillna(long["sell_price"].median())

    sales_daily = long.rename(
        columns={"item_id": "sku_id", "store_id": "location_id", "sell_price": "price"}
    )[["sku_id", "location_id", "date", "units", "price", "snap", "is_event"]]
    sales_daily["units"] = sales_daily["units"].astype("int32")

    avg_price = (
        sales_daily.groupby("sku_id", as_index=False)["price"]
        .mean()
        .rename(columns={"price": "avg_price"})
    )
    products = (
        picked[["item_id", "cat_id", "dept_id"]]
        .rename(columns={"item_id": "sku_id", "cat_id": "category", "dept_id": "dept"})
        .merge(avg_price, on="sku_id")
    )
    locations = pd.DataFrame({"location_id": STORES, "name": STORES})

    products.to_parquet(OUT / "products.parquet", index=False)
    locations.to_parquet(OUT / "locations.parquet", index=False)
    sales_daily.to_parquet(OUT / "sales_daily.parquet", index=False)

    # tiny sample that is safe to commit
    skus = products["sku_id"].head(50)
    last = sales_daily["date"].max() - pd.Timedelta(days=180)
    sample = sales_daily[
        sales_daily["sku_id"].isin(skus) & (sales_daily["date"] > last)
    ]
    sample.to_csv(SAMPLE / "sales_daily_sample.csv", index=False)

    print("products:", len(products), "| sales rows:", len(sales_daily))
    print(
        "date range:",
        sales_daily["date"].min().date(),
        "to",
        sales_daily["date"].max().date(),
    )


if __name__ == "__main__":
    main()
