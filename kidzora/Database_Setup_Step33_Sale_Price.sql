-- ============================================================
-- Step 33 – Sale / Promotional Price
-- Adds optional sale_price + date-range scheduling to products.
-- ============================================================

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS sale_price      NUMERIC(12,4),
  ADD COLUMN IF NOT EXISTS sale_starts_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS sale_ends_at    TIMESTAMPTZ;

-- Index: fast queries for currently-active sales
CREATE INDEX IF NOT EXISTS idx_products_active_sale
  ON products (sale_ends_at)
  WHERE sale_price IS NOT NULL AND is_active = TRUE;

COMMENT ON COLUMN products.sale_price     IS 'Promotional price; NULL means no sale. Must be < price.';
COMMENT ON COLUMN products.sale_starts_at IS 'Sale start (UTC). NULL = starts immediately when sale_price is set.';
COMMENT ON COLUMN products.sale_ends_at   IS 'Sale end (UTC). NULL = no expiry.';
