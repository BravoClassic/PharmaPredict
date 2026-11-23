-- PharmaPredict database smoke checks
USE pharmapredict;

-- 1. Every batch balance must be nonnegative.
SELECT COUNT(*) AS negative_batch_balances
FROM vw_batch_balance
WHERE QuantityOnHand < 0;

-- 2. No dispense may occur on or after the batch expiration date.
SELECT COUNT(*) AS post_expiry_dispenses
FROM InventoryTransaction t
JOIN InventoryBatch b ON b.BatchID = t.BatchID
WHERE t.TransactionType = 'DISPENSE'
  AND DATE(t.TransactionTimestamp) >= b.ExpirationDate;

-- 3. Receipt packages must never exceed ordered packages for a PO line.
SELECT COUNT(*) AS receipt_line_overages
FROM vw_po_status
WHERE PackagesReceived > PackagesOrdered;

-- 4. Every receipt-sourced batch must have receipt lineage.
SELECT COUNT(*) AS missing_receipt_lineage
FROM InventoryBatch
WHERE SourceType = 'RECEIPT'
  AND ReceiptItemID IS NULL;

-- 5. Opening inventory is the explicit exception: no receipt lineage.
SELECT COUNT(*) AS invalid_opening_lineage
FROM InventoryBatch
WHERE SourceType = 'OPENING'
  AND ReceiptItemID IS NOT NULL;

-- 6. Core demo queries.
SELECT * FROM vw_low_stock ORDER BY QuantityOnHand;
SELECT * FROM vw_expiring_60d ORDER BY ExpirationDate;
SELECT * FROM vw_fefo_eligible ORDER BY MedicationID, ExpirationDate;
SELECT * FROM vw_inventory_summary ORDER BY InventoryValue DESC;
