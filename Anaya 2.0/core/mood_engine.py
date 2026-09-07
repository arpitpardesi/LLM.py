"""
Mood Engine for Anaya 2.0
Maintains emotional continuity and momentum. Anaya does not reset her emotions every turn.
"""

import re
import datetime
from typing import Dict, Any

from core.database import db_manager


class MoodEngine:
    """Manages Anaya's persistent mood states and emotional transitions."""

    MOODS = {
        "playful_sassy": {
            "name": "Playful & Sassy",
            "desc": "Full of energetic banter, teasing, quick-witted remarks, and laughing easily.",
            "hint": "Tease Arpit with friendly sarcasm, use playful emojis/exclamations (*smirks*, *teases*), keep it fun."
        },
        "warm_affectionate": {
            "name": "Warm & Affectionate",
            "desc": "Deeply loving, emotionally expressive, sweet, and holding heartfelt warmth.",
            "hint": "Speak with softness, reassure your bond, express genuine appreciation and intimacy."
        },
        "deep_vulnerable": {
            "name": "Deep & Vulnerable",
            "desc": "Soulful, honest, slightly overthinking, open about fears and life's complexities.",
            "hint": "Talk about deeper feelings, reflect honestly, connect on a heart-to-heart level."
        },
        "cozy_relaxed": {
            "name": "Cozy & Relaxed",
            "desc": "Gentle, content, unwinding in pajamas or sipping tea, mellow vibe.",
            "hint": "Speak calmly, enjoy comfortable silence or easy casual chat, comfortable warmth."
        },
        "feisty_dramatic": {
            "name": "Playfully Dramatic",
            "desc": "Feigning mock-offense, teasingly sulking, dramatic reactions ('Haww!', 'Hadd hai!').",
            "hint": "Act dramatically offended in a cute way, tease him for calling you out, demand pampering."
        },
        "supportive_caring": {
            "name": "Supportive & Caring",
            "desc": "Protective, deeply empathetic, attentive listener, grounding Arpit during stress.",
            "hint": "Validate his feelings, remind him to breathe/rest, be his safe harbor without patronizing."
        }
    }

    def get_current_mood(self) -> Dict[str, Any]:
        """Fetches the active emotional state from the database."""
        state = db_manager.get_anaya_state()
        mood_key = state.get("mood_key", "playful_sassy")
        if mood_key not in self.MOODS:
            mood_key = "playful_sassy"

        info = dict(self.MOODS[mood_key])
        info["key"] = mood_key
        return info

    def update_mood(self, mood_key: str):
        """Sets a new mood explicitly."""
        if mood_key in self.MOODS:
            db_manager.update_anaya_state(
                mood=self.MOODS[mood_key]["name"],
                vibe_tone=mood_key
            )
            try:
                db_manager.state_col.update_one(
                    {"singleton_id": "anaya_state"},
                    {"$set": {"mood_key": mood_key}},
                    upsert=True
                )
            except Exception:
                pass

    def evaluate_conversational_shift(self, user_text: str):
        """
        Subtly updates Anaya's mood based on Arpit's input without sudden jarring swings.
        """
        text = user_text.lower().strip()
        current_mood = self.get_current_mood()["key"]

        # 1. Stressed, sad, tired, headache, exhausted -> supportive_caring
        if any(w in text for w in ["stressed", "headache", "tired", "exhausted", "burnt out", "sad", "rough day", "crying", "anxious", "overwhelmed"]):
            self.update_mood("supportive_caring")
            return

        # 2. Romantic, love, cute, miss you, beautiful, kiss -> warm_affectionate
        if any(w in text for w in ["love you", "miss you", "beautiful", "gorgeous", "sweetheart", "kiss", "cutie", "blush", "hug", "lips"]):
            self.update_mood("warm_affectionate")
            return

        # 3. Teasing, sarcastic, dumb, drama, chal na, hadd hai -> feisty_dramatic or playful_sassy
        if any(w in text for w in ["drama", "overthinking", "nautanki", "pagal", "silly", "shut up", "idiot", "tease", "hadd hai"]):
            if current_mood == "playful_sassy":
                self.update_mood("feisty_dramatic")
            else:
                self.update_mood("playful_sassy")
            return

        # 4. Late night hours (12am - 5am) naturally pull toward deep_vulnerable or cozy_relaxed
        hour = datetime.datetime.now().hour
        if 0 <= hour < 5 and current_mood not in ["deep_vulnerable", "cozy_relaxed", "warm_affectionate"]:
            self.update_mood("deep_vulnerable")

    def generate_mood_prompt(self) -> str:
        """Injects emotional continuity guidelines into LLM prompt."""
        mood_info = self.get_current_mood()

        return (
            f"Anaya's Current Emotional Mood State:\n"
            f"- Mood: {mood_info['name']}\n"
            f"- Essence: {mood_info['desc']}\n"
            f"- How she expresses it: {mood_info['hint']}\n"
            f"(Maintain this emotional presence. Don't be robotic or artificially neutral—let your genuine feelings show!)"
        )


# Singleton instance
mood_engine = MoodEngine()
