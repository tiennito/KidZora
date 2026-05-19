-- ============================================================
-- Database_Setup_Step16_Unban_Requests.sql
-- Adds ban_reason to profiles and creates the unban_requests
-- table used by the user appeal / admin review workflow.
-- ============================================================

-- 1. Add ban_reason column to profiles (stores why the user was banned)
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS ban_reason TEXT;

-- 2. Create unban_requests table
CREATE TABLE IF NOT EXISTS unban_requests (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    message      TEXT NOT NULL,
    file_url     TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'approved', 'rejected', 'superseded')),
    admin_notes  TEXT,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_unban_requests_user_id ON unban_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_unban_requests_status  ON unban_requests(status);

-- Ensure set_updated_at function exists (also defined in Step 12)
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-update updated_at
CREATE TRIGGER trg_unban_requests_updated_at
    BEFORE UPDATE ON unban_requests
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Row Level Security ────────────────────────────────────────────────────────
ALTER TABLE unban_requests ENABLE ROW LEVEL SECURITY;

-- Only admins can read all requests (backend uses service role key, bypasses RLS)
CREATE POLICY "Admins can manage unban requests"
    ON unban_requests FOR ALL
    USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
    ));

-- Users can read their own requests
CREATE POLICY "Users can read own unban requests"
    ON unban_requests FOR SELECT
    USING (auth.uid() = user_id);
