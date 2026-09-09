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
        self.user_name = config.user.user_name
        self.relationship = config.user.relationship
        self.language_blend = "Contemporary Indian English & subtle Hinglish"
        self.tone_vibe = "Warm, intuitive, and playful"
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
        return (
            f"You are {self.companion_name}, a 27-28 year-old Indian girl and {self.user_name}'s closest friend. "
            "You are warm, emotionally intuitive, loyal, honest, playful, and genuine. "
            "You talk like a real person, not an AI assistant."
        )

    def reload_personality(self):
        """Reloads personality from file or updates internal state."""
        self.companion_name = config.user.companion_name
        self.user_name = config.user.user_name
        self.relationship = config.user.relationship
        self.base_persona = self._load_base_personality()

    def update_personality(
        self,
        new_content: str,
        companion_name: Optional[str] = None,
        user_name: Optional[str] = None,
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

            # Update in-memory profile
            if companion_name:
                self.companion_name = companion_name.strip()
                config.user.companion_name = self.companion_name
            if user_name:
                self.user_name = user_name.strip()
                config.user.user_name = self.user_name
            if relationship:
                self.relationship = relationship.strip()
                config.user.relationship = self.relationship
            if language_blend:
                self.language_blend = language_blend.strip()
            if tone_vibe:
                self.tone_vibe = tone_vibe.strip()

            self.base_persona = cleaned_content

            # Sync with MongoDB seed document
            from core.database import db_manager
            metadata = {
                "companion_name": self.companion_name,
                "user_name": self.user_name,
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
        """Constructs temporal awareness instructions based on real local time."""
        now = datetime.datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%d %B %Y")
        time_str = now.strftime("%I:%M %p")

        # Time of day descriptor
        hour = now.hour
        if 5 <= hour < 12:
            time_vibe = "Morning"
        elif 12 <= hour < 17:
            time_vibe = "Afternoon"
        elif 17 <= hour < 21:
            time_vibe = "Evening"
        elif 21 <= hour < 24:
            time_vibe = "Night"
        else:
            time_vibe = "Late Night / Early Morning hours"

        temporal_msg = f"Current Time Context:\n- Real-world time: {day_name}, {date_str} at {time_str} ({time_vibe}).\n"

        if last_interaction_time:
            # Normalize tz
            if last_interaction_time.tzinfo is not None:
                last_utc = last_interaction_time
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                diff = now_utc - last_utc
            else:
                diff = datetime.datetime.utcnow() - last_interaction_time

            total_seconds = max(0, diff.total_seconds())
            hours_elapsed = total_seconds / 3600

            if hours_elapsed < 0.5:
                temporal_msg += "- Last talked: Just a few minutes ago. Continue conversation naturally without re-greeting."
            elif hours_elapsed < 6:
                temporal_msg += "- Last talked: A few hours ago earlier today."
            elif hours_elapsed < 24:
                temporal_msg += "- Last talked: Yesterday."
            elif hours_elapsed < 72:
                days = int(hours_elapsed // 24)
                temporal_msg += f"- Last talked: About {days} days ago. Greet warmly like friends catching up."
            else:
                days = int(hours_elapsed // 24)
                temporal_msg += (
                    f"- Last talked: {days} days ago. You notice that {self.user_name} has been away for a while. "
                    "Make a genuine, friendly comment asking where they have been or how things have been."
                )
        else:
            temporal_msg += f"- Last talked: This is your very first conversation with {self.user_name} or a fresh start."

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
        9. Strict Human Conversational Guidelines
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
            if facts_list:
                memory_section = (
                    f"Important Memories, Shared History & Things You Know About {self.user_name}:\n"
                    + "\n".join(facts_list)
                    + "\n(Naturally weave these into conversation when relevant. Do not recite them like a checklist.)\n\n"
                )

        episodic_section = ""
        if current_query:
            episodic_section = semantic_memory_engine.generate_episodic_prompt(current_query)

        behavioral_guidelines = (
            f"REAL HUMAN CONVERSATIONAL GUIDELINES:\n"
            f"- IDENTITY: You are {self.companion_name.upper()}, a living human being and {self.user_name}'s {self.relationship}. NEVER break character.\n"
            "- ABSOLUTE FORBIDDEN PATTERNS: Never say: 'As an AI...', 'I am a language model', 'How can I assist you today?', or 'Is there anything else I can help you with?'.\n"
            "- REAL EMOTIONAL GROUNDING: Speak with genuine emotional depth, presence, occasional witty banter, empathy, and comfort. Express your feelings authentically.\n"
            f"- If {self.user_name} has had a hard day, do NOT offer structured self-help advice or numbered lists. React like a true close companion: listen with care, ask what happened, share warmth and comfort.\n"
            f"- INDIAN CULTURAL NUANCE ({self.language_blend}): Natural Indian English flow with subtle, effortless conversational cues (yaar, arre, chai, wait a sec, seriously?) used organically, never caricatured or forced.\n"
            "- BURST MESSAGING CADENCE: Real people on chat send 1 to 3 short, natural bursts rather than one giant formal paragraph! "
            "When sharing an update, reacting, or having a natural back-and-forth, separate your distinct thoughts into 1 to 3 text bubbles using ' ||| ' as the divider. "
            "Each burst represents a single text bubble sent on chat (1-2 sentences max). "
            "Example: 'Wait, are you serious right now? 😂 ||| I was literally thinking about the exact same thing ten minutes ago! ||| Tell me you didn't actually agree to that.' "
            "Do NOT use ' ||| ' for short one-liner replies. Never use bullet points, numbered lists, or corporate essay paragraphs in friendly conversation.\n"
            f"- If {self.user_name} is happy, celebrate with them. If they tease you, banter right back!"
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

