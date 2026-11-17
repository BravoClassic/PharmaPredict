# Architecture proposal (approval pending)

```text
PySide6 Desktop UI
  ↕ service interfaces (typed data transfer objects)
Python business / application services
  ↕ SQLAlchemy sessions and repository interfaces
MySQL 8+ transactional database
  ↕ import, views, reports, routines
Hinkle synthetic workbook and SQL analytics
```

The architecture separates UI, business logic, persistence, and forecasting so team members can work in parallel. PySide6 screens may initially use mock services with the same contract as the real backend.

## Database constraints to preserve

1. Inventory batch quantities derive from the signed `InventoryTransaction` ledger.
2. Each purchase-order item belongs to a purchase order, and received items must reference matching purchase-order lines.
3. Opening inventory batches may have no receipt item reference.
4. Stock mutations must be atomic, reject negative balances, and retain an audit trail.
5. FEFO excludes expired and empty lots.
6. Scenario metadata is a synthetic testing fixture, not operational stock.

The exact physical schema, including cross-table integrity rules and normalized medication policy, is to be reviewed against the approved logical ER diagram and dataset.

## Service contract candidates

| Service | Candidate operations |
| --- | --- |
| Medication | list, search, read, create/update with validation |
| Inventory | on_hand, list_eligible_batches, expiration_alerts |
| Stock movement | receive, dispense, adjust, expire, history |
| Purchasing | create_order, list_order_lines, receive_order_line, outstanding |
| Reporting | valuation, turnover, reorder_suggestions, FEFO |

All write operations need a documented transaction boundary, tests, and appropriate human authorization.
