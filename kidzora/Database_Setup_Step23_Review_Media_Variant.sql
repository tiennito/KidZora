-- ============================================================
--  Step 23 – Product Reviews: add variant + media columns
--  Run this ONCE in the Supabase SQL editor.
-- ============================================================

-- 1. Add variant columns (nullable – old reviews stay intact)
ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS variant_id   UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS variant_name TEXT;

-- 2. Add media storage column (array of public URLs / local paths)
ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS media_urls JSONB NOT NULL DEFAULT '[]'::jsonb;

-- 3. Index for variant lookups
CREATE INDEX IF NOT EXISTS idx_reviews_variant_id ON product_reviews(variant_id);

-- Done.
