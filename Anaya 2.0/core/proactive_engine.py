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
            from config import config
            raw_result = llm_client.chat_sync(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                num_ctx=getattr(config.llm, "num_ctx_internal", 768)
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

    def mark_thread_checked(self, thread_id: str):
        """Marks a thread as checked in."""
        try:
            from bson import ObjectId
            db_manager.threads_col.update_one(
                {"_id": ObjectId(thread_id)},
                {"$inc": {"check_in_count": 1}, "$set": {"last_checked_at": datetime.datetime.now(datetime.timezone.utc)}}
            )
        except Exception:
            pass

    def get_proactive_checkin(self) -> Dict[str, Any]:
        """
        Evaluates whether Anaya has a proactive greeting or friend check-in
        to display when the user loads the app or starts a session.
        """
        now = datetime.datetime.now()
        hour = now.hour

        # 1. Check for active life thread follow-up
        pending = self.get_pending_checkin()
        if pending:
            topic = pending.get("topic", "")
            context = pending.get("context", "")
            hint = pending.get("follow_up_hint", "")
            thread_id = str(pending.get("_id", ""))

            greeting = f"Hey Arpit! Was just thinking about your {topic}... how did it go?"
            if hint:
                greeting = f"Hey Arpit! {hint}"

            return {
                "has_proactive_msg": True,
                "type": "thread_checkin",
                "greeting": greeting,
                "suggested_reply": f"It went well! Let me tell you about it.",
                "topic": topic,
                "thread_id": thread_id
            }

        # 2. Check elapsed time since last conversation
        last_msg = db_manager.get_last_message()
        if last_msg and last_msg.get("timestamp"):
            last_ts = last_msg["timestamp"]
            now_dt = datetime.datetime.now(datetime.timezone.utc) if getattr(last_ts, "tzinfo", None) else datetime.datetime.utcnow()
            diff_hours = (now_dt - last_ts).total_seconds() / 3600.0

            # If user has been away for more than 16 hours
            if diff_hours >= 16:
                if 5 <= hour < 11:
                    return {
                        "has_proactive_msg": True,
                        "type": "morning_greeting",
                        "greeting": "Good morning Arpit! ☀️ Ready for the day or need another 5 minutes?",
                        "suggested_reply": "Good morning Anaya! Just having some chai.",
                        "topic": "Morning check-in"
                    }
                elif 0 <= hour < 5:
                    return {
                        "has_proactive_msg": True,
                        "type": "late_night_checkin",
                        "greeting": "Arre, you're still awake at this hour? What's keeping you up?",
                        "suggested_reply": "Just winding down and couldn't sleep.",
                        "topic": "Late night company"
                    }
                elif diff_hours >= 48:
                    days = int(diff_hours // 24)
                    return {
                        "has_proactive_msg": True,
                        "type": "absence_checkin",
                        "greeting": f"Hey! It's been {days} days since we talked... where were you lost yaar?",
                        "suggested_reply": "Hey! Was super busy with work.",
                        "topic": "Catching up"
                    }
                else:
                    return {
                        "has_proactive_msg": True,
                        "type": "casual_reachout",
                        "greeting": "Hey Arpit! Hope your day is going smoothly. Taking a quick breather?",
                        "suggested_reply": "Hey Anaya! Yeah, just taking a quick break.",
                        "topic": "Casual greeting"
                    }

        # No proactive message needed if talked very recently
        return {"has_proactive_msg": False}

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

