-- ============================================================
-- Step 39: Proof of Delivery
-- Adds proof_of_delivery_url column to orders so riders can
-- attach a delivery photo when marking an order as delivered.
-- Run after Step 38.
-- ============================================================

-- 1. Add the column (idempotent)
ALTER TABLE public.orders
  ADD COLUMN IF NOT EXISTS proof_of_delivery_url TEXT;

COMMENT ON COLUMN public.orders.proof_of_delivery_url IS
  'Public URL of the proof-of-delivery photo uploaded by the rider.';

-- ============================================================
-- 2. Supabase Storage bucket — run once in the Supabase dashboard
--    (SQL Editor cannot create Storage buckets; use the Storage UI or
--     the Supabase JS client.  The settings below are for reference.)
--
--    Bucket name  : delivery-proofs
--    Public       : true   (buyers and admins need to view the photo)
--    Allowed MIME : image/jpeg, image/png, image/webp
--    Max file size: 10 MB
--
--    RLS policies to add after bucket creation:
--    ─────────────────────────────────────────
--    -- Riders can upload their own proof photos
--    CREATE POLICY "riders upload proof"
--      ON storage.objects FOR INSERT
--      WITH CHECK (
--        bucket_id = 'delivery-proofs'
--        AND auth.role() = 'authenticated'
--      );
--
--    -- Anyone authenticated can read delivery proofs
--    CREATE POLICY "authenticated read proof"
--      ON storage.objects FOR SELECT
--      USING (
--        bucket_id = 'delivery-proofs'
--        AND auth.role() = 'authenticated'
--      );
-- ============================================================
