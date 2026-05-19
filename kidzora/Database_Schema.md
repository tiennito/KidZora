# KidZora Database Schema

This document contains the complete SQL schema for the KidZora e-commerce platform.

## Tables Overview

1. **profiles** - User profiles with role-based access
2. **sellers** - Seller-specific information
3. **riders** - Rider-specific information
4. **products** - Product catalog
5. **orders** - Order management
6. **order_items** - Order line items
7. **coupons** - Discount coupons
8. **messages** - Chat system
9. **transactions** - Financial records
10. **reports** - Generated reports

## SQL Schema

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE user_role AS ENUM ('admin', 'seller', 'buyer', 'rider');
CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'cancelled');
CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'refunded');
CREATE TYPE payment_method AS ENUM ('cash', 'gcash', 'paymaya', 'bank_transfer');
CREATE TYPE discount_type AS ENUM ('percentage', 'fixed');
CREATE TYPE transaction_type AS ENUM ('commission', 'payout', 'refund');
CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'failed');
CREATE TYPE report_type AS ENUM ('sales', 'users', 'commissions', 'activity');
CREATE TYPE vehicle_type AS ENUM ('motorcycle', 'bicycle', 'car');
CREATE TYPE product_condition AS ENUM ('new', 'like_new', 'good', 'fair');
CREATE TYPE message_type AS ENUM ('text', 'image', 'file');

-- Profiles table
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    role user_role NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    is_banned BOOLEAN DEFAULT FALSE,
    address JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sellers table
CREATE TABLE sellers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    shop_name TEXT NOT NULL,
    shop_description TEXT,
    business_permit TEXT, -- URL or file path
    valid_id TEXT, -- URL or file path
    bank_account TEXT,
    bank_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Riders table
CREATE TABLE riders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    vehicle_type vehicle_type NOT NULL,
    vehicle_plate TEXT,
    driver_license TEXT, -- URL or file path
    license_expiry DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category TEXT NOT NULL,
    age_group TEXT, -- e.g., "0-2", "3-5", "6-8", "9-12"
    condition product_condition DEFAULT 'new',
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    images TEXT[], -- Array of image URLs
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    buyer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    rider_id UUID REFERENCES riders(id) ON DELETE SET NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    commission DECIMAL(10,2) NOT NULL,
    seller_earnings DECIMAL(10,2) NOT NULL,
    delivery_address JSONB NOT NULL,
    status order_status DEFAULT 'pending',
    payment_status payment_status DEFAULT 'pending',
    payment_method payment_method,
    rider_assigned_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Order items table
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL, -- Price at time of purchase
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Coupons table
CREATE TABLE coupons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    discount_type discount_type NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    min_order_amount DECIMAL(10,2) DEFAULT 0,
    max_discount_amount DECIMAL(10,2),
    usage_limit INTEGER,
    usage_count INTEGER DEFAULT 0,
    applicable_sellers UUID[], -- Empty array means all sellers
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type message_type DEFAULT 'text',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    commission_amount DECIMAL(10,2) NOT NULL,
    seller_earnings DECIMAL(10,2) NOT NULL,
    type transaction_type NOT NULL,
    status transaction_status DEFAULT 'pending',
    payout_reference TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reports table
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type report_type NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    parameters JSONB,
    data JSONB,
    generated_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_is_approved ON profiles(is_approved);
CREATE INDEX idx_sellers_user_id ON sellers(user_id);
CREATE INDEX idx_riders_user_id ON riders(user_id);
CREATE INDEX idx_products_seller_id ON products(seller_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_orders_buyer_id ON orders(buyer_id);
CREATE INDEX idx_orders_seller_id ON orders(seller_id);
CREATE INDEX idx_orders_rider_id ON orders(rider_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_coupons_code ON coupons(code);
CREATE INDEX idx_coupons_is_active ON coupons(is_active);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_receiver_id ON messages(receiver_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_transactions_seller_id ON transactions(seller_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_created_at ON reports(created_at);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sellers ENABLE ROW LEVEL SECURITY;
ALTER TABLE riders ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Profiles RLS policies
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Admins can view all profiles" ON profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text AND role = 'admin'
        )
    );

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid()::text = id::text);

CREATE POLICY "Admins can update all profiles" ON profiles
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text AND role = 'admin'
        )
    );

