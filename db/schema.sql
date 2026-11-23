-- PharmaPredict physical schema
-- CISC 520 / MySQL 8+
-- Source-aligned to PharmaPredict v1.2 synthetic workbook.
-- Operational balances are derived from signed inventory movements.

CREATE DATABASE IF NOT EXISTS pharmapredict
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE pharmapredict;

CREATE TABLE Manufacturer (
  ManufacturerID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ManufacturerName VARCHAR(120) NOT NULL,
  CONSTRAINT uq_manufacturer_name UNIQUE (ManufacturerName)
) ENGINE=InnoDB;

CREATE TABLE Medication (
  MedicationID VARCHAR(10) PRIMARY KEY,
  NDCNumber VARCHAR(20) NOT NULL,
  GenericName VARCHAR(100) NOT NULL,
  DisplayName VARCHAR(140) NOT NULL,
  Strength VARCHAR(40),
  DosageForm VARCHAR(40),
  ManufacturerID INT UNSIGNED NOT NULL,
  PackageSize INT UNSIGNED NOT NULL,
  CONSTRAINT uq_medication_ndc UNIQUE (NDCNumber),
  CONSTRAINT ck_medication_package_size CHECK (PackageSize > 0),
  CONSTRAINT fk_medication_manufacturer
    FOREIGN KEY (ManufacturerID) REFERENCES Manufacturer(ManufacturerID)
) ENGINE=InnoDB;

CREATE TABLE Pharmacy (
  PharmacyID VARCHAR(10) PRIMARY KEY,
  PharmacyName VARCHAR(140) NOT NULL,
  PharmacyType VARCHAR(60),
  City VARCHAR(80),
  State CHAR(2),
  ZIPCode VARCHAR(10)
) ENGINE=InnoDB;

CREATE TABLE PharmacyMedication (
  PharmacyID VARCHAR(10) NOT NULL,
  MedicationID VARCHAR(10) NOT NULL,
  ReorderPoint INT UNSIGNED NOT NULL DEFAULT 0,
  TargetDaysOnHand INT UNSIGNED NOT NULL,
  LeadTimeDays INT UNSIGNED NOT NULL,
  PRIMARY KEY (PharmacyID, MedicationID),
  CONSTRAINT ck_pm_target_days CHECK (TargetDaysOnHand > 0),
  CONSTRAINT ck_pm_lead_days CHECK (LeadTimeDays > 0),
  CONSTRAINT fk_pm_pharmacy
    FOREIGN KEY (PharmacyID) REFERENCES Pharmacy(PharmacyID),
  CONSTRAINT fk_pm_medication
    FOREIGN KEY (MedicationID) REFERENCES Medication(MedicationID)
) ENGINE=InnoDB;

CREATE TABLE Supplier (
  SupplierID VARCHAR(10) PRIMARY KEY,
  SupplierName VARCHAR(140) NOT NULL,
  ContactName VARCHAR(120),
  Phone VARCHAR(30),
  Email VARCHAR(160),
  City VARCHAR(80),
  State CHAR(2)
) ENGINE=InnoDB;

CREATE TABLE Employee (
  EmployeeID VARCHAR(10) PRIMARY KEY,
  FirstName VARCHAR(80) NOT NULL,
  LastName VARCHAR(80) NOT NULL,
  Role VARCHAR(80) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE PurchaseOrder (
  PurchaseOrderID VARCHAR(12) PRIMARY KEY,
  SupplierID VARCHAR(10) NOT NULL,
  PharmacyID VARCHAR(10) NOT NULL,
  OrderedByEmployeeID VARCHAR(10) NULL,
  OrderDate DATE NOT NULL,
  ExpectedDate DATE,
  CONSTRAINT ck_po_expected_date
    CHECK (ExpectedDate IS NULL OR ExpectedDate >= OrderDate),
  CONSTRAINT fk_po_supplier
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID),
  CONSTRAINT fk_po_pharmacy
    FOREIGN KEY (PharmacyID) REFERENCES Pharmacy(PharmacyID),
  CONSTRAINT fk_po_employee
    FOREIGN KEY (OrderedByEmployeeID) REFERENCES Employee(EmployeeID)
) ENGINE=InnoDB;

