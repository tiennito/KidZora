-- ============================================================
-- Step 38: Rider Availability Toggle
-- Adds is_available flag to the riders table so riders can
-- set themselves online / offline.
-- Run after Step 37.
-- ============================================================

-- Add the column (idempotent — skips if already present)
ALTER TABLE public.riders
  ADD COLUMN IF NOT EXISTS is_available BOOLEAN NOT NULL DEFAULT TRUE;

-- Index for fast filtering of available riders
CREATE INDEX IF NOT EXISTS idx_riders_is_available
  ON public.riders (is_available)
  WHERE is_available = TRUE;

-- Comment
COMMENT ON COLUMN public.riders.is_available IS
  'TRUE = rider is online and accepting new deliveries; FALSE = offline / unavailable.';
