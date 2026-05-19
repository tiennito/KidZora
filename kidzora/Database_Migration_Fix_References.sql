-- ============================================================
-- MIGRATION: Fix all table references for existing database
-- Run this in Supabase SQL Editor (runs safely on existing data)
-- ============================================================

-- ── 1. PROFILES: add all missing columns ────────────────────
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS building_number TEXT,
    ADD COLUMN IF NOT EXISTS street_name TEXT,
    ADD COLUMN IF NOT EXISTS barangay TEXT,
    ADD COLUMN IF NOT EXISTS city TEXT,
    ADD COLUMN IF NOT EXISTS province TEXT,
    ADD COLUMN IF NOT EXISTS region TEXT,
    ADD COLUMN IF NOT EXISTS postal_code TEXT,
    ADD COLUMN IF NOT EXISTS country TEXT DEFAULT 'Philippines',
    ADD COLUMN IF NOT EXISTS business_name TEXT,
    ADD COLUMN IF NOT EXISTS business_type TEXT,
    ADD COLUMN IF NOT EXISTS seller_id_type TEXT,
    ADD COLUMN IF NOT EXISTS seller_id_number TEXT,
    ADD COLUMN IF NOT EXISTS seller_id_file TEXT,
    ADD COLUMN IF NOT EXISTS business_permit_file TEXT,
    ADD COLUMN IF NOT EXISTS bir_file TEXT,
    ADD COLUMN IF NOT EXISTS newsletter BOOLEAN DEFAULT FALSE;

-- ── 2. SELLERS: drop legacy columns, add missing ones ────────
ALTER TABLE sellers
    DROP COLUMN IF EXISTS business_permit,
    DROP COLUMN IF EXISTS valid_id;

ALTER TABLE sellers
    ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5,2) DEFAULT 10.00,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Ensure unique constraint on user_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'sellers_user_id_key'
    ) THEN
        ALTER TABLE sellers ADD CONSTRAINT sellers_user_id_key UNIQUE (user_id);
    END IF;
END $$;

-- ── 3. RIDERS: add document URL columns (may already exist) ──
ALTER TABLE riders
    ADD COLUMN IF NOT EXISTS licensed_id_url TEXT,
    ADD COLUMN IF NOT EXISTS original_receipt_url TEXT,
    ADD COLUMN IF NOT EXISTS certificate_of_registration_url TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Drop legacy columns
ALTER TABLE riders
    DROP COLUMN IF EXISTS driver_license,
    DROP COLUMN IF EXISTS license_expiry;

-- Ensure unique constraint on user_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'riders_user_id_key'
    ) THEN
        ALTER TABLE riders ADD CONSTRAINT riders_user_id_key UNIQUE (user_id);
    END IF;
END $$;

-- ── 4. PRODUCTS: add check constraints ───────────────────────
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC);

-- ── 5. ORDERS: change ON DELETE CASCADE → SET NULL for buyer/seller
--    (preserves order history when accounts are deleted)
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_buyer_id_fkey;
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_seller_id_fkey;

ALTER TABLE orders
    ADD CONSTRAINT orders_buyer_id_fkey
        FOREIGN KEY (buyer_id) REFERENCES profiles(id) ON DELETE SET NULL;

ALTER TABLE orders
    ADD CONSTRAINT orders_seller_id_fkey
        FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE SET NULL;

-- Make buyer_id and seller_id nullable (needed for SET NULL)
ALTER TABLE orders ALTER COLUMN buyer_id DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN seller_id DROP NOT NULL;

-- Add optional columns
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS coupon_id UUID REFERENCES coupons(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10,2) DEFAULT 0;

-- ── 6. ORDER_ITEMS: change RESTRICT → SET NULL on product_id ─
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS order_items_product_id_fkey;

ALTER TABLE order_items ALTER COLUMN product_id DROP NOT NULL;

ALTER TABLE order_items
    ADD CONSTRAINT order_items_product_id_fkey
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL;

-- Add snapshot columns for order history
ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS product_name TEXT,
    ADD COLUMN IF NOT EXISTS variant_name TEXT,
    ADD COLUMN IF NOT EXISTS variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL;

-- ── 7. TRANSACTIONS: change CASCADE → SET NULL on seller_id ──
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_seller_id_fkey;

ALTER TABLE transactions ALTER COLUMN seller_id DROP NOT NULL;

ALTER TABLE transactions
    ADD CONSTRAINT transactions_seller_id_fkey
        FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE SET NULL;

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE INDEX IF NOT EXISTS idx_transactions_order_id ON transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);

-- ── Done ─────────────────────────────────────────────────────
