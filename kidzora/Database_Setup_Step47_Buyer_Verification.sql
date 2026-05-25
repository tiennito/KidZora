-- ============================================================
-- Step 47 - Buyer Identity Verification
-- Adds buyer valid-ID review fields and a private storage bucket.
-- ============================================================

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS valid_id_path TEXT,
ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'Approved',
ADD COLUMN IF NOT EXISTS verified_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

ALTER TABLE profiles
DROP CONSTRAINT IF EXISTS chk_profiles_verification_status;

ALTER TABLE profiles
ADD CONSTRAINT chk_profiles_verification_status
CHECK (verification_status IN ('Pending', 'Approved', 'Rejected'));

UPDATE profiles
SET verification_status = CASE
    WHEN role = 'buyer' AND COALESCE(is_approved, false) = false THEN 'Pending'
    WHEN verification_status IS NULL THEN 'Approved'
    ELSE verification_status
END;

CREATE INDEX IF NOT EXISTS idx_profiles_verification_status
ON profiles(verification_status);

CREATE INDEX IF NOT EXISTS idx_profiles_buyer_verification_pending
ON profiles(role, verification_status)
WHERE role = 'buyer';

INSERT INTO storage.buckets (id, name, public)
VALUES ('buyer-valid-ids', 'buyer-valid-ids', false)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Service role read buyer-valid-ids" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert buyer-valid-ids" ON storage.objects;

CREATE POLICY "Service role read buyer-valid-ids"
  ON storage.objects FOR SELECT TO service_role
  USING (bucket_id = 'buyer-valid-ids');

CREATE POLICY "Authenticated upsert buyer-valid-ids"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'buyer-valid-ids');
