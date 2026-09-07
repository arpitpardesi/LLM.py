"""
Unit and Integration Tests for DatabaseManager in Anaya 2.0.
"""

import sys
import uuid
from pathlib import Path

# Add Anaya 2.0 to sys.path
ANAYA_DIR = Path(__file__).resolve().parent.parent
if str(ANAYA_DIR) not in sys.path:
    sys.path.insert(0, str(ANAYA_DIR))

from core.database import db_manager


def test_database_connection():
    """Verifies MongoDB connectivity."""
    ok, msg = db_manager.health_check()
    assert ok, f"Database health check failed: {msg}"
    print("✓ Database connection OK")


def test_save_and_load_message():
    """Tests message insertion and retrieval."""
    test_session = f"test_{uuid.uuid4()}"
    dialog_id = db_manager.get_next_dialog_id()
    
    saved = db_manager.save_message(
        role="user",
        content="Test automated verification ping",
        session_id=test_session,
        dialog_id=dialog_id,
        metadata={"test": True}
    )
    assert saved, "Failed to save message"

    # Verify retrieval
    recent = db_manager.load_recent_messages(limit=5)
    assert any(m.get("session_id") == test_session for m in recent), "Saved message not found in recent"
    print("✓ Message save & retrieval OK")

    # Clean up test message
    db_manager.delete_messages({"session_id": test_session})
    print("✓ Test message cleanup OK")


def test_memory_facts():
    """Tests memory upsert and retrieval."""
    test_key = "favorite test drink"
    test_val = "Masala Chai with ginger"

    saved = db_manager.save_memory_fact(key=test_key, value=test_val, category="preference")
    assert saved, "Failed to save memory fact"

    mems = db_manager.get_all_memories()
    match = next((m for m in mems if m.get("key") == test_key), None)
    assert match is not None, "Memory fact not found"
    assert match.get("value") == test_val, "Memory value mismatch"
    print("✓ Memory fact save & retrieval OK")

    # Clean up
    db_manager.delete_memory(test_key)
    print("✓ Memory cleanup OK")


def test_delete_last_n():
    """Tests deleting last N messages and turns."""
    test_session = f"test_del_{uuid.uuid4()}"

    # Insert 4 messages (2 turns)
    db_manager.save_message("user", "Hello 1", test_session, 101)
    db_manager.save_message("assistant", "Hi 1", test_session, 102)
    db_manager.save_message("user", "Hello 2", test_session, 103)
    db_manager.save_message("assistant", "Hi 2", test_session, 104)

    # Delete 1 message (should delete 'Hi 2')
    count, docs = db_manager.delete_last_n_messages(n=1, session_id=test_session)
    assert count == 1
    assert docs[0].get("content") == "Hi 2"
    print("✓ Delete last 1 message OK")

    # Delete 1 turn (should delete remaining 'Hello 2' and 'Hi 1')
    count, docs = db_manager.delete_last_n_turns(n_turns=1, session_id=test_session)
    assert count == 2
    assert docs[0].get("content") == "Hello 2"
    assert docs[1].get("content") == "Hi 1"
    print("✓ Delete last 1 turn OK")

    # Clean up remaining
    db_manager.delete_messages({"session_id": test_session})
    print("✓ Cleanup OK")


if __name__ == "__main__":
    test_database_connection()
    test_save_and_load_message()
    test_memory_facts()
    test_delete_last_n()
    print("\nAll database tests passed successfully!")
