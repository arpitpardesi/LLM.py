"""
Unit Tests for Persona and Memory Engine in Anaya 2.0.
"""

import sys
import datetime
from pathlib import Path

# Add Anaya 2.0 to sys.path
ANAYA_DIR = Path(__file__).resolve().parent.parent
if str(ANAYA_DIR) not in sys.path:
    sys.path.insert(0, str(ANAYA_DIR))

from core.persona import persona_engine
from core.memory_engine import memory_engine


def test_persona_loading():
    """Verifies personality.txt is loaded."""
    assert len(persona_engine.base_persona) > 100, "Persona text too short or not loaded"
    assert "Anaya" in persona_engine.base_persona, "Anaya name missing from persona"
    print("✓ Persona file loaded OK")


def test_temporal_context():
    """Verifies temporal context builder produces time and gap instructions."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Just now
    t_just = persona_engine.build_temporal_context(now - datetime.timedelta(minutes=5))
    assert "minutes ago" in t_just or "Real-world time" in t_just
    
    # 2 days ago
    t_days = persona_engine.build_temporal_context(now - datetime.timedelta(days=2))
    assert "2 days ago" in t_days

    print("✓ Temporal context generation OK")


def test_system_prompt_compilation():
    """Verifies complete system prompt compiles cleanly with memories."""
    sample_memories = [
        {"key": "favorite song", "value": "Kun Faya Kun", "category": "music"}
    ]
    prompt = persona_engine.build_system_prompt(memories=sample_memories)
    assert "Kun Faya Kun" in prompt
    assert "CRITICAL CONVERSATIONAL GUIDELINES" in prompt
    print("✓ System prompt assembly OK")


if __name__ == "__main__":
    test_persona_loading()
    test_temporal_context()
    test_system_prompt_compilation()
    print("\nAll memory and persona tests passed successfully!")
