"""Generate SIMULATED suppliers, purchase orders and inventory from real M5 sales."""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
Z = 1.0  # low safety factor on purpose -> some real stockouts
REVIEW_DAYS = 7
ANOMALY_SHARE = 0.05
PROC = Path("data/processed")


def make_suppliers(rng):
    n = 10
    return pd.DataFrame(
        {
            "supplier_id": [f"SUP_{i:02d}" for i in range(1, n + 1)],
            "name": [f"Supplier {i}" for i in range(1, n + 1)],
            "avg_lead_days": rng.integers(3, 15, n),
            "lead_std": np.round(rng.uniform(0.5, 3.0, n), 2),
            "reliability": np.round(rng.uniform(0.80, 0.99, n), 3),
            "moq": rng.choice([10, 20, 25, 50], n),
        }
    )


def make_sku_supplier(products, suppliers, rng):
    ids = suppliers["supplier_id"].to_numpy()
    rows = []
    for sku, price in zip(products["sku_id"], products["avg_price"]):
        primary = str(rng.choice(ids))
        cost = round(float(price) * rng.uniform(0.55, 0.75), 2)
        rows.append((sku, primary, True, cost))
        if rng.random() < 0.3:  # 30% of SKUs have a backup supplier
            second = str(rng.choice(ids[ids != primary]))
            rows.append((sku, second, False, round(cost * rng.uniform(1.0, 1.15), 2)))
    return pd.DataFrame(
        rows, columns=["sku_id", "supplier_id", "is_primary", "unit_cost"]
    )


def pick_anomalies(keys, n_days, rng):
    k = max(1, int(len(keys) * ANOMALY_SHARE))
    chosen = rng.choice(len(keys), k, replace=False)
    out = {}
    for i in chosen:
        kind = str(rng.choice(["supplier_outage", "over_order"]))
        start = int(rng.integers(60, n_days - 30))
        out[keys[i]] = (kind, start, start + 14)
    return out


def simulate(sales, primary, anomalies, dates, rng):
    n = len(dates)
    snaps, pos = [], []
    po_no = 0
    for (sku, loc), g in sales.groupby(["sku_id", "location_id"], sort=False):
        demand = g["units"].to_numpy()
        series = pd.Series(demand, dtype="float64")
        mu = (
            series.rolling(28, min_periods=1)
            .mean()
            .shift(1)
            .fillna(series.iloc[:7].mean())
            .to_numpy()
        )
        sd = series.rolling(28, min_periods=2).std().shift(1).fillna(0).to_numpy()

        sup = primary[sku]
        lead_avg = float(sup["avg_lead_days"])
        lead_std = float(sup["lead_std"])
        reliability = float(sup["reliability"])
        moq = int(sup["moq"])
        anomaly = anomalies.get((sku, loc))

        on_hand = int(np.ceil(max(mu[0], demand.mean()) * (lead_avg + REVIEW_DAYS)))
        on_order = 0
        arrivals = {}
        oh = np.zeros(n, dtype=int)
        oo = np.zeros(n, dtype=int)
        lost = np.zeros(n, dtype=int)

        for t in range(n):
            arrived = arrivals.pop(t, 0)
            on_hand += arrived
            on_order -= arrived
            sold = min(on_hand, int(demand[t]))
            lost[t] = int(demand[t]) - sold
            on_hand -= sold
            oh[t], oo[t] = on_hand, on_order

            reorder_point = mu[t] * lead_avg + Z * sd[t] * np.sqrt(lead_avg)
            target = reorder_point + mu[t] * REVIEW_DAYS
            position = on_hand + on_order
            if position <= reorder_point:
                qty = target - position
                qty = int(np.ceil(qty / moq) * moq) if qty > 0 else 0
                if qty > 0:
                    in_window = anomaly is not None and anomaly[1] <= t <= anomaly[2]
                    if in_window and anomaly[0] == "over_order":
                        qty *= 5
                    lead = max(1, round(rng.normal(lead_avg, lead_std)))
                    if rng.random() > reliability:
                        lead += int(rng.integers(2, 8))
                    if in_window and anomaly[0] == "supplier_outage":
                        lead *= 3
                    arrive = t + lead
                    arrivals[arrive] = arrivals.get(arrive, 0) + qty
                    on_order += qty
                    po_no += 1
                    pos.append(
                        (
                            f"PO_{po_no:06d}",
                            sku,
                            loc,
                            sup["supplier_id"],
                            dates[t],
                            dates[t] + pd.Timedelta(days=round(lead_avg)),
                            dates[arrive] if arrive < n else pd.NaT,
                            qty,
                        )
                    )

        snaps.append(
            pd.DataFrame(
                {
                    "sku_id": sku,
                    "location_id": loc,
                    "date": dates,
                    "on_hand": oh,
                    "on_order": oo,
                    "stockout": lost > 0,
                    "lost_units": lost,
                }
            )
        )
    po_cols = [
        "po_id",
        "sku_id",
        "location_id",
        "supplier_id",
        "order_date",
        "promised_date",
        "received_date",
        "qty",
    ]
    return pd.concat(snaps, ignore_index=True), pd.DataFrame(pos, columns=po_cols)


def main():
    rng = np.random.default_rng(SEED)
    products = pd.read_parquet(PROC / "products.parquet")
    sales = pd.read_parquet(PROC / "sales_daily.parquet").sort_values(
        ["sku_id", "location_id", "date"]
    )
    dates = pd.DatetimeIndex(sorted(sales["date"].unique()))

    suppliers = make_suppliers(rng)
    sku_supplier = make_sku_supplier(products, suppliers, rng)
    sup_by_id = suppliers.set_index("supplier_id")
    prim = sku_supplier[sku_supplier["is_primary"]].set_index("sku_id")
    primary = {
        sku: {
            **sup_by_id.loc[row["supplier_id"]].to_dict(),
            "supplier_id": row["supplier_id"],
        }
        for sku, row in prim.iterrows()
    }

    keys = list(
        sales[["sku_id", "location_id"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    anomalies = pick_anomalies(keys, len(dates), rng)

    inventory, pos = simulate(sales, primary, anomalies, dates, rng)
    injected = pd.DataFrame(
        [(s, l, k, dates[a], dates[b]) for (s, l), (k, a, b) in anomalies.items()],
        columns=["sku_id", "location_id", "type", "start_date", "end_date"],
    )

    suppliers.to_parquet(PROC / "suppliers.parquet", index=False)
    sku_supplier.to_parquet(PROC / "sku_supplier.parquet", index=False)
    inventory.to_parquet(PROC / "inventory_snapshots.parquet", index=False)
    pos.to_parquet(PROC / "purchase_orders.parquet", index=False)
    injected.to_parquet(PROC / "injected_anomalies.parquet", index=False)

    print("inventory rows:", len(inventory), "| purchase orders:", len(pos))
    print("stockout share of SKU-days: %.1f%%" % (100 * inventory["stockout"].mean()))
    print("injected anomalies:", len(injected))


if __name__ == "__main__":
    main()
