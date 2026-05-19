-- ============================================================
-- Step 5: Products Table
-- One row per listing. Variants stored in product_variants.
-- Deleting a seller cascades and removes all their products.
-- Run after Step 4.
-- ============================================================

CREATE TABLE products (
    id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,

    name        TEXT NOT NULL,
    description TEXT,
    price       DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    category    TEXT NOT NULL,  -- 'Toys','Clothing','Books','Educational','Safety','Accessories','Other'
    age_group   TEXT,           -- '0-2 years','3-5 years','6-8 years','9-12 years','13+ years'
    condition   product_condition DEFAULT 'new',

    -- stock_quantity mirrors the sum of all variant stocks when variants exist,
    -- otherwise it is managed directly.
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),

    images    TEXT[],           -- Array of image URLs (/static/uploads/products/...)
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_products_seller_id  ON products(seller_id);
CREATE INDEX idx_products_category   ON products(category);
CREATE INDEX idx_products_is_active  ON products(is_active);
CREATE INDEX idx_products_created_at ON products(created_at DESC);

