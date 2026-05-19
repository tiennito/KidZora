-- ═══════════════════════════════════════════════════════════════════════════
-- Step 27 – Support Tickets (Buyer ↔ Admin Help Desk)
-- ═══════════════════════════════════════════════════════════════════════════
-- Run this in the Supabase SQL editor after all previous migration steps.

-- ─── support_tickets ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS support_tickets (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id    UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    subject     TEXT        NOT NULL,
    category    TEXT        NOT NULL DEFAULT 'general',
    status      TEXT        NOT NULL DEFAULT 'open',   -- open / in_progress / resolved / closed
    priority    TEXT        NOT NULL DEFAULT 'medium', -- low / medium / high / urgent
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── support_replies ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS support_replies (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id   UUID        NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_id   UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    content     TEXT        NOT NULL,
    is_admin    BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Indexes ──────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_support_tickets_buyer_id  ON support_tickets(buyer_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status    ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_updated   ON support_tickets(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_replies_ticket_id ON support_replies(ticket_id);

-- ─── Auto-update updated_at on support_tickets ────────────────────────────
CREATE OR REPLACE FUNCTION update_support_ticket_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE support_tickets SET updated_at = NOW() WHERE id = NEW.ticket_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_support_reply_update_ticket ON support_replies;
CREATE TRIGGER trg_support_reply_update_ticket
    AFTER INSERT ON support_replies
    FOR EACH ROW EXECUTE FUNCTION update_support_ticket_timestamp();

-- ─── Row Level Security ───────────────────────────────────────────────────
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_replies ENABLE ROW LEVEL SECURITY;

-- Service role (used by Flask backend) bypasses RLS — no policies needed.
-- If you also connect with the anon/user role, add policies here.
