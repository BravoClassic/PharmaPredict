"""Inventory application services for the first vertical slice."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from .dto import EligibleBatch, MovementResult
from .repositories import InventoryRepository


class InsufficientStockError(ValueError):
    pass


class InventoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = InventoryRepository(session)

    def fefo_batches(self, pharmacy_id: str, medication_id: str) -> list[EligibleBatch]:
        return self.repo.eligible_batches(pharmacy_id, medication_id)

    def dispense(
        self,
        *,
        pharmacy_id: str,
        medication_id: str,
        quantity: int,
        rx_number: str,
        employee_id: str,
        at: datetime | None = None,
    ) -> list[MovementResult]:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if not rx_number.strip():
            raise ValueError("rx_number is required")

        # The synthetic fixture is historical. When no explicit event time is supplied,
        # use the fixture reference clock instead of the computer's wall-clock date.
        at = at or self.repo.reference_timestamp()
        candidates = self.repo.eligible_batches(pharmacy_id, medication_id)
        available = sum(b.quantity_on_hand for b in candidates)
        if available < quantity:
            raise InsufficientStockError(f"requested {quantity}, available {available}")

        remaining = quantity
        results: list[MovementResult] = []

        for candidate in candidates:
            if remaining <= 0:
                break

            current = self.repo.batch_balance_for_update(candidate.batch_id)
            if current <= 0:
                continue

            take = min(current, remaining)
            transaction_id = "TX" + uuid4().hex[:12].upper()
            self.session.execute(
                text(
                    """
                    INSERT INTO InventoryTransaction
                      (TransactionID,BatchID,TransactionType,QuantityChange,
                       TransactionTimestamp,ReceiptItemID,RxNumber,EmployeeID)
                    VALUES
                      (:transaction_id,:batch_id,'DISPENSE',:quantity_change,
                       :transaction_timestamp,NULL,:rx_number,:employee_id)
                    """
                ),
                {
                    "transaction_id": transaction_id,
                    "batch_id": candidate.batch_id,
                    "quantity_change": -take,
                    "transaction_timestamp": at,
                    "rx_number": rx_number,
                    "employee_id": employee_id,
                },
            )
            resulting = current - take
            results.append(
                MovementResult(
                    transaction_id=transaction_id,
                    batch_id=candidate.batch_id,
                    quantity_change=-take,
                    resulting_balance=resulting,
                )
            )
            remaining -= take

        if remaining:
            # Defensive guard for concurrent stock changes. Caller transaction will roll back.
            raise InsufficientStockError("stock changed while dispensing; retry the operation")

        return results
