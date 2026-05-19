-- ============================================================
-- Step 18: Seller Coupons + Delivery Fee Support
-- Run in Supabase SQL Editor AFTER all previous steps.
-- ============================================================

-- ── 1. Add 'free_delivery' to discount_type enum ─────────────
ALTER TYPE discount_type ADD VALUE IF NOT EXISTS 'free_delivery';

-- ── 2. Add delivery_fee + seller_coupon_id to orders ─────────
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS delivery_fee       DECIMAL(10,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS seller_coupon_id   UUID;

-- ── 3. Seller Coupons Table ───────────────────────────────────
CREATE TABLE IF NOT EXISTS seller_coupons (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id   UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,

    code        TEXT NOT NULL,
    description TEXT,

    -- 'percentage', 'fixed', or 'free_delivery'
    discount_type   TEXT NOT NULL CHECK (discount_type IN ('percentage', 'fixed', 'free_delivery')),
    discount_value  DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (discount_value >= 0),

    min_order_amount    DECIMAL(10,2) DEFAULT 0,
    max_discount_amount DECIMAL(10,2),

    usage_limit  INTEGER,
    usage_count  INTEGER DEFAULT 0,

    is_active   BOOLEAN DEFAULT TRUE,
    expires_at  TIMESTAMP WITH TIME ZONE,

    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(seller_id, code)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_seller_coupons_seller_id ON seller_coupons(seller_id);
CREATE INDEX IF NOT EXISTS idx_seller_coupons_code      ON seller_coupons(code);
CREATE INDEX IF NOT EXISTS idx_seller_coupons_is_active ON seller_coupons(is_active);

-- ── 4. FK: orders → seller_coupons ───────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'orders_seller_coupon_id_fkey'
    ) THEN
        ALTER TABLE orders
            ADD CONSTRAINT orders_seller_coupon_id_fkey
            FOREIGN KEY (seller_coupon_id) REFERENCES seller_coupons(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ── 5. RLS: sellers manage their own coupons ─────────────────
ALTER TABLE seller_coupons ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (used by the Flask backend)
CREATE POLICY "service_role_all_seller_coupons"
    ON seller_coupons FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
