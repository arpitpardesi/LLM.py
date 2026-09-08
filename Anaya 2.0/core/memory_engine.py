"""
Memory Engine for Anaya 2.0
Manages dual-tier memory: Sliding context window + Long-term user facts & episodic extraction.
"""

import json
import re
from typing import List, Dict, Any, Optional
import datetime

from config import config
from core.database import db_manager
from core.persona import persona_engine
from core.llm_client import llm_client


class MemoryEngine:
    """Orchestrates short-term context assembly and long-term memory extraction."""

    def __init__(self):
        self.config = config.llm

    def build_chat_context(self, session_id: str) -> List[Dict[str, str]]:
        """
        Builds the complete message payload for Ollama:
        1. System message: Persona + Temporal Awareness + User Memories + Style
        2. Sliding window of recent message history
        """
        # Fetch last message to determine elapsed time
        last_msg = db_manager.get_last_message()
        last_time = last_msg.get("timestamp") if last_msg else None

        # Fetch stored user memories
        memories = db_manager.get_all_memories()

        # Build dynamic system prompt
        system_prompt = persona_engine.build_system_prompt(
            last_interaction_time=last_time,
            memories=memories
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Fetch recent messages (sliding window)
        recent_docs = db_manager.load_recent_messages(limit=self.config.context_window_turns)
        for doc in recent_docs:
            role = doc.get("role", "user")
            content = doc.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})

        return messages

    def extract_and_save_facts(self, user_text: str):
        """
        Inspects user input for notable personal facts, preferences, emotions, or life events.
        Extracts them using Ollama in the background and saves to MongoDB.
        Also triggers proactive thread detection and mood shift evaluation.
        """
        from core.proactive_engine import proactive_engine
        from core.mood_engine import mood_engine

        # 1. Update Anaya's emotional momentum based on user's tone
        try:
            mood_engine.evaluate_conversational_shift(user_text)
        except Exception:
            pass

        # 2. Check for upcoming life events/threads
        try:
            proactive_engine.detect_and_register_thread(user_text)
        except Exception:
            pass

        if not config.enable_fact_extraction:
            return

        # Skip very short or trivial conversational inputs
        clean_text = user_text.strip()
        if len(clean_text) < 14:
            return

        lower_text = clean_text.lower()
        if lower_text in [
            "hi", "hello", "hey", "how are you", "what's up", "yes", "no", "ok", "bye", "good night", "gn"
        ]:
            return

        # If the user is asking a general question without personal markers, skip fact extraction
        personal_markers = [
            "i ", "i'm", "im ", "my ", "mine", "me ", "we ", "our", "i've", "ive ", "i'll", "ill ",
            "i like", "i love", "i hate", "i feel", "i want", "i prefer", "started", "bought", "working on"
        ]
        if lower_text.endswith("?") and not any(p in lower_text for p in personal_markers):
            return

        # Also skip short non-personal phrases under 35 chars
        if len(clean_text) < 35 and not any(p in lower_text for p in personal_markers):
            return

        extraction_prompt = (
            "Analyze the following user message from Arpit (28) speaking with Anaya. "
            "Identify if he shares a durable personal fact about himself (e.g. his hobbies, work, daily routine, "
            "food/music preferences, health, or his bond/affection with Anaya).\n"
            "DO NOT extract vague single-word items like 'feeling', 'person', 'you', 'kisses'. "
            "Only extract meaningful, complete narrative facts.\n\n"
            "Format strictly as JSON:\n"
            "{\n"
            "  \"has_fact\": true,\n"
            "  \"key\": \"Descriptive title (e.g. 'Coffee preference', 'Work tech stack', 'Romantic affection for Anaya')\",\n"
            "  \"value\": \"Complete narrative sentence describing the fact accurately\",\n"
            "  \"category\": \"profile\" | \"bond\" | \"preference\" | \"work\" | \"health\"\n"
            "}\n"
            "If no meaningful fact was shared, return {\"has_fact\": false}.\n\n"
            f"User message: \"{clean_text}\"\n\nJSON:"
        )

        try:
            raw_result = llm_client.chat_sync(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                num_ctx=getattr(self.config, "num_ctx_internal", 768)
            )
            json_match = re.search(r"\{.*?\}", raw_result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if parsed.get("has_fact") and parsed.get("key") and parsed.get("value"):
                    key = parsed["key"].strip()
                    value = parsed["value"].strip()
                    category = parsed.get("category", "general").strip()
                    # Filter out short or junk single-word extractions
                    if len(value) >= 8 and value.lower() not in ["feeling", "you", "my girl", "person", "amazing"]:
                        db_manager.save_memory_fact(key=key, value=value, category=category)
        except Exception:
            # Memory extraction failure is non-blocking and silent to keep chat smooth
            pass

    def add_manual_fact(self, fact_text: str) -> bool:
        """Allows user to manually add a memory via /remember command."""
        # Split on ':' or '-' if provided, else use the whole text
        if ":" in fact_text:
            key, val = fact_text.split(":", 1)
        elif "-" in fact_text:
            key, val = fact_text.split("-", 1)
        else:
            key = fact_text[:30]
            val = fact_text

        return db_manager.save_memory_fact(
            key=key.strip(),
            value=val.strip(),
            category="manual"
        )

    def forget_fact(self, key: str) -> bool:
        """Deletes a memory fact."""
        return db_manager.delete_memory(key)

    def get_all_facts(self) -> List[Dict[str, Any]]:
        """Returns all remembered facts."""
        return db_manager.get_all_memories()


# Singleton instance
memory_engine = MemoryEngine()
