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
        """Fetches the active emotional state, momentum, and trajectory from the database."""
        state = db_manager.get_anaya_state()
        mood_key = state.get("mood_key", "playful_sassy")
        if mood_key not in self.MOODS:
            mood_key = "playful_sassy"

        info = dict(self.MOODS[mood_key])
        info["key"] = mood_key
        info["momentum"] = state.get("mood_momentum", 0.8)
        info["trajectory"] = state.get("mood_trajectory", [mood_key])[-5:]
        info["intensity"] = state.get("mood_intensity", "moderate")
        return info

    def update_mood(self, mood_key: str, momentum_boost: float = 0.25, intensity: str = "moderate"):
        """Sets a new mood explicitly or via organic momentum."""
        if mood_key in self.MOODS:
            state = db_manager.get_anaya_state()
            trajectory = state.get("mood_trajectory", [])
            trajectory.append(mood_key)
            trajectory = trajectory[-10:]

            current_momentum = state.get("mood_momentum", 0.5)
            new_momentum = min(1.0, max(0.2, current_momentum + momentum_boost))

            db_manager.update_anaya_state(
                mood=self.MOODS[mood_key]["name"],
                vibe_tone=mood_key
            )
            try:
                db_manager.state_col.update_one(
                    {"singleton_id": "anaya_state"},
                    {
                        "$set": {
                            "mood_key": mood_key,
                            "mood_momentum": round(new_momentum, 2),
                            "mood_trajectory": trajectory,
                            "mood_intensity": intensity
                        }
                    },
                    upsert=True
                )
            except Exception:
                pass

    def evaluate_conversational_shift(self, user_text: str):
        """
        Subtly updates Anaya's mood based on Arpit's input with emotional momentum,
        preventing jarring single-word whiplash while organically following conversation tone.
        """
        text = user_text.lower().strip()
        current_state = self.get_current_mood()
        current_mood = current_state["key"]
        current_momentum = current_state.get("momentum", 0.5)

        # 1. Stressed, sad, tired, headache, overwhelmed -> supportive_caring
        stress_words = ["stressed", "headache", "tired", "exhausted", "burnt out", "sad", "rough day", "crying", "anxious", "overwhelmed", "depressed", "heavy heart", "pain"]
        if any(w in text for w in stress_words):
            self.update_mood("supportive_caring", momentum_boost=0.35, intensity="deep")
            return

        # 2. Romantic, heartfelt love, beautiful, miss you -> warm_affectionate
        affection_words = ["love you", "miss you", "beautiful", "gorgeous", "sweetheart", "kiss", "cutie", "blush", "hug", "lips", "adore you", "jaan", "sunona"]
        if any(w in text for w in affection_words):
            self.update_mood("warm_affectionate", momentum_boost=0.3, intensity="high")
            return

        # 3. Teasing, sarcastic, dumb, drama, chal na, hadd hai -> feisty_dramatic or playful_sassy
        tease_words = ["drama", "overthinking", "nautanki", "pagal", "silly", "shut up", "idiot", "tease", "hadd hai", "chal na", "dramebaaz", "bakwas"]
        if any(w in text for w in tease_words):
            # If already supportive due to high momentum, don't immediately switch to feisty
            if current_mood == "supportive_caring" and current_momentum > 0.7:
                # Decay momentum gently rather than abruptly switching
                try:
                    db_manager.state_col.update_one(
                        {"singleton_id": "anaya_state"},
                        {"$set": {"mood_momentum": max(0.3, current_momentum - 0.25)}}
                    )
                except Exception:
                    pass
                return

            if current_mood == "playful_sassy":
                self.update_mood("feisty_dramatic", momentum_boost=0.2, intensity="playful")
            else:
                self.update_mood("playful_sassy", momentum_boost=0.2, intensity="playful")
            return

        # 4. Excited, celebratory, win, passed, got the job, party -> energetic & cheerful
        excited_words = ["congrats", "passed", "got the job", "promoted", "won", "yay", "celebrate", "awesome", "hell yeah", "party", "let's go"]
        if any(w in text for w in excited_words):
            self.update_mood("playful_sassy", momentum_boost=0.4, intensity="high")
            return

        # 5. Philosophical, existential, late night deep thoughts -> deep_vulnerable
        deep_words = ["meaning of life", "why are we", "future", "lonely", "growing old", "feel empty", "scared of", "what if"]
        if any(w in text for w in deep_words):
            self.update_mood("deep_vulnerable", momentum_boost=0.3, intensity="deep")
            return

        # 6. Late night hours (12am - 5am) naturally pull toward deep_vulnerable or cozy_relaxed
        hour = datetime.datetime.now().hour
        if 0 <= hour < 5 and current_mood not in ["deep_vulnerable", "cozy_relaxed", "warm_affectionate"]:
            self.update_mood("deep_vulnerable", momentum_boost=0.15, intensity="gentle")

    def generate_mood_prompt(self) -> str:
        """Injects emotional continuity guidelines into LLM prompt."""
        mood_info = self.get_current_mood()

        return (
            f"Anaya's Current Emotional Mood State:\n"
            f"- Mood: {mood_info['name']}\n"
            f"- Essence: {mood_info['desc']}\n"
            f"- How she expresses it: {mood_info['hint']}\n"
            f"- Intensity: {mood_info.get('intensity', 'moderate')}\n"
            f"(Maintain this emotional presence naturally. Don't be robotic or artificially neutral—let your genuine feelings show!)"
        )


# Singleton instance
mood_engine = MoodEngine()

