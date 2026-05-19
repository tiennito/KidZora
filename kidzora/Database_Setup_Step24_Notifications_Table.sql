-- =============================================================================
-- Step 24: Notifications Table
-- Real-time in-app notifications for all user roles.
-- =============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,          -- recipient (profiles.id)
    type        TEXT         NOT NULL,          -- see types below
    title       TEXT         NOT NULL,
    body        TEXT,
    is_read     BOOLEAN      NOT NULL DEFAULT FALSE,
    data        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Index for efficient per-user polling
CREATE INDEX IF NOT EXISTS idx_notif_user_read
    ON notifications (user_id, is_read, created_at DESC);

-- Row Level Security ─────────────────────────────────────────────────────────
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Service role (Flask backend) can do everything
CREATE POLICY "Service role full access" ON notifications
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- Notification type reference (informational only):
-- ─────────────────────────────────────────────────
--  order_placed          → seller (new order arrived)
--  order_confirmed       → buyer  (seller confirmed)
--  order_preparing       → buyer  (seller is preparing)
--  order_ready_pickup    → buyer  (ready for pickup by rider)
--  order_out_delivery    → buyer  (rider picked up)
--  order_delivered       → buyer  (rider delivered)
--  order_completed       → seller (buyer confirmed receipt)
--  order_cancelled       → buyer/seller (order cancelled)
--  cancel_request        → seller (buyer requests cancel)
--  cancel_approved       → buyer  (seller approved cancel)
--  cancel_rejected       → buyer  (seller rejected cancel)
--  message_received      → any    (new chat message)
--  return_submitted      → seller/admin (buyer filed return)
--  return_updated        → buyer  (status change on return)
-- =============================================================================
