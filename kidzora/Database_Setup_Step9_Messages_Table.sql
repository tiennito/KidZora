-- ============================================================
-- Step 9: Messages Table
-- Used for rider↔seller and buyer↔seller chat.
-- order_ref links a thread to a specific order (optional).
-- Run after Step 8.
-- ============================================================

CREATE TABLE messages (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id   UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    content      TEXT NOT NULL,
    message_type message_type DEFAULT 'text',
    is_read      BOOLEAN DEFAULT FALSE,

    -- Optional: tie message to a specific order thread
    order_ref UUID REFERENCES orders(id) ON DELETE SET NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_messages_sender_id   ON messages(sender_id);
CREATE INDEX idx_messages_receiver_id ON messages(receiver_id);
CREATE INDEX idx_messages_order_ref   ON messages(order_ref);
CREATE INDEX idx_messages_created_at  ON messages(created_at);
