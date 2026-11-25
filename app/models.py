import datetime as dt

from sqlalchemy import Boolean, Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Product(Base):
    __tablename__ = "products"
    sku_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    category: Mapped[str] = mapped_column(String(32))
    dept: Mapped[str] = mapped_column(String(32))
    avg_price: Mapped[float] = mapped_column(Float)


class Location(Base):
    __tablename__ = "locations"
    location_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    avg_lead_days: Mapped[int] = mapped_column(Integer)
    lead_std: Mapped[float] = mapped_column(Float)
    reliability: Mapped[float] = mapped_column(Float)
    moq: Mapped[int] = mapped_column(Integer)


class SkuSupplier(Base):
    __tablename__ = "sku_supplier"
    sku_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    unit_cost: Mapped[float] = mapped_column(Float)


class SalesDaily(Base):
    __tablename__ = "sales_daily"
    sku_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    units: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    snap: Mapped[int] = mapped_column(Integer)
    is_event: Mapped[int] = mapped_column(Integer)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"
    sku_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    on_hand: Mapped[int] = mapped_column(Integer)
    on_order: Mapped[int] = mapped_column(Integer)
    stockout: Mapped[bool] = mapped_column(Boolean)
    lost_units: Mapped[int] = mapped_column(Integer)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    sku_id: Mapped[str] = mapped_column(String(32))
    location_id: Mapped[str] = mapped_column(String(16))
    supplier_id: Mapped[str] = mapped_column(String(16))
    order_date: Mapped[dt.date] = mapped_column(Date)
    promised_date: Mapped[dt.date] = mapped_column(Date)
    received_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    qty: Mapped[int] = mapped_column(Integer)


class InjectedAnomaly(Base):
    __tablename__ = "injected_anomalies"
    sku_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date] = mapped_column(Date)
