-- ============================================================
-- Step 27 — Supabase Storage Buckets
-- Run this in the Supabase SQL Editor (or Dashboard > Storage).
-- ============================================================

-- 1. Create buckets
--    public = true  → files are accessible without authentication
-- ============================================================

INSERT INTO storage.buckets (id, name, public)
VALUES
  ('product-images',   'product-images',   true),
  ('avatars',          'avatars',           true),
  ('return-evidence',  'return-evidence',   true),
  ('review-media',     'review-media',      true),
  -- Private buckets — sensitive ID / legal documents
  ('seller-documents', 'seller-documents',  false),
  ('rider-documents',  'rider-documents',   false),
  ('appeals',          'appeals',           false)
ON CONFLICT (id) DO NOTHING;


-- 2. RLS policies — allow anyone to read, and authenticated
--    users (or service-role uploads from Flask) to insert/update.
-- ============================================================

-- ── product-images ──────────────────────────────────────────
DROP POLICY IF EXISTS "Public read product-images"           ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert product-images"  ON storage.objects;
DROP POLICY IF EXISTS "Authenticated update product-images"  ON storage.objects;

CREATE POLICY "Public read product-images"
  ON storage.objects FOR SELECT TO public
  USING (bucket_id = 'product-images');

CREATE POLICY "Authenticated upsert product-images"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'product-images');

CREATE POLICY "Authenticated update product-images"
  ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'product-images');

-- ── avatars ──────────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read avatars"          ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert avatars" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated update avatars" ON storage.objects;

CREATE POLICY "Public read avatars"
  ON storage.objects FOR SELECT TO public
  USING (bucket_id = 'avatars');

CREATE POLICY "Authenticated upsert avatars"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'avatars');

CREATE POLICY "Authenticated update avatars"
  ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'avatars');

-- ── return-evidence ──────────────────────────────────────────
DROP POLICY IF EXISTS "Public read return-evidence"          ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert return-evidence" ON storage.objects;

CREATE POLICY "Public read return-evidence"
  ON storage.objects FOR SELECT TO public
  USING (bucket_id = 'return-evidence');

CREATE POLICY "Authenticated upsert return-evidence"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'return-evidence');

-- ── review-media ─────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read review-media"          ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert review-media" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated update review-media" ON storage.objects;

CREATE POLICY "Public read review-media"
  ON storage.objects FOR SELECT TO public
  USING (bucket_id = 'review-media');

CREATE POLICY "Authenticated upsert review-media"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'review-media');

CREATE POLICY "Authenticated update review-media"
  ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'review-media');


-- ── seller-documents (PRIVATE — admin only) ──────────────────
DROP POLICY IF EXISTS "Service role read seller-documents"   ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert seller-documents" ON storage.objects;

CREATE POLICY "Service role read seller-documents"
  ON storage.objects FOR SELECT TO service_role
  USING (bucket_id = 'seller-documents');

CREATE POLICY "Authenticated upsert seller-documents"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'seller-documents');

-- ── rider-documents (PRIVATE — admin only) ───────────────────
DROP POLICY IF EXISTS "Service role read rider-documents"    ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert rider-documents" ON storage.objects;

CREATE POLICY "Service role read rider-documents"
  ON storage.objects FOR SELECT TO service_role
  USING (bucket_id = 'rider-documents');

CREATE POLICY "Authenticated upsert rider-documents"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'rider-documents');

-- ── appeals (PRIVATE — admin only) ───────────────────────────
DROP POLICY IF EXISTS "Service role read appeals"   ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert appeals" ON storage.objects;

CREATE POLICY "Service role read appeals"
  ON storage.objects FOR SELECT TO service_role
  USING (bucket_id = 'appeals');

CREATE POLICY "Authenticated upsert appeals"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'appeals');
