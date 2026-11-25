# Dataset Documentation

## 1. Real Data
The demand and pricing history comes from the **M5 Forecasting Accuracy** dataset ([Zenodo CC BY 4.0 copy](https://zenodo.org/records/12636070) / Kaggle Walmart M5).
- **Subset used:** Two California stores (`CA_1` and `CA_2`), ~200 SKUs sampled evenly across all three product categories (`FOODS`, `HOBBIES`, `HOUSEHOLD`) to capture both fast and slow movers, over the last **730 days**.

## 2. Simulated Data
M5 sales are treated as true customer demand to simulate daily inventory, suppliers, and purchase orders (`SEED = 42`):
- **Suppliers & Sourcing:** 10 synthetic suppliers with varying lead times, standard deviations, reliability scores, and Minimum Order Quantities (MOQs). 30% of SKUs include a secondary backup supplier.
- **Replenishment Policy:** Weekly review (`REVIEW_DAYS = 7`) order-up-to policy using a 28-day rolling demand mean/std and safety factor `Z = 1.0` (calibrated to produce realistic stockouts).
- **Injected Anomalies:** 5% of SKU-location pairs contain a 14-day injected `supplier_outage` (3x lead time) or `over_order` (5x order quantity) as ground truth for downstream anomaly detection.

## 3. Why Simulate
Public retail datasets provide point-of-sale transactions, prices, and calendar events, but do not contain internal ERP records such as daily on-hand stock, open purchase orders, or supplier lead-time disruptions.

## 4. Limits
Demand patterns, seasonality, and price elasticity reflect real retail data, while stockout rates, holding costs, and supplier risk evaluations reflect the simulated replenishment rules rather than a live company's operations.