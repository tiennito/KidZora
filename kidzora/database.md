-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.buyer_addresses (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  buyer_id uuid NOT NULL,
  label text NOT NULL DEFAULT 'Home'::text,
  full_name text NOT NULL DEFAULT ''::text,
  phone text NOT NULL DEFAULT ''::text,
  region text NOT NULL DEFAULT ''::text,
  province text NOT NULL DEFAULT ''::text,
  city text NOT NULL DEFAULT ''::text,
  barangay text NOT NULL DEFAULT ''::text,
  street_name text NOT NULL DEFAULT ''::text,
  building_number text NOT NULL DEFAULT ''::text,
  postal_code text NOT NULL DEFAULT ''::text,
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT buyer_addresses_pkey PRIMARY KEY (id),
  CONSTRAINT buyer_addresses_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.cart_items (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  buyer_id uuid NOT NULL,
  cart_key text NOT NULL,
  product_id uuid NOT NULL,
  variant_id uuid,
  quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
  name text NOT NULL,
  price numeric NOT NULL CHECK (price >= 0::numeric),
  image_url text,
  seller_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT cart_items_pkey PRIMARY KEY (id),
  CONSTRAINT cart_items_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.coupons (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  code text NOT NULL UNIQUE,
  description text,
  discount_type USER-DEFINED NOT NULL,
  discount_value numeric NOT NULL,
  min_order_amount numeric DEFAULT 0,
  max_discount_amount numeric,
  usage_limit integer,
  usage_count integer DEFAULT 0,
  applicable_sellers ARRAY,
  is_active boolean DEFAULT true,
  expires_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT coupons_pkey PRIMARY KEY (id)
);
CREATE TABLE public.messages (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  sender_id uuid NOT NULL,
  receiver_id uuid NOT NULL,
  content text NOT NULL,
  message_type USER-DEFINED DEFAULT 'text'::message_type,
  is_read boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  is_delivered boolean NOT NULL DEFAULT false,
  CONSTRAINT messages_pkey PRIMARY KEY (id),
  CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.profiles(id),
  CONSTRAINT messages_receiver_id_fkey FOREIGN KEY (receiver_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.notifications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  type text NOT NULL,
  title text NOT NULL,
  body text,
  is_read boolean NOT NULL DEFAULT false,
  data jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT notifications_pkey PRIMARY KEY (id)
);
CREATE TABLE public.order_items (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  order_id uuid NOT NULL,
  product_id uuid,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  variant_id uuid,
  product_name text,
  variant_name text,
  CONSTRAINT order_items_pkey PRIMARY KEY (id),
  CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id),
  CONSTRAINT order_items_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.product_variants(id),
  CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id)
);
CREATE TABLE public.orders (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  buyer_id uuid,
  seller_id uuid,
  rider_id uuid,
  total_amount numeric NOT NULL,
  commission numeric NOT NULL,
  seller_earnings numeric NOT NULL,
  delivery_address jsonb NOT NULL,
  status USER-DEFINED DEFAULT 'pending'::order_status,
  payment_status USER-DEFINED DEFAULT 'pending'::payment_status,
  payment_method USER-DEFINED,
  rider_assigned_at timestamp with time zone,
  delivered_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  notes text,
  coupon_id uuid,
  discount_amount numeric DEFAULT 0,
  delivery_fee numeric NOT NULL DEFAULT 0,
  seller_coupon_id uuid,
  cancel_requested boolean DEFAULT false,
  cancel_reason text,
  cancel_status text CHECK (cancel_status = ANY (ARRAY['pending_review'::text, 'approved'::text, 'rejected'::text])),
  cancel_response text,
  proof_of_delivery_url text,
  CONSTRAINT orders_pkey PRIMARY KEY (id),
  CONSTRAINT orders_rider_id_fkey FOREIGN KEY (rider_id) REFERENCES public.riders(id),
  CONSTRAINT orders_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.profiles(id),
  CONSTRAINT orders_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(id),
  CONSTRAINT orders_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id),
  CONSTRAINT orders_seller_coupon_id_fkey FOREIGN KEY (seller_coupon_id) REFERENCES public.seller_coupons(id)
);
CREATE TABLE public.payout_requests (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  seller_id uuid NOT NULL,
  amount numeric NOT NULL CHECK (amount > 0::numeric),
  method text NOT NULL,
  account_name text NOT NULL,
  account_number text NOT NULL,
  status text NOT NULL DEFAULT 'pending'::text,
  admin_notes text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  processed_at timestamp with time zone,
  CONSTRAINT payout_requests_pkey PRIMARY KEY (id),
  CONSTRAINT payout_requests_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(id)
);
CREATE TABLE public.platform_settings (
  key text NOT NULL,
  value text NOT NULL,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT platform_settings_pkey PRIMARY KEY (key)
);
CREATE TABLE public.product_reviews (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL,
  buyer_id uuid NOT NULL,
  order_id uuid,
  rating integer NOT NULL CHECK (rating >= 1 AND rating <= 5),
  title text,
  body text,
  is_verified_purchase boolean NOT NULL DEFAULT false,
  helpful_count integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  variant_id uuid,
  variant_name text,
  media_urls jsonb NOT NULL DEFAULT '[]'::jsonb,
  seller_reply text,
  seller_reply_at timestamp with time zone,
  CONSTRAINT product_reviews_pkey PRIMARY KEY (id),
  CONSTRAINT product_reviews_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id),
  CONSTRAINT product_reviews_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.profiles(id),
  CONSTRAINT product_reviews_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id),
  CONSTRAINT product_reviews_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.product_variants(id)
);
CREATE TABLE public.product_variants (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL,
  name text NOT NULL,
  image_url text,
  price_modifier numeric DEFAULT 0,
  stock_quantity integer DEFAULT 0,
  sort_order integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT product_variants_pkey PRIMARY KEY (id),
  CONSTRAINT product_variants_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id)
);
CREATE TABLE public.products (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  seller_id uuid NOT NULL,
  name text NOT NULL,
  description text,
  price numeric NOT NULL,
  category text NOT NULL,
  age_group text,
  condition USER-DEFINED DEFAULT 'new'::product_condition,
  stock_quantity integer NOT NULL DEFAULT 0,
  images ARRAY,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  sale_price numeric,
  sale_starts_at timestamp with time zone,
  sale_ends_at timestamp with time zone,
  is_deleted boolean NOT NULL DEFAULT false,
  slug text,
  meta_title text,
  meta_description text,
  CONSTRAINT products_pkey PRIMARY KEY (id),
  CONSTRAINT products_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(id)
);
CREATE TABLE public.profiles (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  email text NOT NULL UNIQUE,
  first_name text NOT NULL,
  last_name text NOT NULL,
  phone text,
  role USER-DEFINED NOT NULL,
  is_approved boolean DEFAULT false,
  is_banned boolean DEFAULT false,
  address jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  city text,
  state text,
  postal_code text,
  country text,
  newsletter boolean DEFAULT false,
  building_number text,
  street_name text,
  region text,
  province text,
  barangay text,
  business_name text,
  business_type text,
  seller_id_type text,
  seller_id_number text,
  seller_id_file text,
  business_permit_file text,
  bir_file text,
  ban_reason text,
  avatar_url text,
  rejection_reason text,
  CONSTRAINT profiles_pkey PRIMARY KEY (id)
);
CREATE TABLE public.push_subscriptions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  endpoint text NOT NULL,
  p256dh text NOT NULL,
  auth text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT push_subscriptions_pkey PRIMARY KEY (id),
  CONSTRAINT push_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.reports (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  report_type USER-DEFINED NOT NULL,
  title text NOT NULL,
  description text,
  parameters jsonb,
  data jsonb,
  generated_by uuid,
  start_date timestamp with time zone,
  end_date timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT reports_pkey PRIMARY KEY (id),
  CONSTRAINT reports_generated_by_fkey FOREIGN KEY (generated_by) REFERENCES public.profiles(id)
);
CREATE TABLE public.return_requests (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL,
  buyer_id uuid NOT NULL,
  seller_id uuid NOT NULL,
  reason text NOT NULL,
  details text,
  refund_type text NOT NULL DEFAULT 'refund'::text CHECK (refund_type = ANY (ARRAY['refund'::text, 'return_and_refund'::text])),
  status text NOT NULL DEFAULT 'pending'::text CHECK (status = ANY (ARRAY['pending'::text, 'seller_approved'::text, 'seller_rejected'::text, 'escalated'::text, 'admin_approved'::text, 'admin_rejected'::text])),
  seller_response text,
  admin_response text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT return_requests_pkey PRIMARY KEY (id),
  CONSTRAINT return_requests_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id)
);
CREATE TABLE public.review_helpful_votes (
  review_id uuid NOT NULL,
  voter_id uuid NOT NULL,
  CONSTRAINT review_helpful_votes_pkey PRIMARY KEY (review_id, voter_id),
  CONSTRAINT review_helpful_votes_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.product_reviews(id),
  CONSTRAINT review_helpful_votes_voter_id_fkey FOREIGN KEY (voter_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.rider_payout_requests (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  rider_id uuid NOT NULL,
  amount numeric NOT NULL CHECK (amount > 0::numeric),
  method text NOT NULL,
  account_name text NOT NULL,
  account_number text NOT NULL,
  status text NOT NULL DEFAULT 'pending'::text,
  admin_notes text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  processed_at timestamp with time zone,
  CONSTRAINT rider_payout_requests_pkey PRIMARY KEY (id),
  CONSTRAINT rider_payout_requests_rider_id_fkey FOREIGN KEY (rider_id) REFERENCES public.riders(id)
);
CREATE TABLE public.riders (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  licensed_id_url text,
  original_receipt_url text,
  certificate_of_registration_url text,
  is_active boolean DEFAULT true,
  is_available boolean NOT NULL DEFAULT true,
  bank_name text,
  bank_account text,
  CONSTRAINT riders_pkey PRIMARY KEY (id),
  CONSTRAINT riders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.seller_coupons (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  seller_id uuid NOT NULL,
  code text NOT NULL,
  description text,
  discount_type text NOT NULL CHECK (discount_type = ANY (ARRAY['percentage'::text, 'fixed'::text, 'free_delivery'::text])),
  discount_value numeric NOT NULL DEFAULT 0 CHECK (discount_value >= 0::numeric),
  min_order_amount numeric DEFAULT 0,
  max_discount_amount numeric,
  usage_limit integer,
  usage_count integer DEFAULT 0,
  is_active boolean DEFAULT true,
  expires_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT seller_coupons_pkey PRIMARY KEY (id),
  CONSTRAINT seller_coupons_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(id)
);
CREATE TABLE public.seller_follows (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  buyer_id uuid NOT NULL,
  seller_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT seller_follows_pkey PRIMARY KEY (id),
  CONSTRAINT seller_follows_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES auth.users(id),
  CONSTRAINT seller_follows_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(id)
);
CREATE TABLE public.sellers (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE,
  shop_name text NOT NULL,
  shop_description text,
  bank_account text,
  bank_name text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  commission_rate numeric DEFAULT 10.00,
  is_active boolean DEFAULT true,
  shop_banner_url text,
  about_store text,
  CONSTRAINT sellers_pkey PRIMARY KEY (id),
  CONSTRAINT sellers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.support_replies (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  ticket_id uuid NOT NULL,
  sender_id uuid NOT NULL,
  content text NOT NULL,
  is_admin boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT support_replies_pkey PRIMARY KEY (id),
  CONSTRAINT support_replies_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES public.support_tickets(id),
  CONSTRAINT support_replies_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.support_tickets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  buyer_id uuid NOT NULL,
  subject text NOT NULL,
  category text NOT NULL DEFAULT 'general'::text,
  status text NOT NULL DEFAULT 'open'::text,
  priority text NOT NULL DEFAULT 'medium'::text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT support_tickets_pkey PRIMARY KEY (id),
  CONSTRAINT support_tickets_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.transactions (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  order_id uuid,
  seller_id uuid,
  amount numeric NOT NULL,
  commission_amount numeric NOT NULL,
  seller_earnings numeric NOT NULL,
  type USER-DEFINED NOT NULL,
  status USER-DEFINED DEFAULT 'pending'::transaction_status,
  payout_reference text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  notes text,
  CONSTRAINT transactions_pkey PRIMARY KEY (id),
  CONSTRAINT transactions_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id),
  CONSTRAINT transactions_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(id)
);
CREATE TABLE public.unban_requests (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  message text NOT NULL,
  file_url text,
  status text NOT NULL DEFAULT 'pending'::text CHECK (status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'superseded'::text])),
  admin_notes text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT unban_requests_pkey PRIMARY KEY (id),
  CONSTRAINT unban_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL,
  email text NOT NULL,
  full_name text NOT NULL,
  contact_number text NOT NULL,
  role text NOT NULL CHECK (role = ANY (ARRAY['buyer'::text, 'rider'::text])),
  house_no text NOT NULL,
  street_no text NOT NULL,
  barangay text NOT NULL,
  city text NOT NULL,
  province text NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);
CREATE TABLE public.wishlists (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  buyer_id uuid NOT NULL,
  product_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT wishlists_pkey PRIMARY KEY (id),
  CONSTRAINT wishlists_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id),
  CONSTRAINT wishlists_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.profiles(id)
);