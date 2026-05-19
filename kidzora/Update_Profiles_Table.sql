-- Add new columns to profiles table for buyer registration
-- Run this in Supabase SQL Editor

ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS address TEXT,
ADD COLUMN IF NOT EXISTS building_number TEXT,
ADD COLUMN IF NOT EXISTS street_name TEXT,
ADD COLUMN IF NOT EXISTS city TEXT,
ADD COLUMN IF NOT EXISTS postal_code TEXT,
ADD COLUMN IF NOT EXISTS country TEXT,
ADD COLUMN IF NOT EXISTS region TEXT,
ADD COLUMN IF NOT EXISTS province TEXT,
ADD COLUMN IF NOT EXISTS barangay TEXT,
ADD COLUMN IF NOT EXISTS newsletter BOOLEAN DEFAULT FALSE;

-- Add seller-specific columns
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS business_name TEXT,
ADD COLUMN IF NOT EXISTS business_type TEXT,
ADD COLUMN IF NOT EXISTS seller_id_type TEXT,
ADD COLUMN IF NOT EXISTS seller_id_number TEXT,
ADD COLUMN IF NOT EXISTS seller_id_file TEXT,
ADD COLUMN IF NOT EXISTS business_permit_file TEXT,
ADD COLUMN IF NOT EXISTS bir_file TEXT;

-- Update existing profiles to have default values
UPDATE profiles 
SET newsletter = FALSE 
WHERE newsletter IS NULL;
