-- ============================================================
-- Step 37 — Product SEO Fields
-- Adds slug, meta_title, meta_description to the products table
-- Run this in the Supabase SQL Editor
-- ============================================================

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS slug             TEXT,
  ADD COLUMN IF NOT EXISTS meta_title       TEXT,
  ADD COLUMN IF NOT EXISTS meta_description TEXT;

-- Unique, null-safe index: two products can both have NULL slug,
-- but no two products can share the same non-null slug value.
CREATE UNIQUE INDEX IF NOT EXISTS products_slug_unique
  ON products (slug)
  WHERE slug IS NOT NULL;

COMMENT ON COLUMN products.slug             IS 'SEO-friendly URL fragment, e.g. wooden-building-blocks-set';
COMMENT ON COLUMN products.meta_title       IS 'Custom <title> tag (max ~60 chars). Falls back to product name.';
COMMENT ON COLUMN products.meta_description IS 'Custom <meta description> (max ~155 chars). Falls back to product description.';
