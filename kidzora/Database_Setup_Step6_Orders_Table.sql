-- ============================================================
-- Step 6: Orders Table
-- buyer_id / seller_id are SET NULL (not CASCADE) so that
-- order history is preserved when accounts are deleted.
-- Run after Step 5.
-- ============================================================

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- SET NULL so orders survive account deletion
    buyer_id  UUID REFERENCES profiles(id) ON DELETE SET NULL,
    seller_id UUID REFERENCES sellers(id)  ON DELETE SET NULL,
    rider_id  UUID REFERENCES riders(id)   ON DELETE SET NULL,

    total_amount     DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    commission       DECIMAL(10,2) NOT NULL DEFAULT 0,
    seller_earnings  DECIMAL(10,2) NOT NULL DEFAULT 0,
    delivery_address JSONB NOT NULL,

    status          order_status   DEFAULT 'pending',
    payment_status  payment_status DEFAULT 'pending',
    payment_method  payment_method,

    -- Optional coupon applied at checkout
    coupon_id       UUID REFERENCES coupons(id) ON DELETE SET NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,

    notes TEXT,  -- buyer notes / special instructions

    rider_assigned_at TIMESTAMP WITH TIME ZONE,
    delivered_at      TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_orders_buyer_id   ON orders(buyer_id);
CREATE INDEX idx_orders_seller_id  ON orders(seller_id);
CREATE INDEX idx_orders_rider_id   ON orders(rider_id);
CREATE INDEX idx_orders_status     ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

