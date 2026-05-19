-- ============================================================
-- Step 26: Add avatar_url column to profiles table
-- ============================================================

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS avatar_url TEXT DEFAULT NULL;

COMMENT ON COLUMN public.profiles.avatar_url IS
  'URL path to the user profile / store photo used as avatar in chat notifications.';
