-- ============================================================
--  Step 40 – Rider Payout Requests Table
--  Run this ONCE in the Supabase SQL editor.
-- ============================================================

-- Add bank details columns to riders (for saved account convenience)
ALTER TABLE riders
    ADD COLUMN IF NOT EXISTS bank_name    TEXT,
    ADD COLUMN IF NOT EXISTS bank_account TEXT;

CREATE TABLE IF NOT EXISTS rider_payout_requests (
    id             UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    rider_id       UUID          NOT NULL REFERENCES riders(id) ON DELETE CASCADE,

    amount         DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    method         TEXT          NOT NULL,   -- 'gcash' | 'bank_transfer'
    account_name   TEXT          NOT NULL,
    account_number TEXT          NOT NULL,

    status         TEXT          NOT NULL DEFAULT 'pending',
    -- 'pending'  → waiting for admin action
    -- 'approved' → admin released the funds
    -- 'rejected' → admin declined

    admin_notes    TEXT,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    processed_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rider_payout_requests_rider_id ON rider_payout_requests(rider_id);
CREATE INDEX IF NOT EXISTS idx_rider_payout_requests_status   ON rider_payout_requests(status);
CREATE INDEX IF NOT EXISTS idx_rider_payout_requests_created  ON rider_payout_requests(created_at DESC);

-- RLS – service role handles all writes; add permissive read for the rider's own rows.
ALTER TABLE rider_payout_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "rider_payout_requests_rider_read" ON rider_payout_requests;
CREATE POLICY "rider_payout_requests_rider_read"
    ON rider_payout_requests FOR SELECT
    USING (
        rider_id IN (
            SELECT id FROM riders WHERE user_id = auth.uid()
        )
    );
