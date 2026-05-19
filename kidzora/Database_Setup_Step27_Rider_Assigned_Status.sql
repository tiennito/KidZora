-- ============================================================
-- Step 27: Add 'rider_assigned' to order_status enum
-- Run in Supabase SQL Editor.
-- 'rider_assigned' = a rider has accepted the order but has
--                    not yet physically picked it up from the
--                    seller.  The rider clicks "I've Picked Up
--                    the Order" to advance it to 'out_for_delivery'.
-- ============================================================
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'rider_assigned';
