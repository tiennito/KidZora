-- Database_Setup_Step45_General_Images_Bucket.sql
-- Sets up a general-purpose "images" bucket for static/general uploads
-- Run this after creating the bucket in Supabase Storage dashboard

-- ── Create the general images bucket (if not exists) ──────────────────
INSERT INTO storage.buckets (id, name, public, created_at, updated_at)
VALUES ('images', 'images', true, now(), now())
ON CONFLICT (id) DO NOTHING;

-- ── Drop existing policies ────────────────────────────────────────────
DROP POLICY IF EXISTS "Public read images"           ON storage.objects;
DROP POLICY IF EXISTS "Authenticated upsert images"  ON storage.objects;
DROP POLICY IF EXISTS "Authenticated update images"  ON storage.objects;
DROP POLICY IF EXISTS "Authenticated delete images"  ON storage.objects;

-- ── Public read access ────────────────────────────────────────────────
CREATE POLICY "Public read images"
  ON storage.objects
  FOR SELECT USING (bucket_id = 'images');

-- ── Authenticated users can upload ────────────────────────────────────
CREATE POLICY "Authenticated upsert images"
  ON storage.objects
  FOR INSERT
  WITH CHECK (bucket_id = 'images' AND auth.role() = 'authenticated');

-- ── Authenticated users can update their own uploads ──────────────────
CREATE POLICY "Authenticated update images"
  ON storage.objects
  FOR UPDATE USING (bucket_id = 'images' AND auth.role() = 'authenticated');

-- ── Authenticated users can delete their own uploads ───────────────────
CREATE POLICY "Authenticated delete images"
  ON storage.objects
  FOR DELETE USING (bucket_id = 'images' AND auth.role() = 'authenticated');
