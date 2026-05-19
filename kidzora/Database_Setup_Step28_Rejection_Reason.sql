-- Step 28: Add rejection_reason to profiles
-- Used for soft-rejecting riders so they can re-upload documents without re-registering.
-- Sellers are still hard-deleted on rejection (they must re-register).

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

COMMENT ON COLUMN profiles.rejection_reason IS
  'Set when admin soft-rejects a rider. Rider can re-upload documents; cleared on resubmission.';
