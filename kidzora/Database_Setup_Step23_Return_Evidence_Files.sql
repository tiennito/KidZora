-- ============================================================
-- Step 23: Add evidence_files column to return_requests
-- Run in Supabase SQL Editor.
-- Stores a JSON array of file paths (images & videos) that
-- the buyer attached when submitting a return/refund request.
-- ============================================================

ALTER TABLE return_requests
    ADD COLUMN IF NOT EXISTS evidence_files JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN return_requests.evidence_files IS
    'JSON array of local file paths for buyer-uploaded evidence (images/videos).';