-- Sellers RLS policies
CREATE POLICY "Sellers can view own seller profile" ON sellers
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Admins can view all sellers" ON sellers
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text AND role = 'admin'
        )
    );

-- Products RLS policies
CREATE POLICY "Sellers can view own products" ON products
    FOR SELECT USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "Everyone can view active products" ON products
    FOR SELECT USING (is_active = TRUE);

CREATE POLICY "Sellers can manage own products" ON products
    FOR ALL USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()::text
        )
    );

-- Orders RLS policies
CREATE POLICY "Buyers can view own orders" ON orders
    FOR SELECT USING (auth.uid()::text = buyer_id::text);

CREATE POLICY "Sellers can view own orders" ON orders
    FOR SELECT USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "Riders can view assigned orders" ON orders
    FOR SELECT USING (auth.uid()::text = rider_id::text);

CREATE POLICY "Admins can view all orders" ON orders
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text AND role = 'admin'
        )
    );

-- Messages RLS policies
CREATE POLICY "Users can view own messages" ON messages
    FOR SELECT USING (
        auth.uid()::text = sender_id::text OR 
        auth.uid()::text = receiver_id::text
    );

CREATE POLICY "Users can send messages" ON messages
    FOR INSERT WITH CHECK (auth.uid()::text = sender_id::text);

CREATE POLICY "Users can update received messages" ON messages
    FOR UPDATE USING (auth.uid()::text = receiver_id::text);

-- Transactions RLS policies
CREATE POLICY "Sellers can view own transactions" ON transactions
    FOR SELECT USING (
        seller_id IN (
            SELECT id FROM sellers WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "Admins can view all transactions" ON transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text AND role = 'admin'
        )
    );

-- Functions for common operations

