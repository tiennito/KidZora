-- ============================================================
--  Step 22 – Product Reviews
--  Run this in the Supabase SQL editor ONCE.
-- ============================================================

-- 1. Reviews table
CREATE TABLE IF NOT EXISTS product_reviews (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id          UUID        NOT NULL REFERENCES products(id)  ON DELETE CASCADE,
    buyer_id            UUID        NOT NULL REFERENCES profiles(id)  ON DELETE CASCADE,
    order_id            UUID                 REFERENCES orders(id)    ON DELETE SET NULL,
    rating              INTEGER     NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title               TEXT,
    body                TEXT,
    is_verified_purchase BOOLEAN    NOT NULL DEFAULT FALSE,
    helpful_count       INTEGER     NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, buyer_id)   -- one review per buyer per product
);

-- 2. Index for fast lookup by product
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON product_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_buyer_id   ON product_reviews(buyer_id);

-- 3. Auto-update updated_at
CREATE OR REPLACE FUNCTION touch_product_reviews_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reviews_updated_at ON product_reviews;
CREATE TRIGGER trg_reviews_updated_at
    BEFORE UPDATE ON product_reviews
    FOR EACH ROW EXECUTE FUNCTION touch_product_reviews_updated_at();

-- 4. Helpful-votes table (tracks who voted to prevent double-voting)
CREATE TABLE IF NOT EXISTS review_helpful_votes (
    review_id UUID NOT NULL REFERENCES product_reviews(id) ON DELETE CASCADE,
    voter_id  UUID NOT NULL REFERENCES profiles(id)         ON DELETE CASCADE,
    PRIMARY KEY (review_id, voter_id)
);

-- 5. RLS policies
ALTER TABLE product_reviews        ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_helpful_votes   ENABLE ROW LEVEL SECURITY;

-- Drop existing policies first so the script is safe to re-run
DROP POLICY IF EXISTS "reviews_select_all"  ON product_reviews;
DROP POLICY IF EXISTS "reviews_insert_own"  ON product_reviews;
DROP POLICY IF EXISTS "reviews_update_own"  ON product_reviews;
DROP POLICY IF EXISTS "helpful_select_all"  ON review_helpful_votes;
DROP POLICY IF EXISTS "helpful_insert_own"  ON review_helpful_votes;
DROP POLICY IF EXISTS "helpful_delete_own"  ON review_helpful_votes;

-- Anyone (logged-in) can read reviews
CREATE POLICY "reviews_select_all"
    ON product_reviews FOR SELECT
    USING (auth.role() = 'authenticated');

-- Buyers can insert their own review
CREATE POLICY "reviews_insert_own"
    ON product_reviews FOR INSERT
    WITH CHECK (auth.uid() = buyer_id);

-- Buyers can update only their own review
CREATE POLICY "reviews_update_own"
    ON product_reviews FOR UPDATE
    USING (auth.uid() = buyer_id);

-- Anyone (logged-in) can read helpful votes
CREATE POLICY "helpful_select_all"
    ON review_helpful_votes FOR SELECT
    USING (auth.role() = 'authenticated');

-- Buyers can insert their own helpful vote
CREATE POLICY "helpful_insert_own"
    ON review_helpful_votes FOR INSERT
    WITH CHECK (auth.uid() = voter_id);

-- Buyers can remove their own helpful vote
CREATE POLICY "helpful_delete_own"
    ON review_helpful_votes FOR DELETE
    USING (auth.uid() = voter_id);

-- 6. Service-role / admin policies (bypass RLS via supabase_admin client — no extra policy needed)

-- Done
SELECT 'product_reviews table created' AS status;
