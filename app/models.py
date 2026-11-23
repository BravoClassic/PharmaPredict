"""Minimal SQLAlchemy mappings used by the service layer.

These intentionally cover the core vertical slice first. Additional tables can be
mapped incrementally as workflows are implemented.
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Medication(Base):
    __tablename__ = "Medication"

    medication_id: Mapped[str] = mapped_column("MedicationID", String(10), primary_key=True)
    display_name: Mapped[str] = mapped_column("DisplayName", String(140), nullable=False)
    package_size: Mapped[int] = mapped_column("PackageSize", Integer, nullable=False)


class InventoryBatch(Base):
    __tablename__ = "InventoryBatch"

    batch_id: Mapped[str] = mapped_column("BatchID", String(12), primary_key=True)
    medication_id: Mapped[str] = mapped_column("MedicationID", ForeignKey("Medication.MedicationID"), nullable=False)
    pharmacy_id: Mapped[str] = mapped_column("PharmacyID", String(10), nullable=False)
    lot_number: Mapped[str] = mapped_column("LotNumber", String(40), nullable=False)
    expiration_date: Mapped[date] = mapped_column("ExpirationDate", Date, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column("UnitCost", Numeric(12,4), nullable=False)


class InventoryTransaction(Base):
    __tablename__ = "InventoryTransaction"

    transaction_id: Mapped[str] = mapped_column("TransactionID", String(14), primary_key=True)
    batch_id: Mapped[str] = mapped_column("BatchID", ForeignKey("InventoryBatch.BatchID"), nullable=False)
    transaction_type: Mapped[str] = mapped_column("TransactionType", String(30), nullable=False)
    quantity_change: Mapped[int] = mapped_column("QuantityChange", Integer, nullable=False)
    transaction_timestamp: Mapped[datetime] = mapped_column("TransactionTimestamp", DateTime, nullable=False)
    receipt_item_id: Mapped[str | None] = mapped_column("ReceiptItemID", String(14), nullable=True)
    rx_number: Mapped[str | None] = mapped_column("RxNumber", String(30), nullable=True)
    employee_id: Mapped[str] = mapped_column("EmployeeID", String(10), nullable=False)
