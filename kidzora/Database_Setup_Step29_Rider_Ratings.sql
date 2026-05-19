-- ============================================================
--  Step 29 – Rider Ratings Table
--  Run this ONCE in the Supabase SQL editor.
-- ============================================================

CREATE TABLE IF NOT EXISTS rider_ratings (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id    UUID        NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    rider_id    UUID        NOT NULL REFERENCES riders(id)  ON DELETE CASCADE,
    buyer_id    UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    rating      INTEGER     NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback    TEXT,

    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rider_ratings_rider_id ON rider_ratings(rider_id);
CREATE INDEX IF NOT EXISTS idx_rider_ratings_buyer_id ON rider_ratings(buyer_id);

-- RLS
ALTER TABLE rider_ratings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "rider_ratings_select_own" ON rider_ratings;
CREATE POLICY "rider_ratings_select_own"
    ON rider_ratings FOR SELECT
    USING (
        buyer_id = auth.uid()
        OR rider_id IN (SELECT id FROM riders WHERE user_id = auth.uid())
    );

-- Done.
