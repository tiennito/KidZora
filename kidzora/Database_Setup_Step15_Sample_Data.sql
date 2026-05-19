-- Step 15: Insert sample data (optional)
-- Run this after Step 14 if you want sample data

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
