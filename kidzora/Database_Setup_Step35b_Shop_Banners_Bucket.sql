-- ============================================================
-- Step 35b – Create shop-banners Storage Bucket
-- Public bucket for seller shop banner images.
-- Run this in Supabase SQL Editor.
-- ============================================================

-- Create the bucket (public = buyers can view banners without auth)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'shop-banners',
  'shop-banners',
  TRUE,
  5242880,  -- 5 MB max per banner
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO NOTHING;

-- RLS: Anyone can read (public bucket)
CREATE POLICY "Public read shop banners"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'shop-banners');

-- RLS: Authenticated sellers can upload/update their own banner
CREATE POLICY "Sellers can upload their banner"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (bucket_id = 'shop-banners');

CREATE POLICY "Sellers can update their banner"
  ON storage.objects FOR UPDATE
  TO authenticated
  USING (bucket_id = 'shop-banners');
