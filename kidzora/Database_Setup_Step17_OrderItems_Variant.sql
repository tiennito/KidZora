-- ============================================================
-- Step 17: Add variant_id column to order_items
-- Run this in Supabase SQL Editor
-- ============================================================

ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_order_items_variant_id
    ON order_items (variant_id);
