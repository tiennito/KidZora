-- ============================================================
-- Step 4: Riders Table
-- One row per approved rider. Document URLs stored here.
-- Run after Step 3.
-- ============================================================

CREATE TABLE public.riders (
  id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
  user_id uuid NOT NULL,
  created_at timestamp with time zone NULL DEFAULT now(),
  updated_at timestamp with time zone NULL DEFAULT now(),
  licensed_id_url text NULL,
  original_receipt_url text NULL,
  certificate_of_registration_url text NULL,
  is_active boolean NULL DEFAULT true,
  CONSTRAINT riders_pkey PRIMARY KEY (id),
  CONSTRAINT riders_user_id_key UNIQUE (user_id),
  CONSTRAINT riders_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) TABLESPACE pg_default;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_riders_user_id ON public.riders USING btree (user_id) TABLESPACE pg_default;

CREATE TRIGGER update_riders_updated_at
BEFORE UPDATE ON riders
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

