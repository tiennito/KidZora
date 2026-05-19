-- ============================================================
-- Step 7: Order Items Table
-- product_id / variant_id are SET NULL so that deleting a
-- product does NOT break existing order records.
-- product_name / variant_name snapshot the values at purchase.
-- Run after Step 6.
-- ============================================================

CREATE TABLE order_items (
    id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,

    -- SET NULL — product may be deleted but order history is kept
    product_id UUID REFERENCES products(id)         ON DELETE SET NULL,
    variant_id UUID REFERENCES product_variants(id)  ON DELETE SET NULL,

    -- Snapshots captured at purchase time (survive product deletion)
    product_name TEXT,
    variant_name TEXT,

    quantity INTEGER      NOT NULL CHECK (quantity > 0),
    price    DECIMAL(10,2) NOT NULL CHECK (price >= 0), -- unit price at purchase

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_order_items_order_id   ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

