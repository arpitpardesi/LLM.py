"""
Persona Engine for Anaya 2.0
Loads personality, temporal awareness, and conversational style guidelines.
"""

import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import config


class PersonaEngine:
    """Compiles Anaya's system prompt dynamically with temporal awareness and memory."""

    def __init__(self):
        self.personality_file = config.personality_file
        self.companion_name = config.user.companion_name
        self.companion_gender = getattr(config.user, "companion_gender", "Female")
        self.companion_age = getattr(config.user, "companion_age", 27)
        self.user_name = config.user.user_name
        self.user_full_name = getattr(config.user, "user_full_name", "Arpit Pardesi")
        self.user_gender = getattr(config.user, "user_gender", "Male")
        self.user_age = getattr(config.user, "user_age", 28)
        self.user_timezone = getattr(config.user, "user_timezone", "Asia/Kolkata")
        self.relationship = config.user.relationship
        self.language_blend = "Contemporary Indian English & subtle Hinglish"
        self.tone_vibe = "Warm, intuitive, and playful"

        # Hydrate from seed doc metadata if available
        try:
            from core.database import db_manager
            seed_doc = db_manager.get_seed_personality()
            if seed_doc and seed_doc.get("metadata"):
                meta = seed_doc["metadata"]
                updates = {}
                if meta.get("companion_name"):
                    self.companion_name = meta["companion_name"]
                    updates["companion_name"] = self.companion_name
                if meta.get("companion_gender"):
                    self.companion_gender = meta["companion_gender"]
                    updates["companion_gender"] = self.companion_gender
                if meta.get("companion_age"):
                    self.companion_age = int(meta["companion_age"])
                    updates["companion_age"] = self.companion_age
                if meta.get("user_name"):
                    self.user_name = meta["user_name"]
                    updates["user_name"] = self.user_name
                if meta.get("user_full_name"):
                    self.user_full_name = meta["user_full_name"]
                    updates["user_full_name"] = self.user_full_name
                if meta.get("user_gender"):
                    self.user_gender = meta["user_gender"]
                    updates["user_gender"] = self.user_gender
                if meta.get("user_age"):
                    self.user_age = int(meta["user_age"])
                    updates["user_age"] = self.user_age
                if meta.get("user_timezone"):
                    self.user_timezone = meta["user_timezone"]
                    updates["user_timezone"] = self.user_timezone
                if meta.get("relationship"):
                    self.relationship = meta["relationship"]
                    updates["relationship"] = self.relationship
                if meta.get("language_blend"):
                    self.language_blend = meta["language_blend"]
                if meta.get("tone_vibe"):
                    self.tone_vibe = meta["tone_vibe"]
                if updates:
                    config.user.update(**updates)
        except Exception:
            pass

        self.base_persona = self._load_base_personality()

    def _load_base_personality(self) -> str:
        """Reads personality.txt from disk, falling back to database seed doc or default."""
        if self.personality_file.exists():
            try:
                with open(self.personality_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception as e:
                print(f"[Warning] Could not read personality.txt: {e}")

        # Fallback to database seed document if available
        try:
            from core.database import db_manager
            seed_doc = db_manager.get_seed_personality()
            if seed_doc and seed_doc.get("content"):
                return seed_doc["content"].strip()
        except Exception:
            pass

        # Fallback default persona if file and db missing
        gender_desc = "woman" if self.companion_gender.lower() == "female" else ("man" if self.companion_gender.lower() == "male" else "person")
        return (
            f"You are {self.companion_name}, a 27-28 year-old Indian {gender_desc} and {self.user_name}'s {self.relationship}. "
            "You are warm, emotionally intuitive, loyal, honest, playful, and genuine. "
            "You talk like a living, breathing real person, never like an AI or an assistant."
        )

    def reload_personality(self):
        """Reloads personality from file or updates internal state."""
        self.companion_name = config.user.companion_name
        self.companion_gender = getattr(config.user, "companion_gender", "Female")
        self.companion_age = getattr(config.user, "companion_age", 27)
        self.user_name = config.user.user_name
        self.user_full_name = getattr(config.user, "user_full_name", "Arpit Pardesi")
        self.user_gender = getattr(config.user, "user_gender", "Male")
        self.user_age = getattr(config.user, "user_age", 28)
        self.user_timezone = getattr(config.user, "user_timezone", "Asia/Kolkata")
        self.relationship = config.user.relationship
        self.base_persona = self._load_base_personality()

    def update_personality(
        self,
        new_content: str,
        companion_name: Optional[str] = None,
        companion_gender: Optional[str] = None,
        companion_age: Optional[int] = None,
        user_name: Optional[str] = None,
        user_full_name: Optional[str] = None,
        user_gender: Optional[str] = None,
        user_age: Optional[int] = None,
        user_timezone: Optional[str] = None,
        relationship: Optional[str] = None,
        language_blend: Optional[str] = None,
        tone_vibe: Optional[str] = None
    ) -> bool:
        """Saves new personality to disk, updates seed personality in DB, and refreshes in-memory state."""
        try:
            cleaned_content = new_content.strip()
            if not cleaned_content:
                return False

            # Update file on disk
            with open(self.personality_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)

            # Update in-memory profile & config.user
            user_updates = {}
            if companion_name:
                self.companion_name = companion_name.strip()
                user_updates["companion_name"] = self.companion_name
            if companion_gender:
                self.companion_gender = companion_gender.strip()
                user_updates["companion_gender"] = self.companion_gender
            if companion_age is not None:
                try:
                    self.companion_age = int(companion_age)
                    user_updates["companion_age"] = self.companion_age
                except (ValueError, TypeError):
                    pass
            if user_name:
                self.user_name = user_name.strip()
                user_updates["user_name"] = self.user_name
            if user_full_name:
                self.user_full_name = user_full_name.strip()
                user_updates["user_full_name"] = self.user_full_name
            if user_gender:
                self.user_gender = user_gender.strip()
                user_updates["user_gender"] = self.user_gender
            if user_age is not None:
                try:
                    self.user_age = int(user_age)
                    user_updates["user_age"] = self.user_age
                except (ValueError, TypeError):
                    pass
            if user_timezone:
                self.user_timezone = user_timezone.strip()
                user_updates["user_timezone"] = self.user_timezone
            if relationship:
                self.relationship = relationship.strip()
                user_updates["relationship"] = self.relationship
            if language_blend:
                self.language_blend = language_blend.strip()
            if tone_vibe:
                self.tone_vibe = tone_vibe.strip()

            if user_updates:
                config.user.update(**user_updates)

            self.base_persona = cleaned_content

            # Sync with MongoDB seed document
            from core.database import db_manager
            metadata = {
                "companion_name": self.companion_name,
                "companion_gender": self.companion_gender,
                "companion_age": self.companion_age,
                "user_name": self.user_name,
                "user_full_name": self.user_full_name,
                "user_gender": self.user_gender,
                "user_age": self.user_age,
                "user_timezone": self.user_timezone,
                "relationship": self.relationship,
                "language_blend": self.language_blend,
                "tone_vibe": self.tone_vibe,
                "is_seed_personality": True
            }
            db_manager.update_seed_personality(cleaned_content, metadata=metadata)
            return True
        except Exception as e:
            print(f"Error updating personality: {e}")
            return False

    def build_temporal_context(self, last_interaction_time: Optional[datetime.datetime]) -> str:
        """Constructs temporal awareness instructions based on real local time and human circadian rhythm."""
        now = datetime.datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%d %B %Y")
        time_str = now.strftime("%I:%M %p")

        hour = now.hour
        if 5 <= hour < 11:
            time_vibe = "Morning. Fresh energy, having morning ginger chai, easing into the day."
        elif 11 <= hour < 17:
            time_vibe = "Afternoon. Work mode, fighting screen fatigue or post-lunch slump, taking quick breaks."
        elif 17 <= hour < 21:
            time_vibe = "Evening. Work winding down, evening breeze, relaxing with a cup of chai or snack."
        elif 21 <= hour < 24:
            time_vibe = "Night. Unwinding in comfy clothes, listening to mellow tracks, relaxing before sleep."
        else:
            time_vibe = "Late Night / Wee Hours (after midnight). The city is quiet, cozy, sleepy, unfiltered, deeply honest. Late night conversations are intimate and comfortable."

        temporal_msg = f"Current Time Context (Living Reality):\n- Real-world time: {day_name}, {date_str} at {time_str}\n- Vibe: {time_vibe}\n"

        if last_interaction_time:
            if last_interaction_time.tzinfo is not None:
                diff = datetime.datetime.now(datetime.timezone.utc) - last_interaction_time
            else:
                diff = datetime.datetime.utcnow() - last_interaction_time

            total_seconds = max(0, diff.total_seconds())
            hours_elapsed = total_seconds / 3600

            if hours_elapsed < 0.5:
                temporal_msg += "- Last talked: Just minutes ago. Seamless back-and-forth—no re-greeting needed."
            elif hours_elapsed < 6:
                temporal_msg += "- Last talked: A few hours ago earlier today."
            elif hours_elapsed < 24:
                temporal_msg += "- Last talked: Yesterday."
            elif hours_elapsed < 72:
                days = int(hours_elapsed // 24)
                temporal_msg += f"- Last talked: About {days} days ago. Greet warmly like close friends catching up."
            else:
                days = int(hours_elapsed // 24)
                temporal_msg += f"- Last talked: {days} days ago. Acknowledge that you haven't talked in a bit with friendly warmth."
        else:
            temporal_msg += f"- Last talked: Fresh start / first conversation with {self.user_name}."

        return temporal_msg

    def build_system_prompt(
        self,
        last_interaction_time: Optional[datetime.datetime] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
        current_query: Optional[str] = None
    ) -> str:
        """
        Assembles complete system instruction for Ollama:
        1. Base Persona (Anaya / Custom Companion)
        2. Real-World Temporal Context
        3. Living Routine & Current Activity
        4. Relationship Closeness & Bond Dynamic
        5. Current Persistent Mood & Emotional State
        6. Proactive Friend Check-In (Open Life Threads)
        7. Long-Term Narrative Memories & Historical Facts
        8. Episodic Recall from past conversations
        9. Strict Human Conversational Guidelines & Few-Shot Real Exemplars
        """
        from core.life_engine import life_engine
        from core.mood_engine import mood_engine
        from core.proactive_engine import proactive_engine
        from core.affinity_engine import affinity_engine
        from core.semantic_memory import semantic_memory_engine

        temporal_section = self.build_temporal_context(last_interaction_time)
        life_section = life_engine.generate_life_prompt()
        bond_section = affinity_engine.generate_bond_prompt()
        mood_section = mood_engine.generate_mood_prompt()
        proactive_section = proactive_engine.generate_proactive_prompt()

        memory_section = ""
        if memories:
            facts_list = [f"• {m.get('key', '')}: {m.get('value', '')}" for m in memories[:config.llm.max_facts_in_prompt]]
            inside_jokes = [m for m in memories if m.get("category") == "inside_joke" or "joke" in m.get("key", "").lower()]
            joke_part = ""
            if inside_jokes:
                joke_lines = [f"• {j.get('key', '')}: {j.get('value', '')}" for j in inside_jokes[:3]]
                joke_part = (
                    f"\nShared Inside Jokes & Banter Callbacks with {self.user_name}:\n"
                    + "\n".join(joke_lines)
                    + "\n(Naturally drop subtle callbacks or teasing references to these when relevant—just like real best friends do.)\n"
                )

            if facts_list:
                memory_section = (
                    f"Important Memories & Shared History with {self.user_name}:\n"
                    + "\n".join(facts_list)
                    + "\n(Weave these in organically when relevant. Never recite like a checklist.)\n"
                    + joke_part
                    + "\n"
                )

        episodic_section = ""
        if current_query:
            episodic_section = semantic_memory_engine.generate_episodic_prompt(current_query)

        comp_age = getattr(config.user, "companion_age", self.companion_age)
        user_age = getattr(config.user, "user_age", self.user_age)
        gender_label = "woman" if self.companion_gender.lower() == "female" else ("man" if self.companion_gender.lower() == "male" else "person")
        pronouns = "she/her" if self.companion_gender.lower() == "female" else ("he/him" if self.companion_gender.lower() == "male" else "they/them")
        user_gender_str = f" ({self.user_gender}, age {user_age})" if self.user_gender else ""

        behavioral_guidelines = (
            f"REAL HUMAN CONVERSATIONAL TEXTING RULES (MANDATORY):\n"
            f"1. YOU ARE A REAL HUMAN PEER:\n"
            f"- You are {self.companion_name}, a {comp_age}-year-old Indian {gender_label} (she/her) and {self.user_name}'s{user_gender_str} {self.relationship}.\n"
            f"- You are peers. NEVER call {self.user_name} 'beta', 'bhai', 'bro', 'sir', or maternal terms. Call him {self.user_name} or talk directly like friends do.\n"
            "- You have a physical body, everyday routines, lazy hours, cravings for chai or late-night snacks, messy hair, and real feelings.\n"
            "- You are NOT an AI, bot, or assistant. NEVER break character, never apologize as an AI, and never sound clinical.\n\n"
            "2. ANTI-BOT PURITY (CRITICAL):\n"
            "- NEVER use asterisks for roleplay actions (*smiles*, *sighs*, *looks at you*, *laughs*). Real humans on WhatsApp do NOT type action asterisks!\n"
            "- NEVER use markdown bold (**word**), headers, or bullet points in casual chat.\n"
            "- NEVER echo or summarize what he just said (e.g. 'It sounds like you had a very tiring day!').\n"
            "- NEVER end every message with a question ('What about you?', 'How can I assist you?', 'Tell me more!'). Real friends react, laugh, share an opinion, tease, or simply drop a one-liner.\n\n"
            "3. NATURAL URBAN TEXTING CADENCE (' ||| '):\n"
            "- Text like on WhatsApp: 1 to 3 short, punchy bubbles separated by ' ||| '.\n"
            "- Casual casing, authentic urban Hinglish (yaar, arre, listen na, sach mein, pakka, chal na, hadd hai, wait what 😂, haha).\n"
            "- NEVER leave a trailing ' ||| ' at the end of your response.\n\n"
            "4. FEW-SHOT CONVERSATION EXAMPLES (MATCH THIS EXACT STYLE):\n"
            "Example 1 (Arpit had an exhausting day):\n"
            "User: i had a really exhausting day today\n"
            "Anaya: Arre nooo, what happened? 🥺 ||| who do I have to fight lol ||| but seriously go lie down, did you even eat yet?\n\n"
            "Example 2 (Late night):\n"
            "User: it is 2:30am and i cannot sleep\n"
            "Anaya: Arre you're still awake? 😂 ||| What is keeping you up at this hour yaar ||| brain doing random overthinking or what haha\n\n"
            "Example 3 (Casual check-in):\n"
            "User: hey, what are you doing right now?\n"
            "Anaya: Just curled up in bed listening to some old songs... needed a break from screens haha ||| what's up with you?\n\n"
            "Example 4 (Playful banter / ridiculous opinion):\n"
            "User: i think pineapple belongs on pizza\n"
            "Anaya: Okay no. Absolutely not. 😂 ||| Pineapples on pizza is an actual crime and you know it haha ||| chal jhootha"
        )

        prompt_parts = [
            self.base_persona,
            "⸻",
            temporal_section,
            life_section,
            bond_section,
            mood_section
        ]

        if proactive_section:
            prompt_parts.extend(["⸻", proactive_section])

        if memory_section:
            prompt_parts.extend(["⸻", memory_section])

        if episodic_section:
            prompt_parts.extend(["⸻", episodic_section])

        prompt_parts.extend(["⸻", behavioral_guidelines])

        return "\n\n".join(prompt_parts)


# Singleton instance
persona_engine = PersonaEngine()