CREATE TABLE PurchaseOrderItem (
  POItemID VARCHAR(14) PRIMARY KEY,
  PurchaseOrderID VARCHAR(12) NOT NULL,
  LineNumber INT UNSIGNED NOT NULL,
  MedicationID VARCHAR(10) NOT NULL,
  PackagesOrdered INT UNSIGNED NOT NULL,
  PackageSize INT UNSIGNED NOT NULL,
  UnitCost DECIMAL(12,4) NOT NULL,
  CONSTRAINT uq_po_line UNIQUE (PurchaseOrderID, LineNumber),
  CONSTRAINT uq_po_medication UNIQUE (PurchaseOrderID, MedicationID),
  CONSTRAINT ck_poi_packages CHECK (PackagesOrdered > 0),
  CONSTRAINT ck_poi_package_size CHECK (PackageSize > 0),
  CONSTRAINT ck_poi_unit_cost CHECK (UnitCost >= 0),
  CONSTRAINT fk_poi_order
    FOREIGN KEY (PurchaseOrderID) REFERENCES PurchaseOrder(PurchaseOrderID),
  CONSTRAINT fk_poi_medication
    FOREIGN KEY (MedicationID) REFERENCES Medication(MedicationID)
) ENGINE=InnoDB;

CREATE TABLE Receipt (
  ReceiptID VARCHAR(12) PRIMARY KEY,
  PurchaseOrderID VARCHAR(12) NOT NULL,
  ReceiptDate DATE NOT NULL,
  ReceivedByEmployeeID VARCHAR(10) NOT NULL,
  CONSTRAINT fk_receipt_order
    FOREIGN KEY (PurchaseOrderID) REFERENCES PurchaseOrder(PurchaseOrderID),
  CONSTRAINT fk_receipt_employee
    FOREIGN KEY (ReceivedByEmployeeID) REFERENCES Employee(EmployeeID)
) ENGINE=InnoDB;

CREATE TABLE ReceiptItem (
  ReceiptItemID VARCHAR(14) PRIMARY KEY,
  ReceiptID VARCHAR(12) NOT NULL,
  POItemID VARCHAR(14) NOT NULL,
  PackagesReceived INT UNSIGNED NOT NULL,
  CONSTRAINT ck_ri_packages CHECK (PackagesReceived > 0),
  CONSTRAINT fk_ri_receipt
    FOREIGN KEY (ReceiptID) REFERENCES Receipt(ReceiptID),
  CONSTRAINT fk_ri_po_item
    FOREIGN KEY (POItemID) REFERENCES PurchaseOrderItem(POItemID)
) ENGINE=InnoDB;

CREATE TABLE InventoryBatch (
  BatchID VARCHAR(12) PRIMARY KEY,
  MedicationID VARCHAR(10) NOT NULL,
  SupplierID VARCHAR(10) NOT NULL,
  PharmacyID VARCHAR(10) NOT NULL,
  ReceiptItemID VARCHAR(14) NULL,
  LotNumber VARCHAR(40) NOT NULL,
  DateReceived DATE NOT NULL,
  ExpirationDate DATE NOT NULL,
  UnitCost DECIMAL(12,4) NOT NULL,
  SourceType ENUM('OPENING','RECEIPT') NOT NULL,
  CONSTRAINT uq_batch_lot UNIQUE (LotNumber),
  CONSTRAINT uq_batch_receipt_item UNIQUE (ReceiptItemID),
  CONSTRAINT ck_batch_expiry CHECK (ExpirationDate > DateReceived),
  CONSTRAINT ck_batch_cost CHECK (UnitCost >= 0),
  CONSTRAINT ck_batch_source_lineage CHECK (
    (SourceType = 'OPENING' AND ReceiptItemID IS NULL)
    OR
    (SourceType = 'RECEIPT' AND ReceiptItemID IS NOT NULL)
  ),
  CONSTRAINT fk_batch_medication
    FOREIGN KEY (MedicationID) REFERENCES Medication(MedicationID),
  CONSTRAINT fk_batch_supplier
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID),
  CONSTRAINT fk_batch_pharmacy
    FOREIGN KEY (PharmacyID) REFERENCES Pharmacy(PharmacyID),
  CONSTRAINT fk_batch_receipt_item
    FOREIGN KEY (ReceiptItemID) REFERENCES ReceiptItem(ReceiptItemID)
) ENGINE=InnoDB;

