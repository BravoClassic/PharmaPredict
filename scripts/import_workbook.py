"""Load the PharmaPredict v1.2 synthetic workbook into MySQL.

Usage:
    python scripts/import_workbook.py --workbook data/PharmaPredict_v1_2_Business_Realistic_Dataset.xlsx

Database connection is read from DATABASE_URL when set. Otherwise the script
builds a MySQL URL from MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE,
MYSQL_USERNAME and MYSQL_PASSWORD.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATE_COLUMNS = {
    "Purchase_Order": ["Order_Date", "Expected_Date"],
    "Receipt": ["Receipt_Date"],
    "Inventory_Batch": ["Date_Received", "Expiration_Date"],
    "Inventory_Transaction": ["Transaction_Date"],
}


def database_url() -> str:
    load_dotenv()
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "pharmapredict")
    username = os.getenv("MYSQL_USERNAME", "pharmapredict_user")
    password = os.getenv("MYSQL_PASSWORD", "")
    return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def read_sheet(workbook: Path, name: str) -> pd.DataFrame:
    df = pd.read_excel(workbook, sheet_name=name, dtype=object)
    df = df.where(pd.notna(df), None)
    for col in DATE_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="raise").dt.date
    return df


def rows(df: pd.DataFrame, rename: dict[str, str] | None = None) -> list[dict]:
    if rename:
        df = df.rename(columns=rename)
    return df.to_dict(orient="records")


def execute_many(engine: Engine, sql: str, payload: Iterable[dict], chunk_size: int = 2000) -> int:
    payload = list(payload)
    if not payload:
        return 0

    with engine.begin() as conn:
        for start in range(0, len(payload), chunk_size):
            conn.execute(text(sql), payload[start : start + chunk_size])
    return len(payload)


def clear_operational_tables(engine: Engine) -> None:
    # Child-to-parent order. Static TransactionType rows are kept.
    statements = [
        "DELETE FROM InventoryTransaction",
        "DELETE FROM InventoryBatch",
        "DELETE FROM ReceiptItem",
        "DELETE FROM Receipt",
        "DELETE FROM PurchaseOrderItem",
        "DELETE FROM PurchaseOrder",
        "DELETE FROM ScenarioMetadata",
        "DELETE FROM PharmacyMedication",
        "DELETE FROM Employee",
        "DELETE FROM Supplier",
        "DELETE FROM Pharmacy",
        "DELETE FROM Medication",
        "DELETE FROM Manufacturer",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def load(workbook: Path, engine: Engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    clear_operational_tables(engine)

    medication = read_sheet(workbook, "Medication")
    manufacturers = sorted({str(v) for v in medication["Manufacturer"] if v is not None})

    manufacturer_rows = [{"name": name} for name in manufacturers]
    counts["Manufacturer"] = execute_many(
        engine,
        "INSERT INTO Manufacturer (ManufacturerName) VALUES (:name)",
        manufacturer_rows,
    )

    with engine.connect() as conn:
        manufacturer_map = dict(
            conn.execute(text("SELECT ManufacturerName, ManufacturerID FROM Manufacturer")).all()
        )

    med_rows = []
    policy_rows = []
    for rec in medication.to_dict(orient="records"):
        med_rows.append(
            {
                "MedicationID": rec["Medication_ID"],
                "NDCNumber": rec["NDC_Number"],
                "GenericName": rec["Generic_Name"],
                "DisplayName": rec["Display_Name"],
                "Strength": rec["Strength"],
                "DosageForm": rec["Dosage_Form"],
                "ManufacturerID": manufacturer_map[str(rec["Manufacturer"])],
                "PackageSize": int(rec["Package_Size"]),
            }
        )
        policy_rows.append(
            {
                "PharmacyID": "LOC001",
                "MedicationID": rec["Medication_ID"],
                "ReorderPoint": int(rec["Reorder_Point"]),
                "TargetDaysOnHand": int(rec["Target_Days_On_Hand"]),
                "LeadTimeDays": int(rec["Lead_Time_Days"]),
            }
        )

    counts["Medication"] = execute_many(
        engine,
        """INSERT INTO Medication
           (MedicationID,NDCNumber,GenericName,DisplayName,Strength,DosageForm,ManufacturerID,PackageSize)
           VALUES
           (:MedicationID,:NDCNumber,:GenericName,:DisplayName,:Strength,:DosageForm,:ManufacturerID,:PackageSize)""",
        med_rows,
    )

    location = read_sheet(workbook, "Pharmacy_Location")
    pharmacy_rows = [
        {
            "PharmacyID": r["Location_ID"],
            "PharmacyName": r["Location_Name"],
            "PharmacyType": r["Location_Type"],
            "City": r["City"],
            "State": r["State"],
            "ZIPCode": str(r["ZIP_Code"]) if r["ZIP_Code"] is not None else None,
        }
        for r in location.to_dict(orient="records")
    ]
    counts["Pharmacy"] = execute_many(
        engine,
        """INSERT INTO Pharmacy
           (PharmacyID,PharmacyName,PharmacyType,City,State,ZIPCode)
           VALUES (:PharmacyID,:PharmacyName,:PharmacyType,:City,:State,:ZIPCode)""",
        pharmacy_rows,
    )

    counts["PharmacyMedication"] = execute_many(
        engine,
        """INSERT INTO PharmacyMedication
           (PharmacyID,MedicationID,ReorderPoint,TargetDaysOnHand,LeadTimeDays)
           VALUES (:PharmacyID,:MedicationID,:ReorderPoint,:TargetDaysOnHand,:LeadTimeDays)""",
        policy_rows,
    )

    supplier = rows(read_sheet(workbook, "Supplier"), {
        "Supplier_ID":"SupplierID","Supplier_Name":"SupplierName","Contact_Name":"ContactName",
        "Phone":"Phone","Email":"Email","City":"City","State":"State"
    })
    counts["Supplier"] = execute_many(
        engine,
        """INSERT INTO Supplier
           (SupplierID,SupplierName,ContactName,Phone,Email,City,State)
           VALUES (:SupplierID,:SupplierName,:ContactName,:Phone,:Email,:City,:State)""",
        supplier,
    )

    employee = rows(read_sheet(workbook, "Employee"), {
        "Employee_ID":"EmployeeID","First_Name":"FirstName","Last_Name":"LastName","Role":"Role"
    })
    counts["Employee"] = execute_many(
        engine,
        """INSERT INTO Employee (EmployeeID,FirstName,LastName,Role)
           VALUES (:EmployeeID,:FirstName,:LastName,:Role)""",
        employee,
    )

    po = read_sheet(workbook, "Purchase_Order")
    po_rows = [
        {
            "PurchaseOrderID": r["Purchase_Order_ID"],
            "SupplierID": r["Supplier_ID"],
            "PharmacyID": "LOC001",
            "OrderedByEmployeeID": None,
            "OrderDate": r["Order_Date"],
            "ExpectedDate": r["Expected_Date"],
        }
        for r in po.to_dict(orient="records")
    ]
    counts["PurchaseOrder"] = execute_many(
        engine,
        """INSERT INTO PurchaseOrder
           (PurchaseOrderID,SupplierID,PharmacyID,OrderedByEmployeeID,OrderDate,ExpectedDate)
           VALUES (:PurchaseOrderID,:SupplierID,:PharmacyID,:OrderedByEmployeeID,:OrderDate,:ExpectedDate)""",
        po_rows,
    )

    poi = rows(read_sheet(workbook, "Purchase_Order_Item"), {
        "PO_Item_ID":"POItemID","Purchase_Order_ID":"PurchaseOrderID","Line_Number":"LineNumber",
        "Medication_ID":"MedicationID","Packages_Ordered":"PackagesOrdered",
        "Package_Size":"PackageSize","Unit_Cost":"UnitCost"
    })
    counts["PurchaseOrderItem"] = execute_many(
        engine,
        """INSERT INTO PurchaseOrderItem
           (POItemID,PurchaseOrderID,LineNumber,MedicationID,PackagesOrdered,PackageSize,UnitCost)
           VALUES (:POItemID,:PurchaseOrderID,:LineNumber,:MedicationID,:PackagesOrdered,:PackageSize,:UnitCost)""",
        poi,
    )

    receipt = rows(read_sheet(workbook, "Receipt"), {
        "Receipt_ID":"ReceiptID","Purchase_Order_ID":"PurchaseOrderID",
        "Receipt_Date":"ReceiptDate","Received_By_Employee_ID":"ReceivedByEmployeeID"
    })
    counts["Receipt"] = execute_many(
        engine,
        """INSERT INTO Receipt
           (ReceiptID,PurchaseOrderID,ReceiptDate,ReceivedByEmployeeID)
           VALUES (:ReceiptID,:PurchaseOrderID,:ReceiptDate,:ReceivedByEmployeeID)""",
        receipt,
    )

    receipt_item = read_sheet(workbook, "Receipt_Item")
    ri_rows = [
        {
            "ReceiptItemID": r["Receipt_Item_ID"],
            "ReceiptID": r["Receipt_ID"],
            "POItemID": r["PO_Item_ID"],
            "PackagesReceived": int(r["Packages_Received"]),
        }
        for r in receipt_item.to_dict(orient="records")
    ]
    counts["ReceiptItem"] = execute_many(
        engine,
        """INSERT INTO ReceiptItem
           (ReceiptItemID,ReceiptID,POItemID,PackagesReceived)
           VALUES (:ReceiptItemID,:ReceiptID,:POItemID,:PackagesReceived)""",
        ri_rows,
    )

    batch = read_sheet(workbook, "Inventory_Batch")
    batch_rows = [
        {
            "BatchID": r["Batch_ID"],
            "MedicationID": r["Medication_ID"],
            "SupplierID": r["Supplier_ID"],
            "PharmacyID": r["Location_ID"],
            "ReceiptItemID": r["Receipt_Item_ID"],
            "LotNumber": r["Lot_Number"],
            "DateReceived": r["Date_Received"],
            "ExpirationDate": r["Expiration_Date"],
            "UnitCost": r["Unit_Cost"],
            "SourceType": r["Source_Type"],
        }
        for r in batch.to_dict(orient="records")
    ]
    counts["InventoryBatch"] = execute_many(
        engine,
        """INSERT INTO InventoryBatch
           (BatchID,MedicationID,SupplierID,PharmacyID,ReceiptItemID,LotNumber,
            DateReceived,ExpirationDate,UnitCost,SourceType)
           VALUES (:BatchID,:MedicationID,:SupplierID,:PharmacyID,:ReceiptItemID,:LotNumber,
                   :DateReceived,:ExpirationDate,:UnitCost,:SourceType)""",
        batch_rows,
    )

    scenario = rows(read_sheet(workbook, "Scenario_Metadata"), {
        "Medication_ID":"MedicationID","Scenario_Tag":"ScenarioTag",
        "Scenario_Description":"ScenarioDescription"
    })
    counts["ScenarioMetadata"] = execute_many(
        engine,
        """INSERT INTO ScenarioMetadata
           (MedicationID,ScenarioTag,ScenarioDescription)
           VALUES (:MedicationID,:ScenarioTag,:ScenarioDescription)""",
        scenario,
    )

    txn = read_sheet(workbook, "Inventory_Transaction")
    txn = txn.sort_values(["Transaction_Date", "Transaction_ID"])
    txn_rows = [
        {
            "TransactionID": r["Transaction_ID"],
            "BatchID": r["Batch_ID"],
            "TransactionType": r["Transaction_Type"],
            "QuantityChange": int(r["Quantity_Change"]),
            "TransactionTimestamp": pd.Timestamp(r["Transaction_Date"]).to_pydatetime(),
            "ReceiptItemID": r["Receipt_Item_ID"],
            "RxNumber": r["Rx_Number"],
            "EmployeeID": r["Employee_ID"],
        }
        for r in txn.to_dict(orient="records")
    ]
    counts["InventoryTransaction"] = execute_many(
        engine,
        """INSERT INTO InventoryTransaction
           (TransactionID,BatchID,TransactionType,QuantityChange,TransactionTimestamp,
            ReceiptItemID,RxNumber,EmployeeID)
           VALUES (:TransactionID,:BatchID,:TransactionType,:QuantityChange,:TransactionTimestamp,
                   :ReceiptItemID,:RxNumber,:EmployeeID)""",
        txn_rows,
        chunk_size=3000,
    )

    return counts


def reconcile(engine: Engine) -> None:
    checks = {
        "negative_batch_balances":
            "SELECT COUNT(*) FROM vw_batch_balance WHERE QuantityOnHand < 0",
        "post_expiry_dispenses":
            """SELECT COUNT(*)
               FROM InventoryTransaction t
               JOIN InventoryBatch b ON b.BatchID=t.BatchID
               WHERE t.TransactionType='DISPENSE'
                 AND DATE(t.TransactionTimestamp) >= b.ExpirationDate""",
        "receipt_line_overages":
            """SELECT COUNT(*)
               FROM vw_po_status
               WHERE PackagesReceived > PackagesOrdered""",
    }
    with engine.connect() as conn:
        failed = []
        for name, sql in checks.items():
            value = conn.scalar(text(sql))
            print(f"{name}: {value}")
            if value:
                failed.append((name, value))
        if failed:
            raise RuntimeError(f"Reconciliation failed: {failed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--skip-reconcile", action="store_true")
    args = parser.parse_args()

    if not args.workbook.exists():
        raise SystemExit(f"Workbook not found: {args.workbook}")

    engine = create_engine(database_url(), pool_pre_ping=True)
    counts = load(args.workbook, engine)
    for table, count in counts.items():
        print(f"{table}: {count}")

    if not args.skip_reconcile:
        reconcile(engine)
        print("Reconciliation passed.")


if __name__ == "__main__":
    main()