-- Function to get user conversations
CREATE OR REPLACE FUNCTION get_user_conversations(current_user_id TEXT)
RETURNS TABLE(
    other_user_id UUID,
    other_user_name TEXT,
    last_message TEXT,
    last_message_time TIMESTAMP WITH TIME ZONE,
    unread_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH conversations AS (
        SELECT DISTINCT
            CASE 
                WHEN sender_id = current_user_id::uuid THEN receiver_id
                ELSE sender_id
            END as other_user_id
        FROM messages
        WHERE sender_id = current_user_id::uuid OR receiver_id = current_user_id::uuid
    ),
    last_messages AS (
        SELECT 
            c.other_user_id,
            m.content as last_message,
            m.created_at as last_message_time
        FROM conversations c
        LEFT JOIN LATERAL (
            SELECT content, created_at
            FROM messages
            WHERE (sender_id = current_user_id::uuid AND receiver_id = c.other_user_id)
               OR (sender_id = c.other_user_id AND receiver_id = current_user_id::uuid)
            ORDER BY created_at DESC
            LIMIT 1
        ) m ON true
    ),
    unread_counts AS (
        SELECT 
            CASE 
                WHEN sender_id = current_user_id::uuid THEN receiver_id
                ELSE sender_id
            END as other_user_id,
            COUNT(*) as unread_count
        FROM messages
        WHERE receiver_id = current_user_id::uuid AND is_read = FALSE
        GROUP BY other_user_id
    )
    SELECT 
        lm.other_user_id,
        p.first_name || ' ' || p.last_name as other_user_name,
        lm.last_message,
        lm.last_message_time,
        COALESCE(uc.unread_count, 0) as unread_count
    FROM last_messages lm
    JOIN profiles p ON p.id = lm.other_user_id
    LEFT JOIN unread_counts uc ON uc.other_user_id = lm.other_user_id;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sellers_updated_at BEFORE UPDATE ON sellers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_riders_updated_at BEFORE UPDATE ON riders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_coupons_updated_at BEFORE UPDATE ON coupons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Sample Data

```sql
-- Insert admin user
INSERT INTO profiles (email, first_name, last_name, role, is_approved) VALUES
('admin@kidzora.com', 'Admin', 'User', 'admin', TRUE);

-- Insert sample sellers
INSERT INTO profiles (email, first_name, last_name, phone, role, is_approved) VALUES
('seller1@kidzora.com', 'Juan', 'Dela Cruz', '+639123456789', 'seller', TRUE),
('seller2@kidzora.com', 'Maria', 'Santos', '+639987654321', 'seller', FALSE);

INSERT INTO sellers (user_id, shop_name, shop_description, bank_account, bank_name) VALUES
((SELECT id FROM profiles WHERE email = 'seller1@kidzora.com'), 'Kids Toys Store', 'Quality toys for all ages', '1234567890', 'BPI'),
((SELECT id FROM profiles WHERE email = 'seller2@kidzora.com'), 'Baby Essentials', 'Everything for your little one', '0987654321', 'BDO');

-- Insert sample buyers
INSERT INTO profiles (email, first_name, last_name, phone, role, is_approved) VALUES
('buyer1@kidzora.com', 'Pedro', 'Reyes', '+639112233445', 'buyer', TRUE),
('buyer2@kidzora.com', 'Ana', 'Garcia', '+639556677889', 'buyer', TRUE);

-- Insert sample riders
INSERT INTO profiles (email, first_name, last_name, phone, role, is_approved) VALUES
('rider1@kidzora.com', 'Ricardo', 'Lim', '+639334455667', 'rider', TRUE),
('rider2@kidzora.com', 'Sofia', 'Lee', '+639778899001', 'rider', FALSE);

INSERT INTO riders (user_id, vehicle_type, vehicle_plate, driver_license, license_expiry) VALUES
((SELECT id FROM profiles WHERE email = 'rider1@kidzora.com'), 'motorcycle', 'ABC123', 'LICENSE001', '2025-12-31'),
((SELECT id FROM profiles WHERE email = 'rider2@kidzora.com'), 'bicycle', 'N/A', 'LICENSE002', '2025-06-30');

-- Insert sample products
INSERT INTO products (seller_id, name, description, price, category, age_group, condition, stock_quantity) VALUES
((SELECT id FROM sellers WHERE shop_name = 'Kids Toys Store'), 'Educational Building Blocks', 'Colorful building blocks for creative play', 599.99, 'Toys', '3-5', 'new', 50),
((SELECT id FROM sellers WHERE shop_name = 'Kids Toys Store'), 'Stuffed Teddy Bear', 'Soft and cuddly teddy bear', 299.99, 'Toys', '0-2', 'new', 30),
((SELECT id FROM sellers WHERE shop_name = 'Baby Essentials'), 'Baby Diapers Pack', 'Pack of 50 disposable diapers', 450.00, 'Baby Care', '0-2', 'new', 100),
((SELECT id FROM sellers WHERE shop_name = 'Baby Essentials'), 'Baby Bottle Set', 'Set of 3 feeding bottles', 350.00, 'Baby Care', '0-2', 'new', 25);

-- Insert sample coupons
INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, usage_limit, expires_at) VALUES
('WELCOME10', 'Welcome discount for new users', 'percentage', 10, 500, 100, '2024-12-31'),
('SUMMER20', 'Summer sale special', 'percentage', 20, 1000, 50, '2024-08-31'),
('FLAT100', 'Fixed discount on minimum purchase', 'fixed', 100, 800, 200, '2024-11-30');
```

## Notes

1. **UUIDs**: All primary keys use UUIDs for better scalability and security
2. **RLS**: Row Level Security is enabled to ensure data privacy
3. **JSONB**: Used for flexible data storage (addresses, images, etc.)
4. **Timestamps**: All tables track creation and update times
5. **Indexes**: Optimized for common query patterns
6. **Enums**: Used for data consistency in status fields
7. **Functions**: Helper functions for complex operations
8. **Triggers**: Automatic timestamp updates

This schema provides a solid foundation for the KidZora e-commerce platform with proper security, scalability, and maintainability.
