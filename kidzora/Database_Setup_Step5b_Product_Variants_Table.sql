-- ============================================================
-- Step 5b: Product Variants Table
-- Optional per-product size/colour/etc. variants.
-- When variants exist, stock_quantity on each variant is the
-- source of truth; products.stock_quantity = their sum.
-- Run after Step 5 (products).
-- ============================================================

CREATE TABLE product_variants (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    name           TEXT NOT NULL,           -- e.g. "Red / Small", "Size M"
    image_url      TEXT,                    -- optional variant-specific image
    price_modifier DECIMAL(10,2) DEFAULT 0, -- added to products.price (can be negative)
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    sort_order     INTEGER DEFAULT 0,       -- display order within the product

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX idx_product_variants_sort_order  ON product_variants(product_id, sort_order);
