"""Typed DTOs exposed by the application service layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class InventorySummary:
    pharmacy_id: str
    medication_id: str
    display_name: str
    reorder_point: int
    quantity_on_hand: int
    inventory_value: Decimal
    earliest_active_expiration: date | None


@dataclass(frozen=True)
class EligibleBatch:
    batch_id: str
    pharmacy_id: str
    medication_id: str
    lot_number: str
    expiration_date: date
    quantity_on_hand: int


@dataclass(frozen=True)
class MovementResult:
    transaction_id: str
    batch_id: str
    quantity_change: int
    resulting_balance: int
