# Local database setup

This branch implements the first runnable PharmaPredict foundation: the MySQL physical schema, source-aligned views/constraints, and a deterministic loader for the audited v1.2 workbook.

## Prerequisites

- MySQL 8+
- Python 3.11+
- PharmaPredict v1.2 synthetic workbook

## 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure MySQL

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your local MySQL credentials.

The application user needs permission to create/use the `pharmapredict` database during development. For a stricter setup, an administrator can execute the schema first and grant the application account only the permissions it needs.

## 3. Create the physical schema

```bash
mysql -u root -p < db/schema.sql
```

The schema intentionally derives these values rather than storing duplicate fields:

- batch quantity on hand
- current inventory value
- purchase-order receipt status
- units currently on order

It also keeps opening inventory as the explicit exception to receipt lineage.

## 4. Place the approved workbook

Copy the audited workbook to:

```text
data/PharmaPredict_v1_2_Business_Realistic_Dataset.xlsx
```

The workbook is synthetic project data, not live Hinkle Pharmacy production data.

## 5. Import and reconcile

```bash
python scripts/import_workbook.py \
  --workbook data/PharmaPredict_v1_2_Business_Realistic_Dataset.xlsx
```

The importer:

1. clears previously imported operational rows;
2. normalizes manufacturer names into `Manufacturer`;
3. moves pharmacy-specific reorder settings into `PharmacyMedication`;
4. loads parent tables before child tables;
5. converts workbook dates into database dates/timestamps;
6. omits source fields that are intentionally derived in the physical model;
7. loads inventory movements chronologically;
8. runs reconciliation checks for negative stock, post-expiry dispensing and receipt overages.

## 6. Run SQL smoke checks

```bash
mysql -u pharmapredict_user -p pharmapredict < db/smoke_checks.sql
```

The first five result counts should all be zero.

## Current implementation boundary

Implemented on this foundation branch:

- MySQL physical schema
- PK/FK/unique/check constraints
- signed inventory ledger
- batch balance, valuation, FEFO, expiry, PO status, outstanding-order and low-stock views
- stock mutation validation trigger
- deterministic v1.2 workbook importer
- reconciliation SQL

Not yet implemented:

- SQLAlchemy domain/repository layer
- atomic application services for receipt/dispense/adjustment
- PySide6 screens
- application-level approval workflow
- automated pytest integration suite
