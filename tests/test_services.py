from __future__ import annotations

from datetime import date

import pytest

from app.dto import EligibleBatch
from app.services import InsufficientStockError, InventoryService


class FakeRepo:
    def __init__(self):
        self.balances = {"B1": 5, "B2": 7}

    def eligible_batches(self, pharmacy_id: str, medication_id: str):
        return [
            EligibleBatch("B1", pharmacy_id, medication_id, "LOT1", date(2027,1,1), 5),
            EligibleBatch("B2", pharmacy_id, medication_id, "LOT2", date(2027,2,1), 7),
        ]

    def batch_balance_for_update(self, batch_id: str) -> int:
        return self.balances[batch_id]


class FakeSession:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((str(sql), params))


def build_service():
    session = FakeSession()
    service = InventoryService(session)  # type: ignore[arg-type]
    service.repo = FakeRepo()  # type: ignore[assignment]
    return service, session


def test_dispense_uses_fefo_and_splits_across_batches():
    service, session = build_service()
    result = service.dispense(
        pharmacy_id="LOC001", medication_id="MED001", quantity=8,
        rx_number="RX100", employee_id="EMP003"
    )
    assert [r.batch_id for r in result] == ["B1", "B2"]
    assert [r.quantity_change for r in result] == [-5, -3]
    assert len(session.executed) == 2


def test_dispense_rejects_insufficient_stock_before_writes():
    service, session = build_service()
    with pytest.raises(InsufficientStockError):
        service.dispense(
            pharmacy_id="LOC001", medication_id="MED001", quantity=13,
            rx_number="RX100", employee_id="EMP003"
        )
    assert session.executed == []


def test_dispense_requires_positive_quantity():
    service, _ = build_service()
    with pytest.raises(ValueError):
        service.dispense(
            pharmacy_id="LOC001", medication_id="MED001", quantity=0,
            rx_number="RX100", employee_id="EMP003"
        )
