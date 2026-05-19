-- ============================================================
-- Step 16: Product Variants Table
-- Run this in Supabase SQL Editor
-- ============================================================

-- Create product_variants table
CREATE TABLE IF NOT EXISTS product_variants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,              -- e.g. "Red", "Large", "Blue / XL"
    image_url       TEXT,                       -- variant-specific image (optional)
    price_modifier  DECIMAL(10,2) DEFAULT 0,   -- price offset from base price (+ or -)
    stock_quantity  INT DEFAULT 0,
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookup by product
CREATE INDEX IF NOT EXISTS idx_product_variants_product_id
    ON product_variants (product_id);

-- Enable RLS
ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;

-- Anyone can read variants of active products
CREATE POLICY "public_read_variants"
    ON product_variants FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM products
            WHERE products.id = product_variants.product_id
              AND products.is_active = TRUE
        )
    );

-- Sellers can manage their own product variants
CREATE POLICY "seller_manage_variants"
    ON product_variants FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM products p
            JOIN sellers s ON s.id = p.seller_id
            WHERE p.id = product_variants.product_id
              AND s.user_id = auth.uid()
        )
    );
