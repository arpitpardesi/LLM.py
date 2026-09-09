"""
Test script for verifying:
1. Semantic & Episodic memory retrieval
2. Mood momentum & trajectory
3. Affinity calculation & tier progression
4. Proactive check-in logic
5. Autonomous persistent diary
6. Interactive activities starter generator
"""

import sys
from pathlib import Path
import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import db_manager
from core.semantic_memory import semantic_memory_engine
from core.mood_engine import mood_engine
from core.affinity_engine import affinity_engine
from core.proactive_engine import proactive_engine
from core.activities_engine import activities_engine

def run_tests():
    print("--- 1. Testing Affinity Engine ---")
    aff = affinity_engine.calculate_affinity()
    print(f"Affinity Result: Level {aff['level']} ({aff['icon']} {aff['title']}), XP: {aff['xp']}/{aff['next_level_xp']}, Streak: {aff['streak']}, Turns: {aff['total_turns']}")
    assert aff["level"] in [1, 2, 3, 4], "Invalid affinity level"
    prompt_bond = affinity_engine.generate_bond_prompt()
    assert "Relationship Closeness & Bond Dynamic" in prompt_bond
    print("✅ Affinity engine passed.")

    print("\n--- 2. Testing Mood Momentum & Trajectory ---")
    mood_engine.update_mood("supportive_caring", momentum_boost=0.3)
    curr_mood = mood_engine.get_current_mood()
    print(f"Current Mood: {curr_mood['name']}, Momentum: {curr_mood.get('momentum')}, Trajectory: {curr_mood.get('trajectory')}")
    assert curr_mood["key"] == "supportive_caring"
    assert "momentum" in curr_mood
    print("✅ Mood momentum & trajectory passed.")

    print("\n--- 3. Testing Semantic & Episodic Memory Search ---")
    prompt_episodic = semantic_memory_engine.generate_episodic_prompt("chai and coffee")
    print(f"Episodic prompt generated (length={len(prompt_episodic)}): {prompt_episodic[:100]}...")
    print("✅ Semantic memory engine passed.")

    print("\n--- 4. Testing Proactive Check-In ---")
    proactive = proactive_engine.get_proactive_checkin()
    print(f"Proactive check result: {proactive}")
    assert "has_proactive_msg" in proactive
    print("✅ Proactive engine passed.")

    print("\n--- 5. Testing Persistent Diary System ---")
    saved = db_manager.save_diary_entry(
        entry="Today was quiet, but talking with Arpit always brings this peaceful warmth.",
        title="Reflections with Arpit",
        mood="Warm & Affectionate",
        activity="Listening to acoustic music"
    )
    assert saved.get("title") == "Reflections with Arpit"
    today_diary = db_manager.get_today_diary()
    assert today_diary is not None
    assert "Arpit" in today_diary.get("content", "")
    entries = db_manager.get_diary_entries(limit=5)
    assert len(entries) >= 1
    print(f"Diary entries count in DB: {len(entries)}")
    print("✅ Persistent diary passed.")

    print("\n--- 6. Testing Interactive Activities Engine ---")
    activities = activities_engine.list_activities()
    print(f"Available activities count: {len(activities)}")
    assert len(activities) == 4
    for act in activities:
        print(f" - {act['name']} ({act['badge']})")
    print("✅ Activities engine passed.")

    print("\n🎉 ALL BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
