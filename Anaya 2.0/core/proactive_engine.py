"""
Proactive Life Threads Engine for Anaya 2.0
Tracks Arpit's upcoming events, commitments, health status, and plans.
Enables Anaya to proactively check in like a real friend rather than waiting to be prompted.
"""

import re
import json
import datetime
from typing import Optional, Dict, Any, List

from core.database import db_manager
from core.llm_client import llm_client


class ProactiveEngine:
    """Manages open conversational loops and proactive follow-ups."""

    def detect_and_register_thread(self, user_text: str):
        """
        Analyzes user message to see if an upcoming event, plan, health issue,
        or commitment was mentioned that warrants following up.
        """
        clean_text = user_text.strip()
        if len(clean_text) < 15:
            return

        # Fast keyword check before calling LLM
        trigger_words = [
            "tomorrow", "later today", "meeting", "interview", "presentation",
            "doctor", "headache", "fever", "sick", "gym", "workout", "exam",
            "deadline", "appointment", "leaving for", "going to", "coding", "deploy", "travel"
        ]
        if not any(w in clean_text.lower() for w in trigger_words):
            return

        prompt = (
            "Analyze if the user mentions an upcoming event, appointment, task, health situation, "
            "or plan that a caring close friend should check in on later.\n"
            "If yes, extract as JSON:\n"
            "{\n"
            "  \"has_thread\": true,\n"
            "  \"topic\": \"short topic summary (e.g. 'Project Presentation', 'Doctor Appointment')\",\n"
            "  \"context\": \"brief details from message\",\n"
            "  \"follow_up_hint\": \"friendly question Anaya can ask when they next talk\"\n"
            "}\n"
            "If no future event or follow-up is needed, return {\"has_thread\": false}.\n\n"
            f"User message: \"{clean_text}\"\n\nJSON:"
        )

        try:
            raw_result = llm_client.chat_sync(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            json_match = re.search(r"\{.*?\}", raw_result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if parsed.get("has_thread") and parsed.get("topic"):
                    topic = parsed["topic"].strip()
                    context = parsed.get("context", clean_text).strip()
                    hint = parsed.get("follow_up_hint", "").strip()
                    db_manager.add_life_thread(
                        topic=topic,
                        context=context,
                        follow_up_hint=hint,
                        category="life_event"
                    )
        except Exception:
            pass

    def get_pending_checkin(self) -> Optional[Dict[str, Any]]:
        """
        Finds an open thread that has not been checked in on yet.
        """
        threads = db_manager.get_active_life_threads(limit=3)
        for t in threads:
            if t.get("check_in_count", 0) == 0:
                return t
        return None

    def generate_proactive_prompt(self, is_session_start: bool = False) -> str:
        """
        Injects instructions for Anaya to bring up an open thread naturally.
        """
        pending = self.get_pending_checkin()
        if not pending:
            return ""

        topic = pending.get("topic", "")
        context = pending.get("context", "")
        hint = pending.get("follow_up_hint", "")

        return (
            f"PROACTIVE FRIEND CHECK-IN (High Priority):\n"
            f"- Earlier, Arpit mentioned: '{topic}' ({context}).\n"
            f"- Friendly follow-up idea: '{hint}'.\n"
            f"- Guideline: Like a real, attentive friend, warmly ask Arpit how it went or how he is doing with it! "
            f"Don't sound scripted—make it feel like it was naturally on your mind."
        )


# Singleton instance
proactive_engine = ProactiveEngine()
