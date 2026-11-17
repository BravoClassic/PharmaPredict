# PharmaPredict — Perpetual Pharmacy Inventory Management

**Mercy University · CISC 520 · Fall 2026 · Team project**

PharmaPredict is a proposed Python desktop application backed by **MySQL** for tracking pharmacy inventory at the batch/lot level. The development plan covers inventory transactions, purchasing and receiving, FEFO guidance, stock alerts, inventory valuation and audit queries.

> **Project status:** planning and development scaffold. The presence of a tracked task does **not** mean the feature is implemented. All dates in the attached plan are provisional until the instructor confirms the submission deadlines.

## Team responsibilities

| Contributor | Proposed primary role |
| --- | --- |
| Gerald Akorli | Backend & Analytics Lead |
| Daniel Cardona | Database & Data Engineering Lead |
| Dare Akinpelu | Desktop Application & Integration Lead |

Individual GitHub assignments require each teammate's exact GitHub username. Team ownership in the GitHub Project is represented by its **Team Member** field until usernames are confirmed.

## Technology plan

- MySQL 8+ database, keys, constraints, stored routines, views and transactions
- Python 3, SQLAlchemy 2, Alembic and pandas for the backend and import pipeline
- PySide6 (Qt) desktop interface; matplotlib for dashboard charts
- pytest and a reproducible local installation

## Important business invariants

- Batch on-hand balance is the **sum of signed inventory transactions** for that batch.
- Opening stock batches may lack purchase-order receipt lineage. Do not require a receipt link for those lots.
- FEFO applies only to eligible, unexpired lots with positive available stock.
- Package quantities and medication inventory units must not be mixed.
- Purchases or adjustments proposed by an assistant require explicit human approval.
- Synthetic records do **not** establish production pharmacy regulatory compliance.

## Roadmap and issue tracking

- [Work breakdown (CSV)](docs/WORK_BREAKDOWN.csv): 54 implementation and academic tasks.
- [Architecture](docs/ARCHITECTURE.md): proposed module boundaries and business rules.
- [Team charter](docs/TEAM_CHARTER.md): working agreements and peer-review expectations.
- [Academic deliverables](docs/COURSE_DELIVERABLES.md): instructor's three-phase checklist.

A GitHub Projects board is created and linked to this repository by the accompanying setup script. Its views can be configured in GitHub as a Board grouped by **Status**, a Table grouped by **Team Member**, and a Roadmap by planned dates.

## Local development

Application code has not been implemented in this scaffold yet. Do not expect `python -m app` to run until the appropriate issues are completed. Keep your MySQL credentials in `.env` (never commit them). Synthetic dataset workbooks belong in the `data/` directory and should be reviewed before publication.
