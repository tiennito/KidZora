-- ============================================================
-- Step 2: Profiles Table
-- Mirrors auth.users (id = auth.users.id).
-- Stores EVERY user type — address + seller docs live here.
-- Run after Step 1.
-- ============================================================

CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    role user_role NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    is_banned BOOLEAN DEFAULT FALSE,

    -- Address fields
    building_number TEXT,
    street_name TEXT,
    barangay TEXT,
    city TEXT,
    province TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'Philippines',

    -- Seller-specific fields (NULL for non-sellers)
    business_name TEXT,
    business_type TEXT,
    seller_id_type TEXT,
    seller_id_number TEXT,
    seller_id_file TEXT,         -- uploaded gov ID URL
    business_permit_file TEXT,   -- uploaded business permit URL
    bir_file TEXT,               -- uploaded BIR certificate URL

    -- Preferences
    newsletter BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_is_approved ON profiles(is_approved);
