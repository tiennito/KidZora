-- ============================================================
--  Step 27 – Product Reviews: add seller reply columns
--  Run this ONCE in the Supabase SQL editor.
-- ============================================================

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS seller_reply      TEXT,
    ADD COLUMN IF NOT EXISTS seller_reply_at   TIMESTAMPTZ;

-- Allow sellers to update only their reply columns (via service role or RLS policy)
-- The app uses supabase_admin (service role) so no RLS change is strictly required,
-- but adding a policy makes it explicit.

DROP POLICY IF EXISTS "reviews_seller_reply" ON product_reviews;

CREATE POLICY "reviews_seller_reply"
    ON product_reviews
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM products p
            JOIN sellers s ON s.id = p.seller_id
            WHERE p.id = product_reviews.product_id
            AND s.user_id = auth.uid()
        )
    )
    WITH CHECK (TRUE);

-- Done.
