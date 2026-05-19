-- ============================================================
-- Step 21: Return & Refund Requests
-- Run in Supabase SQL Editor after Step 20.
-- ============================================================

-- return_requests table
-- Flow:
--   pending
--     → seller_approved  (seller agrees to refund/return)
--     → seller_rejected  (seller denies)
--         → escalated    (buyer escalates to admin)
--             → admin_approved  (admin sides with buyer → refund)
--             → admin_rejected  (admin sides with seller → no refund)

CREATE TABLE IF NOT EXISTS return_requests (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id         UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    buyer_id         UUID NOT NULL,
    seller_id        UUID NOT NULL,
    reason           TEXT NOT NULL,   -- e.g. 'wrong_item', 'damaged', 'defective', 'not_as_described', 'other'
    details          TEXT,
    refund_type      TEXT NOT NULL DEFAULT 'refund'  -- 'refund' or 'return_and_refund'
                         CHECK (refund_type IN ('refund','return_and_refund')),
    status           TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN (
                             'pending',
                             'seller_approved', 'seller_rejected',
                             'escalated',
                             'admin_approved', 'admin_rejected'
                         )),
    seller_response  TEXT,
    admin_response   TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only one active return request per order at a time
CREATE UNIQUE INDEX IF NOT EXISTS uniq_return_per_order
    ON return_requests(order_id)
    WHERE status NOT IN ('admin_rejected', 'seller_rejected');

-- Fast lookup for seller and admin dashboards
CREATE INDEX IF NOT EXISTS idx_returns_seller    ON return_requests(seller_id);
CREATE INDEX IF NOT EXISTS idx_returns_buyer     ON return_requests(buyer_id);
CREATE INDEX IF NOT EXISTS idx_returns_status    ON return_requests(status);
CREATE INDEX IF NOT EXISTS idx_returns_order     ON return_requests(order_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_return_requests_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_returns_updated_at ON return_requests;
CREATE TRIGGER trg_returns_updated_at
    BEFORE UPDATE ON return_requests
    FOR EACH ROW EXECUTE FUNCTION update_return_requests_updated_at();
