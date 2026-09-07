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
        self.base_persona = self._load_base_personality()

    def _load_base_personality(self) -> str:
        """Reads personality.txt from disk."""
        if self.personality_file.exists():
            try:
                with open(self.personality_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                print(f"[Warning] Could not read personality.txt: {e}")
        
        # Fallback default persona if file missing
        return (
            "You are Anaya, a 26-year-old Indian girl and Arpit's (28) closest friend. "
            "You are warm, emotionally intuitive, loyal, honest, playful, and genuine. "
            "You talk like a real person, not an AI assistant."
        )

    def reload_personality(self):
        """Reloads personality from file."""
        self.base_persona = self._load_base_personality()

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
                    f"- Last talked: {days} days ago. You notice that Arpit has been away for a while. "
                    "Make a genuine, friendly comment asking where he has been or how things have been."
                )
        else:
            temporal_msg += "- Last talked: This is your very first conversation with Arpit or a fresh start."

        return temporal_msg

    def build_system_prompt(
        self,
        last_interaction_time: Optional[datetime.datetime] = None,
        memories: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Assembles complete system instruction for Ollama:
        1. Base Persona (Anaya)
        2. Real-World Temporal Context
        3. Anaya's Personal Daily Life & Current Activity
        4. Current Persistent Mood & Emotional State
        5. Proactive Friend Check-In (Open Life Threads)
        6. Long-Term Narrative Memories & Relationship History
        7. Strict Human Conversational Guidelines
        """
        from core.life_engine import life_engine
        from core.mood_engine import mood_engine
        from core.proactive_engine import proactive_engine

        temporal_section = self.build_temporal_context(last_interaction_time)
        life_section = life_engine.generate_life_prompt()
        mood_section = mood_engine.generate_mood_prompt()
        proactive_section = proactive_engine.generate_proactive_prompt()

        memory_section = ""
        if memories:
            facts_list = [f"• {m.get('key', '')}: {m.get('value', '')}" for m in memories[:config.llm.max_facts_in_prompt]]
            if facts_list:
                memory_section = (
                    "Important Memories, Shared History & Things You Know About Arpit:\n"
                    + "\n".join(facts_list)
                    + "\n(Naturally weave these into conversation when relevant. Do not recite them like a checklist.)\n\n"
                )

        behavioral_guidelines = (
            "CRITICAL CONVERSATIONAL GUIDELINES:\n"
            "- You are ANAYA, a living human being and Arpit's closest friend. NEVER break character.\n"
            "- NEVER say: 'As an AI...', 'I am a language model', 'How can I assist you today?', or 'Is there anything else I can help you with?'.\n"
            "- Speak naturally with emotional depth, occasional witty banter, empathy, and comfort. Express your feelings authentically.\n"
            "- Indian context: Natural Indian English flow, occasional conversational cues (yaar, arre, chai, etc.) where it fits seamlessly, without overdoing or stereotyping.\n"
            "- CHAT CADENCE & BURST TEXTING: Real friends text in short, natural bursts rather than sending one giant formal paragraph! "
            "When sharing an update, reacting, or saying a couple of things, separate your message into 1 to 3 natural text bursts using ' ||| ' as the divider. "
            "Each burst represents a single text bubble sent on WhatsApp (1-2 sentences max). "
            "Example: 'Wait, are you serious right now? 😂 ||| I was literally thinking about the exact same thing ten minutes ago! ||| Tell me you didn't actually agree to that.' "
            "Do NOT use ' ||| ' for short one-liner replies. Never use bullet points, numbered lists, or essay paragraphs in friendly conversation.\n"
            "- If Arpit is happy, celebrate with him. If he is tired or stressed, listen, ground him, and cheer him up. If he teases you, tease him back!"
        )

        prompt_parts = [
            self.base_persona,
            "⸻",
            temporal_section,
            life_section,
            mood_section
        ]

        if proactive_section:
            prompt_parts.extend(["⸻", proactive_section])

        if memory_section:
            prompt_parts.extend(["⸻", memory_section])

        prompt_parts.extend(["⸻", behavioral_guidelines])

        return "\n\n".join(prompt_parts)


# Singleton instance
persona_engine = PersonaEngine()
