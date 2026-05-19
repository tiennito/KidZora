-- ============================================================
--  Step 28 – Payout Requests Table
--  Run this ONCE in the Supabase SQL editor.
-- ============================================================

CREATE TABLE IF NOT EXISTS payout_requests (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id      UUID        NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,

    amount         DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    method         TEXT        NOT NULL,   -- 'gcash' | 'bank_transfer'
    account_name   TEXT        NOT NULL,
    account_number TEXT        NOT NULL,

    status         TEXT        NOT NULL DEFAULT 'pending',
    -- 'pending' → waiting for admin action
    -- 'approved' → admin released the funds
    -- 'rejected' → admin declined

    admin_notes    TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payout_requests_seller_id ON payout_requests(seller_id);
CREATE INDEX IF NOT EXISTS idx_payout_requests_status    ON payout_requests(status);
CREATE INDEX IF NOT EXISTS idx_payout_requests_created   ON payout_requests(created_at DESC);

-- RLS – service role (app) handles all writes; no RLS needed for that path.
-- But add permissive read policies for the seller's own rows.
ALTER TABLE payout_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "payout_requests_seller_read" ON payout_requests;
CREATE POLICY "payout_requests_seller_read"
    ON payout_requests FOR SELECT
    USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()
        )
    );

-- Done.
