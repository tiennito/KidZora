-- ============================================================
-- Step 30: Guarantee delivery_fee is always a valid number
--          and backfill delivered_at for historical orders.
-- Run in Supabase SQL Editor AFTER all previous steps.
-- ============================================================

-- ── 1. Backfill delivery_fee NULLs to 0 ──────────────────────
--   The column was added with DEFAULT 0 in Step 18, but any rows
--   that existed before that migration may still hold NULL.
UPDATE orders
SET    delivery_fee = 0
WHERE  delivery_fee IS NULL;

-- ── 2. Enforce NOT NULL + keep DEFAULT 0 ─────────────────────
ALTER TABLE orders
    ALTER COLUMN delivery_fee SET NOT NULL,
    ALTER COLUMN delivery_fee SET DEFAULT 0;

-- ── 3. Backfill delivered_at for legacy delivered/completed rows ──
--   rider/earnings.py now filters on delivered_at instead of
--   updated_at (which shifts on every status change).  Any order
--   that is in a terminal delivery state but missing delivered_at
--   gets updated_at as a safe approximation.
UPDATE orders
SET    delivered_at = updated_at
WHERE  delivered_at IS NULL
  AND  status IN ('delivered', 'completed');

-- ── 4. Index for fast rider earnings queries ──────────────────
CREATE INDEX IF NOT EXISTS idx_orders_rider_delivered
    ON orders (rider_id, delivered_at DESC)
    WHERE delivered_at IS NOT NULL;
