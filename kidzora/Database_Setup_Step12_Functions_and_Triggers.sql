-- ============================================================
-- Step 12: Functions and Triggers
-- Run after Step 11.
-- ============================================================

-- ── Auto-update updated_at on every row change ─────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_sellers_updated_at
    BEFORE UPDATE ON sellers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_riders_updated_at
    BEFORE UPDATE ON riders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_product_variants_updated_at
    BEFORE UPDATE ON product_variants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Helper: get user conversations (used by chat views) ─────────
CREATE OR REPLACE FUNCTION get_user_conversations(current_user_id TEXT)
RETURNS TABLE(
    other_user_id      UUID,
    other_user_name    TEXT,
    last_message       TEXT,
    last_message_time  TIMESTAMP WITH TIME ZONE,
    unread_count       INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH conversations AS (
        SELECT DISTINCT
            CASE
                WHEN sender_id = current_user_id::uuid THEN receiver_id
                ELSE sender_id
            END AS other_user_id
        FROM messages
        WHERE sender_id   = current_user_id::uuid
           OR receiver_id = current_user_id::uuid
    ),
    last_messages AS (
        SELECT
            c.other_user_id,
            m.content    AS last_message,
            m.created_at AS last_message_time
        FROM conversations c
        LEFT JOIN LATERAL (
            SELECT content, created_at
            FROM messages
            WHERE (sender_id   = current_user_id::uuid AND receiver_id = c.other_user_id)
               OR (sender_id   = c.other_user_id       AND receiver_id = current_user_id::uuid)
            ORDER BY created_at DESC
            LIMIT 1
        ) m ON TRUE
    ),
    unread_counts AS (
        SELECT
            sender_id AS other_user_id,
            COUNT(*)  AS unread_count
        FROM messages
        WHERE receiver_id = current_user_id::uuid AND is_read = FALSE
        GROUP BY sender_id
    )
    SELECT
        lm.other_user_id,
        p.first_name || ' ' || p.last_name AS other_user_name,
        lm.last_message,
        lm.last_message_time,
        COALESCE(uc.unread_count, 0)::INTEGER AS unread_count
    FROM last_messages lm
    JOIN profiles p ON p.id = lm.other_user_id
    LEFT JOIN unread_counts uc ON uc.other_user_id = lm.other_user_id;
END;
$$ LANGUAGE plpgsql;


-- Function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
