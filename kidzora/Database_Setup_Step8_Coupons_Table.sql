-- ============================================================
-- Step 8: Coupons Table
-- Admin-created discount codes applied at checkout.
-- Run after Step 7.
-- ============================================================

CREATE TABLE coupons (
    id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT UNIQUE NOT NULL,

    description   TEXT,
    discount_type  discount_type NOT NULL,   -- 'percentage' or 'fixed'
    discount_value DECIMAL(10,2) NOT NULL CHECK (discount_value > 0),

    min_order_amount    DECIMAL(10,2) DEFAULT 0,
    max_discount_amount DECIMAL(10,2),       -- cap for percentage discounts

    usage_limit INTEGER,                     -- NULL = unlimited
    usage_count INTEGER DEFAULT 0,

    applicable_sellers UUID[],               -- empty = valid for all sellers

    is_active  BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_coupons_code      ON coupons(code);
CREATE INDEX idx_coupons_is_active ON coupons(is_active);
