-- ============================================================
-- Step 32 – Soft-delete products
-- Adds is_deleted flag so archived products are hidden from buyers
-- but their order history remains intact.
-- ============================================================

-- 1. Add the column (safe to run multiple times)
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Partial index: fast scans that exclude deleted products
CREATE INDEX IF NOT EXISTS idx_products_not_deleted
  ON products (seller_id, created_at DESC)
  WHERE is_deleted = FALSE;

-- 3. All existing products are considered NOT deleted
UPDATE products SET is_deleted = FALSE WHERE is_deleted IS NULL;
