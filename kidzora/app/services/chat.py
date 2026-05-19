"""
Shared ephemeral chat state — typing indicators (in-memory, no DB required).

Usage:
    from app.services.chat import set_typing, is_typing

    set_typing(sender_id, receiver_id)     # call when user is typing
    is_typing(sender_id, receiver_id)      # call in poll to include in response
"""
import time

# { (sender_user_id, receiver_user_id): monotonic_timestamp }
_typing_map: dict[tuple, float] = {}
TYPING_TTL = 5.0  # seconds — indicator expires after this long without a refresh


def set_typing(sender_id: str, receiver_id: str) -> None:
    """Record that sender_id is typing a message to receiver_id."""
    _typing_map[(sender_id, receiver_id)] = time.monotonic()


def is_typing(sender_id: str, receiver_id: str) -> bool:
    """Return True if sender_id typed to receiver_id within the last TYPING_TTL seconds."""
    t = _typing_map.get((sender_id, receiver_id))
    if t is None:
        return False
    if time.monotonic() - t > TYPING_TTL:
        _typing_map.pop((sender_id, receiver_id), None)
        return False
    return True
