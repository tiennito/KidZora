-- ============================================================
-- Step 10: Transactions Table
-- Financial audit log. seller_id is SET NULL (not CASCADE) so
-- financial records survive seller account deletion.
-- Run after Step 9.
-- ============================================================

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    order_id  UUID REFERENCES orders(id)  ON DELETE SET NULL,
    seller_id UUID REFERENCES sellers(id) ON DELETE SET NULL, -- audit trail preserved

    amount           DECIMAL(10,2) NOT NULL,
    commission_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    seller_earnings   DECIMAL(10,2) NOT NULL DEFAULT 0,

    type   transaction_type   NOT NULL,   -- 'commission','payout','refund'
    status transaction_status DEFAULT 'pending',

    payout_reference TEXT,  -- external reference (GCash ref, bank ref, etc.)
    notes            TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_transactions_seller_id  ON transactions(seller_id);
CREATE INDEX idx_transactions_order_id   ON transactions(order_id);
CREATE INDEX idx_transactions_type       ON transactions(type);
CREATE INDEX idx_transactions_status     ON transactions(status);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);

