-- Step 44: Configurable location-based delivery fees
-- Run this in Supabase SQL editor.

create extension if not exists "pgcrypto";

create table if not exists public.delivery_zones (
  id uuid primary key default gen_random_uuid(),
  location_name text not null,
  delivery_fee numeric(10, 2) not null default 0 check (delivery_fee >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists delivery_zones_location_name_lower_uidx
  on public.delivery_zones (lower(trim(location_name)));

alter table public.orders
  add column if not exists subtotal numeric(10, 2),
  add column if not exists delivery_fee numeric(10, 2) not null default 0,
  add column if not exists discount_amount numeric(10, 2) not null default 0;

-- Backfill subtotal for older orders where possible.
update public.orders
set subtotal = greatest(
  coalesce(total_amount, 0) - coalesce(delivery_fee, 0) + coalesce(discount_amount, 0),
  0
)
where subtotal is null;

-- Configurable fallback fee used when no zone matches.
insert into public.platform_settings (key, value)
values ('default_delivery_fee', '120.00')
on conflict (key) do nothing;

-- Optional starter examples. Update/delete these to fit your real service area.
insert into public.delivery_zones (location_name, delivery_fee)
select v.location_name, v.delivery_fee
from (
  values
    ('Cebu City', 50.00),
    ('Manila', 80.00),
    ('Davao', 80.00),
    ('Province', 120.00)
) as v(location_name, delivery_fee)
where not exists (
  select 1
  from public.delivery_zones dz
  where lower(trim(dz.location_name)) = lower(trim(v.location_name))
);
