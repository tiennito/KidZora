-- ============================================================
-- Step 41: Product Reports (Moderation Queue)
-- Allows buyers to report product listings for admin review.
-- ============================================================

CREATE TABLE IF NOT EXISTS product_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    details TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'actioned', 'dismissed')),
    action_taken TEXT CHECK (action_taken IN ('hidden', 'removed', 'dismissed')),
    admin_notes TEXT,
    reviewed_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_reports_status_created
    ON product_reports(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_reports_product_id
    ON product_reports(product_id);

CREATE INDEX IF NOT EXISTS idx_product_reports_reporter_id
    ON product_reports(reporter_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_reports_pending_per_buyer
    ON product_reports(product_id, reporter_id)
    WHERE status = 'pending';
