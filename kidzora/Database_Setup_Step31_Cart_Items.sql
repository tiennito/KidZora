-- ============================================================
-- Step 31: Cart Items — persistent cart per buyer
-- Run in Supabase SQL Editor AFTER all previous steps.
-- ============================================================

-- ── 1. Cart items table ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS cart_items (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    buyer_id    UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- Composite key mirroring the session cart key:  '{product_id}_{variant_id|""}'
    cart_key    TEXT NOT NULL,

    product_id  UUID NOT NULL,
    variant_id  UUID,                         -- NULL when no variant selected

    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),

    -- Snapshotted display fields (used when product data is unavailable offline)
    name        TEXT NOT NULL,
    price       DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    image_url   TEXT,
    seller_id   UUID,

    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One row per buyer–item combination
    UNIQUE (buyer_id, cart_key)
);

-- ── 2. Indexes ────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cart_items_buyer_id ON cart_items(buyer_id);

-- ── 3. Auto-update updated_at ─────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'set_cart_items_updated_at'
    ) THEN
        CREATE TRIGGER set_cart_items_updated_at
            BEFORE UPDATE ON cart_items
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ── 4. Row Level Security ─────────────────────────────────────
ALTER TABLE cart_items ENABLE ROW LEVEL SECURITY;

-- Buyers can only access their own cart items
CREATE POLICY "cart_items_buyer_select" ON cart_items
    FOR SELECT USING (buyer_id = auth.uid());

CREATE POLICY "cart_items_buyer_insert" ON cart_items
    FOR INSERT WITH CHECK (buyer_id = auth.uid());

CREATE POLICY "cart_items_buyer_update" ON cart_items
    FOR UPDATE USING (buyer_id = auth.uid());

CREATE POLICY "cart_items_buyer_delete" ON cart_items
    FOR DELETE USING (buyer_id = auth.uid());
