-- ============================================================
-- Step 34 – Platform Settings Table
-- Stores admin-configurable runtime settings (commission rate,
-- payout frequency, etc.) that take effect without restarting.
-- ============================================================

CREATE TABLE IF NOT EXISTS platform_settings (
  key        TEXT        PRIMARY KEY,
  value      TEXT        NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed defaults (do not overwrite if already customised)
INSERT INTO platform_settings (key, value)
  VALUES ('commission_rate',  '0.05')
  ON CONFLICT (key) DO NOTHING;

INSERT INTO platform_settings (key, value)
  VALUES ('payout_frequency', 'weekly')
  ON CONFLICT (key) DO NOTHING;

-- Auto-update updated_at on change
CREATE OR REPLACE FUNCTION _platform_settings_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_platform_settings_updated_at ON platform_settings;
CREATE TRIGGER trg_platform_settings_updated_at
  BEFORE UPDATE ON platform_settings
  FOR EACH ROW EXECUTE FUNCTION _platform_settings_set_updated_at();

COMMENT ON TABLE platform_settings IS
  'Admin-configurable key/value runtime settings. Changes take effect immediately without server restart.';
