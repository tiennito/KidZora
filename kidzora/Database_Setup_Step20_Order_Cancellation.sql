-- ============================================================
-- Step 20: Order Cancellation Support
-- Run in Supabase SQL Editor after Step 19.
-- ============================================================

-- Add cancellation columns to orders table
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS cancel_requested  BOOLEAN   DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS cancel_reason     TEXT,
    ADD COLUMN IF NOT EXISTS cancel_status     TEXT      CHECK (cancel_status IN ('pending_review','approved','rejected')),
    ADD COLUMN IF NOT EXISTS cancel_response   TEXT;

-- Index for fast admin/seller queries on pending cancel requests
CREATE INDEX IF NOT EXISTS idx_orders_cancel_requested ON orders(cancel_requested) WHERE cancel_requested = TRUE;
