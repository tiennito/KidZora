-- Simple RLS Fix - Disable RLS temporarily for testing
-- Run this in Supabase SQL Editor

-- Option 1: Disable RLS completely (for testing)
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;

-- Option 2: If you want RLS but simpler, use these policies instead:
-- DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
-- DROP POLICY IF EXISTS "Admins can view all profiles" ON profiles;
-- DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
-- DROP POLICY IF EXISTS "Admins can update all profiles" ON profiles;

-- Create very simple policies
-- CREATE POLICY "Enable all access for authenticated users" ON profiles
--     FOR ALL USING (auth.uid() IS NOT NULL);

-- Try Option 1 first (disable RLS completely)
