-- ============================================================
-- Step 43: Application Error Logs
-- Stores unhandled request exceptions for admin diagnostics.
-- ============================================================

CREATE TABLE IF NOT EXISTS app_error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level TEXT NOT NULL DEFAULT 'error',
    message TEXT NOT NULL,
    error_type TEXT,
    path TEXT,
    method TEXT,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_error_logs_created_at
    ON app_error_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_app_error_logs_level
    ON app_error_logs(level);
