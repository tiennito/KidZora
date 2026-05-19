-- ─────────────────────────────────────────────────────────────────────────────
-- Step 33: seller_follows — buyer subscription to seller shops
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS seller_follows (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id   UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    seller_id  UUID NOT NULL REFERENCES sellers(id)    ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT seller_follows_unique UNIQUE (buyer_id, seller_id)
);

-- Index for fast follower-count queries and fan-out notifications
CREATE INDEX IF NOT EXISTS idx_seller_follows_seller_id ON seller_follows(seller_id);
CREATE INDEX IF NOT EXISTS idx_seller_follows_buyer_id  ON seller_follows(buyer_id);

-- ── Row-Level Security ───────────────────────────────────────────────────────
ALTER TABLE seller_follows ENABLE ROW LEVEL SECURITY;

-- Buyers read their own follow rows
CREATE POLICY sf_select ON seller_follows
    FOR SELECT USING (auth.uid() = buyer_id);

-- Buyers follow a seller (insert)
CREATE POLICY sf_insert ON seller_follows
    FOR INSERT WITH CHECK (auth.uid() = buyer_id);

-- Buyers unfollow (delete their own rows only)
CREATE POLICY sf_delete ON seller_follows
    FOR DELETE USING (auth.uid() = buyer_id);

-- Allow server-side (service role) reads for fan-out notifications
-- The service role bypasses RLS by default — no additional policy needed.
