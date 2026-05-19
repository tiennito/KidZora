-- ============================================================
-- Step 14: Row Level Security (RLS)
-- The Flask backend uses the SERVICE ROLE KEY (bypasses RLS).
-- RLS here protects direct client access.
-- Run after Step 13.
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE profiles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE sellers          ENABLE ROW LEVEL SECURITY;
ALTER TABLE riders           ENABLE ROW LEVEL SECURITY;
ALTER TABLE products         ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders           ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items      ENABLE ROW LEVEL SECURITY;
ALTER TABLE coupons          ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages         ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports          ENABLE ROW LEVEL SECURITY;

-- ── PROFILES ────────────────────────────────────────────────
CREATE POLICY "Users can read own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Admins can read all profiles"
    ON profiles FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin' AND is_approved = TRUE
    ));

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Admins can update all profiles"
    ON profiles FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin' AND is_approved = TRUE
    ));

-- ── SELLERS ─────────────────────────────────────────────────
CREATE POLICY "Sellers can read own row"
    ON sellers FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Buyers/riders can read active sellers"
    ON sellers FOR SELECT USING (is_active = TRUE);

CREATE POLICY "Admins can read all sellers"
    ON sellers FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
    ));

-- ── PRODUCTS ───────────────────────────────────────────────
CREATE POLICY "Everyone can view active products"
    ON products FOR SELECT USING (is_active = TRUE);

CREATE POLICY "Sellers can manage own products"
    ON products FOR ALL
    USING (seller_id IN (SELECT id FROM sellers WHERE user_id = auth.uid()));

-- ── PRODUCT VARIANTS ───────────────────────────────────────
CREATE POLICY "Everyone can read product variants"
    ON product_variants FOR SELECT USING (TRUE);

CREATE POLICY "Sellers can manage own variants"
    ON product_variants FOR ALL
    USING (product_id IN (
        SELECT id FROM products WHERE seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()
        )
    ));

-- ── ORDERS ──────────────────────────────────────────────────
CREATE POLICY "Buyers can view own orders"
    ON orders FOR SELECT USING (auth.uid() = buyer_id);

CREATE POLICY "Sellers can view orders for their shop"
    ON orders FOR SELECT
    USING (seller_id IN (SELECT id FROM sellers WHERE user_id = auth.uid()));

CREATE POLICY "Riders can view assigned orders"
    ON orders FOR SELECT
    USING (rider_id IN (SELECT id FROM riders WHERE user_id = auth.uid()));

-- ── MESSAGES ────────────────────────────────────────────────
CREATE POLICY "Users can read own messages"
    ON messages FOR SELECT
    USING (auth.uid() = sender_id OR auth.uid() = receiver_id);

CREATE POLICY "Users can send messages"
    ON messages FOR INSERT
    WITH CHECK (auth.uid() = sender_id);


CREATE POLICY "Sellers can manage own products" ON products
    FOR ALL USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()
        )
    );

-- Orders RLS policies
CREATE POLICY "Buyers can view own orders" ON orders
    FOR SELECT USING (auth.uid() = buyer_id);

CREATE POLICY "Sellers can view own orders" ON orders
    FOR SELECT USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Riders can view assigned orders" ON orders
    FOR SELECT USING (auth.uid() = rider_id);

CREATE POLICY "Admins can view all orders" ON orders
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Messages RLS policies
CREATE POLICY "Users can view own messages" ON messages
    FOR SELECT USING (
        auth.uid() = sender_id OR 
        auth.uid() = receiver_id
    );

CREATE POLICY "Users can send messages" ON messages
    FOR INSERT WITH CHECK (auth.uid() = sender_id);

CREATE POLICY "Users can update received messages" ON messages
    FOR UPDATE USING (auth.uid() = receiver_id);

-- Transactions RLS policies
CREATE POLICY "Sellers can view own transactions" ON transactions
    FOR SELECT USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Admins can view all transactions" ON transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );
