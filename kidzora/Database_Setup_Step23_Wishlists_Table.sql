-- ── Step 23: Wishlists (Favorites) Table ─────────────────────────────────────
-- Stores products a buyer has favorited (saved for later).

CREATE TABLE IF NOT EXISTS wishlists (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id    UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    product_id  UUID        NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A buyer can only favorite a product once
    UNIQUE (buyer_id, product_id)
);

-- Index for fast per-buyer lookups
CREATE INDEX IF NOT EXISTS idx_wishlists_buyer_id ON wishlists(buyer_id);

-- ── Row Level Security ────────────────────────────────────────────────────────
ALTER TABLE wishlists ENABLE ROW LEVEL SECURITY;

-- Buyers can only see their own favorites
CREATE POLICY "Buyers view own wishlist"
    ON wishlists FOR SELECT
    USING (auth.uid() = buyer_id);

-- Buyers can add to their own wishlist
CREATE POLICY "Buyers insert own wishlist"
    ON wishlists FOR INSERT
    WITH CHECK (auth.uid() = buyer_id);

-- Buyers can remove from their own wishlist
CREATE POLICY "Buyers delete own wishlist"
    ON wishlists FOR DELETE
    USING (auth.uid() = buyer_id);
