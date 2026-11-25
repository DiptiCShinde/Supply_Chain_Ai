"""Load processed parquet files into the database (full reload via Postgres COPY)."""

import csv
import io
import sys
from pathlib import Path

import pandas as pd

import app.models  # noqa: F401  (registers tables)
from app.config import settings
from app.db import Base, engine

PROC = Path("data/processed")
TABLES = [
    "products",
    "locations",
    "suppliers",
    "sku_supplier",
    "sales_daily",
    "inventory_snapshots",
    "purchase_orders",
    "injected_anomalies",
]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes("datetime64").columns:
        as_date = df[col].dt.date
        df[col] = as_date.where(df[col].notna(), None)
    return df


def copy_table(name: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="\\N", quoting=csv.QUOTE_MINIMAL)
    buf.seek(0)

    cols = ", ".join(df.columns)
    sql = f"COPY {name} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '\\N')"

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur, cur.copy(sql) as copy:
            while data := buf.read(65536):
                copy.write(data)
        raw_conn.commit()
    finally:
        raw_conn.close()


def main():
    if engine is None:
        sys.exit("DATABASE_URL is empty. Fill .env.dev first.")
    if settings.app_env == "prod" and "--force" not in sys.argv:
        sys.exit("Refusing to reset a prod database without --force.")

    print("Resetting tables...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()

    for name in TABLES:
        df = prepare(pd.read_parquet(PROC / f"{name}.parquet"))
        copy_table(name, df)
        print(f"loaded {name}: {len(df)} rows")


if __name__ == "__main__":
    main()