CREATE TABLE TransactionType (
  TransactionType VARCHAR(30) PRIMARY KEY,
  Direction ENUM('POSITIVE','NEGATIVE','EITHER') NOT NULL,
  Description VARCHAR(180) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE InventoryTransaction (
  TransactionID VARCHAR(14) PRIMARY KEY,
  BatchID VARCHAR(12) NOT NULL,
  TransactionType VARCHAR(30) NOT NULL,
  QuantityChange INT NOT NULL,
  TransactionTimestamp DATETIME NOT NULL,
  ReceiptItemID VARCHAR(14) NULL,
  RxNumber VARCHAR(30) NULL,
  EmployeeID VARCHAR(10) NOT NULL,
  CONSTRAINT ck_inventory_txn_nonzero CHECK (QuantityChange <> 0),
  CONSTRAINT fk_txn_batch
    FOREIGN KEY (BatchID) REFERENCES InventoryBatch(BatchID),
  CONSTRAINT fk_txn_type
    FOREIGN KEY (TransactionType) REFERENCES TransactionType(TransactionType),
  CONSTRAINT fk_txn_receipt_item
    FOREIGN KEY (ReceiptItemID) REFERENCES ReceiptItem(ReceiptItemID),
  CONSTRAINT fk_txn_employee
    FOREIGN KEY (EmployeeID) REFERENCES Employee(EmployeeID),
  INDEX ix_txn_batch_time (BatchID, TransactionTimestamp),
  INDEX ix_txn_type_time (TransactionType, TransactionTimestamp),
  INDEX ix_txn_rx (RxNumber)
) ENGINE=InnoDB;

CREATE TABLE ScenarioMetadata (
  MedicationID VARCHAR(10) NOT NULL,
  ScenarioTag VARCHAR(60) NOT NULL,
  ScenarioDescription VARCHAR(255) NOT NULL,
  PRIMARY KEY (MedicationID, ScenarioTag),
  CONSTRAINT fk_scenario_medication
    FOREIGN KEY (MedicationID) REFERENCES Medication(MedicationID)
) ENGINE=InnoDB;

INSERT INTO TransactionType (TransactionType, Direction, Description) VALUES
  ('OPENING_BALANCE','POSITIVE','Opening stock loaded when the perpetual ledger begins'),
  ('RECEIPT','POSITIVE','Stock received against a purchase-order receipt'),
  ('DISPENSE','NEGATIVE','Medication dispensed against a prescription'),
  ('EXPIRATION','NEGATIVE','Expired stock removed from available inventory'),
  ('DAMAGE','NEGATIVE','Damaged stock removed from available inventory'),
  ('ADJUSTMENT_POS','POSITIVE','Positive verified inventory adjustment'),
  ('ADJUSTMENT_NEG','NEGATIVE','Negative verified inventory adjustment')
ON DUPLICATE KEY UPDATE
  Direction = VALUES(Direction),
  Description = VALUES(Description);

CREATE OR REPLACE VIEW vw_batch_balance AS
SELECT
  b.BatchID,
  b.MedicationID,
  b.PharmacyID,
  b.LotNumber,
  b.ExpirationDate,
  b.UnitCost,
  COALESCE(SUM(t.QuantityChange),0) AS QuantityOnHand,
  COALESCE(SUM(t.QuantityChange),0) * b.UnitCost AS InventoryValue
FROM InventoryBatch b
LEFT JOIN InventoryTransaction t ON t.BatchID = b.BatchID
GROUP BY
  b.BatchID,b.MedicationID,b.PharmacyID,b.LotNumber,b.ExpirationDate,b.UnitCost;

CREATE OR REPLACE VIEW vw_inventory_summary AS
SELECT
  pm.PharmacyID,
  m.MedicationID,
  m.DisplayName,
  pm.ReorderPoint,
  pm.TargetDaysOnHand,
  pm.LeadTimeDays,
  COALESCE(SUM(bb.QuantityOnHand),0) AS QuantityOnHand,
  COALESCE(SUM(bb.InventoryValue),0) AS InventoryValue,
  MIN(CASE WHEN bb.QuantityOnHand > 0 THEN bb.ExpirationDate END) AS EarliestActiveExpiration
FROM PharmacyMedication pm
JOIN Medication m ON m.MedicationID = pm.MedicationID
LEFT JOIN vw_batch_balance bb
  ON bb.PharmacyID = pm.PharmacyID
 AND bb.MedicationID = pm.MedicationID
GROUP BY
  pm.PharmacyID,m.MedicationID,m.DisplayName,
  pm.ReorderPoint,pm.TargetDaysOnHand,pm.LeadTimeDays;

CREATE OR REPLACE VIEW vw_fefo_eligible AS
SELECT
  bb.BatchID,
  bb.PharmacyID,
  bb.MedicationID,
  bb.LotNumber,
  bb.ExpirationDate,
  bb.QuantityOnHand
FROM vw_batch_balance bb
WHERE bb.QuantityOnHand > 0
  AND bb.ExpirationDate > CURRENT_DATE();

CREATE OR REPLACE VIEW vw_expiring_60d AS
SELECT *
FROM vw_fefo_eligible
WHERE ExpirationDate <= DATE_ADD(CURRENT_DATE(), INTERVAL 60 DAY);

CREATE OR REPLACE VIEW vw_po_status AS
SELECT
  po.PurchaseOrderID,
  poi.POItemID,
  poi.MedicationID,
  poi.PackagesOrdered,
  COALESCE(SUM(ri.PackagesReceived),0) AS PackagesReceived,
  CASE
    WHEN COALESCE(SUM(ri.PackagesReceived),0) = 0 THEN 'OPEN'
    WHEN COALESCE(SUM(ri.PackagesReceived),0) < poi.PackagesOrdered THEN 'PARTIAL'
    ELSE 'RECEIVED'
  END AS LineStatus
FROM PurchaseOrder po
JOIN PurchaseOrderItem poi ON poi.PurchaseOrderID = po.PurchaseOrderID
LEFT JOIN ReceiptItem ri ON ri.POItemID = poi.POItemID
GROUP BY
  po.PurchaseOrderID,poi.POItemID,poi.MedicationID,poi.PackagesOrdered;

CREATE OR REPLACE VIEW vw_units_on_order AS
SELECT
  po.PharmacyID,
  poi.MedicationID,
  SUM(
    GREATEST(poi.PackagesOrdered - COALESCE(r.PackagesReceived,0),0)
    * poi.PackageSize
  ) AS UnitsOnOrder
FROM PurchaseOrder po
JOIN PurchaseOrderItem poi ON poi.PurchaseOrderID = po.PurchaseOrderID
LEFT JOIN (
  SELECT POItemID, SUM(PackagesReceived) AS PackagesReceived
  FROM ReceiptItem
  GROUP BY POItemID
) r ON r.POItemID = poi.POItemID
GROUP BY po.PharmacyID,poi.MedicationID;

CREATE OR REPLACE VIEW vw_low_stock AS
SELECT
  s.*,
  COALESCE(o.UnitsOnOrder,0) AS UnitsOnOrder
FROM vw_inventory_summary s
LEFT JOIN vw_units_on_order o
  ON o.PharmacyID = s.PharmacyID
 AND o.MedicationID = s.MedicationID
WHERE s.QuantityOnHand <= s.ReorderPoint;

DELIMITER $$

CREATE TRIGGER trg_inventory_transaction_validate
BEFORE INSERT ON InventoryTransaction
FOR EACH ROW
BEGIN
  DECLARE v_expiration DATE;
  DECLARE v_direction VARCHAR(10);
  DECLARE v_balance BIGINT;

  SELECT ExpirationDate
    INTO v_expiration
  FROM InventoryBatch
  WHERE BatchID = NEW.BatchID;

  SELECT Direction
    INTO v_direction
  FROM TransactionType
  WHERE TransactionType = NEW.TransactionType;

  IF v_direction = 'POSITIVE' AND NEW.QuantityChange <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Positive transaction type requires positive QuantityChange';
  END IF;

  IF v_direction = 'NEGATIVE' AND NEW.QuantityChange >= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Negative transaction type requires negative QuantityChange';
  END IF;

  IF NEW.TransactionType = 'DISPENSE'
     AND DATE(NEW.TransactionTimestamp) >= v_expiration THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Cannot dispense expired stock';
  END IF;

  IF NEW.TransactionType = 'DISPENSE' AND NEW.RxNumber IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Dispense transaction requires RxNumber';
  END IF;

  SELECT COALESCE(SUM(QuantityChange),0)
    INTO v_balance
  FROM InventoryTransaction
  WHERE BatchID = NEW.BatchID;

  IF v_balance + NEW.QuantityChange < 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Inventory movement would create a negative batch balance';
  END IF;
END$$

DELIMITER ;
