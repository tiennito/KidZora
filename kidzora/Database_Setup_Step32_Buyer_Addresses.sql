-- ============================================================
-- Step 32: Saved Delivery Addresses for Buyers
-- ============================================================
-- Buyers can save multiple shipping addresses and pick one
-- at checkout. One address per buyer is flagged is_default.
-- ============================================================

CREATE TABLE IF NOT EXISTS buyer_addresses (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    buyer_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    label            TEXT NOT NULL DEFAULT 'Home',
    full_name        TEXT NOT NULL DEFAULT '',
    phone            TEXT NOT NULL DEFAULT '',
    region           TEXT NOT NULL DEFAULT '',
    province         TEXT NOT NULL DEFAULT '',
    city             TEXT NOT NULL DEFAULT '',
    barangay         TEXT NOT NULL DEFAULT '',
    street_name      TEXT NOT NULL DEFAULT '',
    building_number  TEXT NOT NULL DEFAULT '',
    postal_code      TEXT NOT NULL DEFAULT '',
    is_default       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_buyer_addresses_buyer
    ON buyer_addresses (buyer_id, created_at);

-- ── updated_at trigger ────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION _trg_buyer_addresses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_buyer_addresses_updated_at ON buyer_addresses;
CREATE TRIGGER trg_buyer_addresses_updated_at
    BEFORE UPDATE ON buyer_addresses
    FOR EACH ROW EXECUTE FUNCTION _trg_buyer_addresses_updated_at();

-- ── Row Level Security ────────────────────────────────────────────────────────
ALTER TABLE buyer_addresses ENABLE ROW LEVEL SECURITY;

-- Buyers can only see their own addresses
CREATE POLICY ba_select ON buyer_addresses
    FOR SELECT USING (buyer_id = auth.uid());

-- Buyers can only insert their own addresses
CREATE POLICY ba_insert ON buyer_addresses
    FOR INSERT WITH CHECK (buyer_id = auth.uid());

-- Buyers can only update their own addresses
CREATE POLICY ba_update ON buyer_addresses
    FOR UPDATE USING (buyer_id = auth.uid());

-- Buyers can only delete their own addresses
CREATE POLICY ba_delete ON buyer_addresses
    FOR DELETE USING (buyer_id = auth.uid());

-- Admin service role bypasses RLS (uses supabase_admin client)
