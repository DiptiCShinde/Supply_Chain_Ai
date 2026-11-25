from pathlib import Path

import pandas as pd
import pytest

PROC = Path("data/processed")


def load(name):
    path = PROC / f"{name}.parquet"
    if not path.exists():
        pytest.skip("processed data not found; run the scripts first")
    return pd.read_parquet(path)


def test_sales_values_valid():
    s = load("sales_daily")
    assert (s["units"] >= 0).all()
    assert s["price"].notna().all()


def test_sales_no_duplicates():
    s = load("sales_daily")
    assert not s.duplicated(["sku_id", "location_id", "date"]).any()


def test_sales_no_date_gaps():
    s = load("sales_daily")
    g = s.groupby(["sku_id", "location_id"])["date"]
    span = (g.max() - g.min()).dt.days + 1
    assert (span == g.count()).all()


def test_inventory_non_negative():
    inv = load("inventory_snapshots")
    assert (inv["on_hand"] >= 0).all()
    assert (inv["on_order"] >= 0).all()


def test_purchase_order_dates():
    po = load("purchase_orders")
    received = po.dropna(subset=["received_date"])
    assert (received["received_date"] >= received["order_date"]).all()
