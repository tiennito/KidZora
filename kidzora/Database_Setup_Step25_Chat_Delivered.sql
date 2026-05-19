-- Add is_delivered column to messages table
-- Run this once in your Supabase SQL editor

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS is_delivered boolean NOT NULL DEFAULT false;
