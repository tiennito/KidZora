-- Authenticator-app two-factor authentication fields.
-- Run this in the Supabase SQL Editor before enabling KidZora TOTP 2FA.

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS two_factor_secret TEXT,
ADD COLUMN IF NOT EXISTS two_factor_confirmed_at TIMESTAMP WITH TIME ZONE;
