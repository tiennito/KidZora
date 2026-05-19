-- ============================================================
-- Step 35 – Store Customization
-- Adds shop banner image and "About the Store" rich text to
-- the sellers table so sellers can personalise their storefront.
-- ============================================================

ALTER TABLE sellers
  ADD COLUMN IF NOT EXISTS shop_banner_url TEXT,
  ADD COLUMN IF NOT EXISTS about_store     TEXT;

COMMENT ON COLUMN sellers.shop_banner_url IS
  'Public URL of the wide banner image shown at the top of the seller store page.';
COMMENT ON COLUMN sellers.about_store IS
  '"About the Store" text (plain text or light markdown) displayed on the store page.';
