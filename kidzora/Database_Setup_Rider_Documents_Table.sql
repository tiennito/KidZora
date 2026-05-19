-- Add document URL columns directly to the riders table
-- Run this in the Supabase SQL Editor

ALTER TABLE riders
    ADD COLUMN IF NOT EXISTS licensed_id_url                 TEXT,
    ADD COLUMN IF NOT EXISTS original_receipt_url            TEXT,
    ADD COLUMN IF NOT EXISTS certificate_of_registration_url TEXT;

-- Drop the separate rider_documents table if it was already created
DROP TABLE IF EXISTS rider_documents;
