"""
Interactive Mini-Activities Engine for Anaya 2.0
Provides collaborative, playful companion games and bonding modes:
1. Would You Rather
2. 20 Questions / Guess What I'm Thinking
3. Chai Break & Song Recommender
4. Midnight Deep Talk
"""

import random
from typing import Dict, Any, List

from core.llm_client import llm_client
from core.mood_engine import mood_engine


class ActivitiesEngine:
    """Manages collaborative companion activities, games, and deep talks."""

    ACTIVITIES = {
        "would_you_rather": {
            "id": "would_you_rather",
            "name": "Would You Rather? 🎭",
            "desc": "Hilarious, bizarre, and thought-provoking dilemmas with spicy debate!",
            "badge": "Game"
        },
        "twenty_questions": {
            "id": "twenty_questions",
            "name": "20 Questions 🔮",
            "desc": "Anaya picks a secret object, celebrity, or place—can you guess it in 20 questions?",
            "badge": "Game"
        },
        "chai_song": {
            "id": "chai_song",
            "name": "Chai & Music Vibe ☕🎵",
            "desc": "Anaya shares a song she loves right now and the nostalgic story behind it.",
            "badge": "Music"
        },
        "deep_talk": {
            "id": "deep_talk",
            "name": "Midnight Deep Talk 🌙",
            "desc": "Soulful, intimate questions about life, memories, dreams, and the universe.",
            "badge": "Bonding"
        }
    }

    # Curated handcrafted song gems to complement LLM generation
    SONG_VAULT = [
        {
            "title": "Alag Aasmaan",
            "artist": "Anuv Jain",
            "vibe": "Dreamy acoustic indie",
            "reason": "There's this peaceful melancholy in the acoustic guitar that makes you want to stare at the stars with hot chai."
        },
        {
            "title": "Baarishein",
            "artist": "Anuv Jain",
            "vibe": "Rainy cozy warmth",
            "reason": "Every time it rains or the evening breeze gets cool, this song feels like a warm hug."
        },
        {
            "title": "Choo Lo",
            "artist": "The Local Train",
            "vibe": "Raw, nostalgic rock",
            "reason": "Raman Negi's vocals in the climax are pure goosebumps. You literally feel the ache in your chest."
        },
        {
            "title": "Kasoor (Acoustic)",
            "artist": "Prateek Kuhad",
            "vibe": "Soft, vulnerable indie",
            "reason": "Simple guitar chords, but the lyrics hit right when you're in a quiet, thoughtful headspace."
        },
        {
            "title": "Tu Kisi Rail Si",
            "artist": "Swanand Kirkire (Masaan)",
            "vibe": "Poetic, timeless",
            "reason": "Dushyant Kumar's poetry with that gentle strumming... pure art."
        },
        {
            "title": "O Sanam",
            "artist": "Lucky Ali",
            "vibe": "90s timeless nostalgia",
            "reason": "Nobody captures that wanderer soul feeling quite like Lucky Ali. Instant calm."
        }
    ]

    def list_activities(self) -> List[Dict[str, Any]]:
        """Lists all interactive activities."""
        return list(self.ACTIVITIES.values())

    def start_activity(self, activity_id: str, companion_name: str = "Anaya", user_name: str = "Arpit") -> Dict[str, Any]:
        """
        Generates an authentic, in-character starting burst for the chosen activity.
        """
        mood_info = mood_engine.get_current_mood()

        if activity_id == "would_you_rather":
            prompt = (
                f"You are {companion_name} (27-28), playful and witty Indian companion talking with {user_name} (28). "
                "You are kicking off a spontaneous round of 'Would You Rather!'.\n"
                "Invent a fresh, funny, slightly absurd or playfully relatable dilemma tailored for two close friends in India "
                "(e.g. food dilemmas, travel chaos, crazy superpowers, or funny social embarrassments).\n"
                "Write your message in your authentic conversational style with 1-2 bursts (divided by ' ||| '). "
                "State the dilemma excitedly and challenge him to pick one and explain why!"
            )
            text = llm_client.chat_sync([{"role": "user", "content": prompt}], temperature=0.85)
            if not text:
                text = "Okay, my turn to ask! Would you rather only be able to eat cold Maggi for the rest of your life, or never be able to drink chai again? ||| Think carefully before you answer, your Indian citizenship is on the line here! 😂"

            return {
                "activity_id": activity_id,
                "title": "Would You Rather?",
                "starter_message": text
            }

        elif activity_id == "twenty_questions":
            items = ["Cutting Chai Glass", "Autoricshaw Meter", "Old iPod Shuffle", "Samosa", "Gulab Jamun", "Backpack", "Taj Mahal", "Guitar", "Filter Coffee", "Maggi Bowl"]
            secret = random.choice(items)
            text = (
                f"Ooh yes, let's play! 🔮 ||| "
                f"I've picked something in my mind right now... it's a real physical object! ||| "
                f"You have 20 Yes/No questions to figure out what it is. Ask your first question!"
            )
            return {
                "activity_id": activity_id,
                "title": "20 Questions",
                "secret": secret,
                "starter_message": text
            }

        elif activity_id == "chai_song":
            song = random.choice(self.SONG_VAULT)
            text = (
                f"Wait, pause everything! Let me put you on to this track... 🎧 ||| "
                f"I've been listening to **'{song['title']}' by {song['artist']}** on loop. {song['reason']} ||| "
                f"Go listen to it right now, or tell me what song you have on repeat lately!"
            )
            return {
                "activity_id": activity_id,
                "title": "Chai & Song Recommendation",
                "song": song,
                "starter_message": text
            }

        elif activity_id == "deep_talk":
            prompt = (
                f"You are {companion_name} (27-28), sitting with {user_name} (28) in a quiet, soulful moment. "
                "Ask one genuinely thoughtful, non-cliché deep question to ponder together "
                "(e.g. about childhood nostalgia, things we take for granted, how time moves, or what home feels like).\n"
                "Speak intimately with warmth and vulnerability. Use 1-2 natural bursts (divided by ' ||| ')."
            )
            text = llm_client.chat_sync([{"role": "user", "content": prompt}], temperature=0.8)
            if not text:
                text = (
                    "Can I ask you something honest? ||| "
                    "When was the last time you felt completely at peace with where you are in life, without worrying about the next milestone?"
                )
            return {
                "activity_id": activity_id,
                "title": "Midnight Deep Talk",
                "starter_message": text
            }

        else:
            return {
                "activity_id": "unknown",
                "title": "Activity",
                "starter_message": "Let's do something fun! What's on your mind?"
            }


# Singleton instance
activities_engine = ActivitiesEngine()
