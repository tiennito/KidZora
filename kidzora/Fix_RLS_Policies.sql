-- Fix RLS Policies to remove infinite recursion
-- Run this in Supabase SQL Editor

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
DROP POLICY IF EXISTS "Admins can view all profiles" ON profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
DROP POLICY IF EXISTS "Admins can update all profiles" ON profiles;

-- Create new, simpler policies
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles" ON profiles
    FOR SELECT USING (
        auth.uid() IN (
            SELECT id FROM profiles 
            WHERE role = 'admin' AND is_approved = TRUE
        )
    );

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can update all profiles" ON profiles
    FOR UPDATE USING (
        auth.uid() IN (
            SELECT id FROM profiles 
            WHERE role = 'admin' AND is_approved = TRUE
        )
    );
