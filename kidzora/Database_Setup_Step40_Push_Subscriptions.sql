-- Step 40: Web Push subscription storage (VAPID)
-- One row per user × browser/device.  Pruned automatically when a push
-- returns 410 Gone (expired subscription).

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    endpoint   TEXT        NOT NULL,
    p256dh     TEXT        NOT NULL,
    auth       TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, endpoint)
);

CREATE INDEX IF NOT EXISTS push_subscriptions_user_idx ON push_subscriptions(user_id);

-- Trigger: keep updated_at fresh
CREATE OR REPLACE FUNCTION update_push_subscriptions_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN  NEW.updated_at = now();  RETURN NEW; END;
$$;

DROP TRIGGER IF EXISTS trg_push_subscriptions_updated_at ON push_subscriptions;
CREATE TRIGGER trg_push_subscriptions_updated_at
    BEFORE UPDATE ON push_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_push_subscriptions_updated_at();

-- RLS: only the service-role key (used by Flask backend) can read/write
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access" ON push_subscriptions
    FOR ALL USING (true) WITH CHECK (true);

COMMENT ON TABLE push_subscriptions IS
    'Web Push (VAPID) subscription endpoints per user device.  '
    'Stale rows (HTTP 410 from push service) are pruned by services/push.py.';
