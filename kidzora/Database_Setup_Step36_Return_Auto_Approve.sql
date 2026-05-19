-- ============================================================
-- Step 36 – Return Auto-Approve Days Setting
-- Seeds the return_auto_approve_days key into platform_settings.
-- Requires Step 34 (platform_settings table) to already exist.
-- Run in Supabase SQL Editor.
-- ============================================================

-- Default: 5 days. Admin can change via admin UI anytime.
INSERT INTO platform_settings (key, value)
  VALUES ('return_auto_approve_days', '5')
  ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE platform_settings IS
  'Admin-configurable key/value runtime settings. Changes take effect immediately without server restart.';
