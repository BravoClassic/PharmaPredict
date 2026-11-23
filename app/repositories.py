"""Read repositories for inventory and medication data."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from .dto import EligibleBatch, InventorySummary


class InventoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def reference_timestamp(self) -> datetime:
        value = self.session.scalar(text("SELECT AsOfTimestamp FROM vw_reference_clock"))
        if value is None:
            raise RuntimeError("database reference clock is unavailable")
        return value

    def inventory_summary(self, pharmacy_id: str) -> list[InventorySummary]:
        rows = self.session.execute(
            text(
                """
                SELECT PharmacyID, MedicationID, DisplayName, ReorderPoint,
                       QuantityOnHand, InventoryValue, EarliestActiveExpiration
                FROM vw_inventory_summary
                WHERE PharmacyID = :pharmacy_id
                ORDER BY DisplayName
                """
            ),
            {"pharmacy_id": pharmacy_id},
        ).mappings()
        return [
            InventorySummary(
                pharmacy_id=r["PharmacyID"],
                medication_id=r["MedicationID"],
                display_name=r["DisplayName"],
                reorder_point=int(r["ReorderPoint"]),
                quantity_on_hand=int(r["QuantityOnHand"]),
                inventory_value=Decimal(r["InventoryValue"] or 0),
                earliest_active_expiration=r["EarliestActiveExpiration"],
            )
            for r in rows
        ]

    def eligible_batches(self, pharmacy_id: str, medication_id: str) -> list[EligibleBatch]:
        rows = self.session.execute(
            text(
                """
                SELECT BatchID, PharmacyID, MedicationID, LotNumber, ExpirationDate, QuantityOnHand
                FROM vw_fefo_eligible
                WHERE PharmacyID = :pharmacy_id
                  AND MedicationID = :medication_id
                ORDER BY ExpirationDate, BatchID
                """
            ),
            {"pharmacy_id": pharmacy_id, "medication_id": medication_id},
        ).mappings()
        return [
            EligibleBatch(
                batch_id=r["BatchID"],
                pharmacy_id=r["PharmacyID"],
                medication_id=r["MedicationID"],
                lot_number=r["LotNumber"],
                expiration_date=r["ExpirationDate"],
                quantity_on_hand=int(r["QuantityOnHand"]),
            )
            for r in rows
        ]

    def batch_balance_for_update(self, batch_id: str) -> int:
        # Lock the physical batch row, then compute the signed balance in the same transaction.
        self.session.execute(
            text("SELECT BatchID FROM InventoryBatch WHERE BatchID=:batch_id FOR UPDATE"),
            {"batch_id": batch_id},
        ).one()
        return int(
            self.session.scalar(
                text(
                    """SELECT COALESCE(SUM(QuantityChange),0)
                       FROM InventoryTransaction
                       WHERE BatchID=:batch_id"""
                ),
                {"batch_id": batch_id},
            )
            or 0
        )
