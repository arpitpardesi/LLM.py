"""
Unit tests for Living Person engines: LifeEngine, MoodEngine, and ProactiveEngine.
"""

import sys
import uuid
from pathlib import Path

# Add Anaya 2.0 to sys.path
ANAYA_DIR = Path(__file__).resolve().parent.parent
if str(ANAYA_DIR) not in sys.path:
    sys.path.insert(0, str(ANAYA_DIR))

from core.database import db_manager
from core.life_engine import life_engine
from core.mood_engine import mood_engine
from core.proactive_engine import proactive_engine
from core.persona import persona_engine


def test_life_engine():
    """Verifies that Anaya has active daily routines, thoughts, and music."""
    info = life_engine.get_current_activity()
    assert "activity" in info and len(info["activity"]) > 5
    assert "thoughts" in info
    assert "vibe" in info

    prompt_section = life_engine.generate_life_prompt()
    assert "Anaya's Current Personal Life Context" in prompt_section
    print("✓ LifeEngine personal activity & routines OK")


def test_mood_engine():
    """Verifies that emotional momentum persists and transitions appropriately."""
    # Test initial mood
    mood = mood_engine.get_current_mood()
    assert "name" in mood and "hint" in mood

    # Test shifting on stress cues
    mood_engine.evaluate_conversational_shift("I'm feeling really stressed and overwhelmed with work")
    new_mood = mood_engine.get_current_mood()
    assert new_mood["key"] == "supportive_caring"

    # Test shifting on romantic cues
    mood_engine.evaluate_conversational_shift("You look beautiful and I miss you so much")
    romantic_mood = mood_engine.get_current_mood()
    assert romantic_mood["key"] == "warm_affectionate"

    # Test shifting on teasing cues
    mood_engine.evaluate_conversational_shift("Stop being such a dramatic nautanki haha")
    teasing_mood = mood_engine.get_current_mood()
    assert teasing_mood["key"] in ["feisty_dramatic", "playful_sassy"]

    prompt_mood = mood_engine.generate_mood_prompt()
    assert "Anaya's Current Emotional Mood State" in prompt_mood
    print("✓ MoodEngine emotional state transitions OK")


def test_proactive_threads():
    """Verifies life thread tracking and follow-up generation."""
    test_topic = f"Test Meeting {uuid.uuid4()}"
    saved = db_manager.add_life_thread(
        topic=test_topic,
        context="Important client demo at 3 PM",
        follow_up_hint="How did the client demo go?",
        category="work"
    )
    assert saved, "Failed to save life thread"

    # Retrieve active threads
    threads = db_manager.get_active_life_threads()
    assert any(t.get("topic") == test_topic.lower() for t in threads)

    # Check pending follow-up prompt
    proactive_prompt = proactive_engine.generate_proactive_prompt()
    assert "PROACTIVE FRIEND CHECK-IN" in proactive_prompt

    # Mark resolved and cleanup
    db_manager.resolve_life_thread(test_topic)
    db_manager.threads_col.delete_many({"topic": test_topic.lower()})
    print("✓ ProactiveEngine life threads & check-ins OK")


def test_persona_living_integration():
    """Verifies that the compiled system prompt contains living persona elements."""
    full_prompt = persona_engine.build_system_prompt()
    assert "Anaya's Current Personal Life Context" in full_prompt
    assert "Anaya's Current Emotional Mood State" in full_prompt
    assert "CRITICAL CONVERSATIONAL GUIDELINES" in full_prompt
    print("✓ PersonaEngine living integration OK")


if __name__ == "__main__":
    test_life_engine()
    test_mood_engine()
    test_proactive_threads()
    test_persona_living_integration()
    print("\nAll living person engine tests passed successfully!")
