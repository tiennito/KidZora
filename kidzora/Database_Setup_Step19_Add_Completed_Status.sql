-- ============================================================
-- Step 19: Re-add 'completed' to order_status enum
-- Run in Supabase SQL Editor.
-- 'completed' = buyer has confirmed they received the order.
-- ============================================================
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'completed';
