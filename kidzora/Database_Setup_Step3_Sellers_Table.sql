-- ============================================================
-- Step 3: Sellers Table
-- One row per approved seller. Business docs are on profiles.
-- Run after Step 2.
-- ============================================================

CREATE TABLE sellers (
    id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,

    shop_name        TEXT NOT NULL,
    shop_description TEXT,

    -- Payout details
    bank_account TEXT,
    bank_name    TEXT,

    -- Commission the platform takes (default 10%)
    commission_rate DECIMAL(5,2) DEFAULT 10.00,

    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sellers_user_id   ON sellers(user_id);
CREATE INDEX idx_sellers_is_active ON sellers(is_active);

