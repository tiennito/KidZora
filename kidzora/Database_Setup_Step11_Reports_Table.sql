-- ============================================================
-- Step 11: Reports Table
-- Admin-generated report snapshots (sales, users, etc.).
-- Run after Step 10.
-- ============================================================

CREATE TABLE reports (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type report_type NOT NULL,  -- 'sales','users','commissions','activity'
    title       TEXT NOT NULL,
    description TEXT,

    parameters JSONB,  -- filter criteria used to generate the report
    data       JSONB,  -- serialised report rows / summary

    generated_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    start_date   TIMESTAMP WITH TIME ZONE,
    end_date     TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_reports_type       ON reports(report_type);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
