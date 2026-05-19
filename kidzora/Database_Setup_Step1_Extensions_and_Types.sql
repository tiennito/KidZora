-- ============================================================
-- Step 1: Extensions and Custom Types
-- Run this FIRST in Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── User / account types ──────────────────────────────────────
CREATE TYPE user_role       AS ENUM ('admin', 'seller', 'buyer', 'rider');

-- ── Order lifecycle ───────────────────────────────────────────
CREATE TYPE order_status    AS ENUM (
    'pending',
    'confirmed',
    'preparing',
    'ready_for_pickup',
    'out_for_delivery',
    'delivered',
    'cancelled'
);
CREATE TYPE payment_status  AS ENUM ('pending', 'paid', 'refunded');
CREATE TYPE payment_method  AS ENUM ('cash', 'gcash', 'paymaya', 'bank_transfer');

-- ── Financial ─────────────────────────────────────────────────
CREATE TYPE discount_type       AS ENUM ('percentage', 'fixed');
CREATE TYPE transaction_type    AS ENUM ('commission', 'payout', 'refund');
CREATE TYPE transaction_status  AS ENUM ('pending', 'completed', 'failed');

-- ── Misc ──────────────────────────────────────────────────────
CREATE TYPE report_type       AS ENUM ('sales', 'users', 'commissions', 'activity');
CREATE TYPE vehicle_type      AS ENUM ('motorcycle', 'bicycle', 'car');
CREATE TYPE product_condition AS ENUM ('new', 'like_new', 'good', 'fair');
CREATE TYPE message_type      AS ENUM ('text', 'image', 'file');
