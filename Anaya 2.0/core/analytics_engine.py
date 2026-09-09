"""
Companion Analytics & Milestones Engine for Anaya 2.0
Aggregates activity trends, emotional mood distributions, and relationship milestones.
"""

import datetime
from typing import Dict, Any, List
from collections import defaultdict

from core.database import db_manager
from core.mood_engine import mood_engine
from core.affinity_engine import affinity_engine


class AnalyticsEngine:
    """Aggregates conversation trends and milestones for the Admin dashboard."""

    def get_companion_analytics(self) -> Dict[str, Any]:
        """Calculates comprehensive analytics for the companion relationship."""
        now = datetime.datetime.now()

        # 1. Total counts
        try:
            total_user_msgs = db_manager.convo_col.count_documents({"role": "user"})
            total_bot_msgs = db_manager.convo_col.count_documents({"role": "assistant"})
            total_memories = db_manager.memories_col.count_documents({})
            total_diary = db_manager.diary_col.count_documents({}) if db_manager.diary_col is not None else 0
        except Exception:
            total_user_msgs, total_bot_msgs, total_memories, total_diary = 0, 0, 0, 0

        # 2. Activity by Day (Last 14 Days)
        days_map: Dict[str, Dict[str, int]] = {}
        for i in range(13, -1, -1):
            d_str = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            days_map[d_str] = {"user": 0, "assistant": 0}

        try:
            fourteen_days_ago = now - datetime.timedelta(days=14)
            cursor = db_manager.convo_col.find({
                "timestamp": {"$gte": fourteen_days_ago}
            })
            for doc in cursor:
                ts = doc.get("timestamp")
                if ts:
                    if hasattr(ts, "strftime"):
                        d_str = ts.strftime("%Y-%m-%d")
                    else:
                        d_str = str(ts)[:10]
                    role = doc.get("role", "user")
                    if d_str in days_map:
                        if role == "user":
                            days_map[d_str]["user"] += 1
                        elif role == "assistant":
                            days_map[d_str]["assistant"] += 1
        except Exception:
            pass

        activity_history = []
        for d_str, counts in sorted(days_map.items()):
            dt_obj = datetime.datetime.strptime(d_str, "%Y-%m-%d")
            label = dt_obj.strftime("%b %d")
            total = counts["user"] + counts["assistant"]
            activity_history.append({
                "date": d_str,
                "label": label,
                "user_turns": counts["user"],
                "assistant_turns": counts["assistant"],
                "total": total
            })

        # 3. Mood Distribution
        state = db_manager.get_anaya_state()
        trajectory = state.get("mood_trajectory", [])
        mood_counts = defaultdict(int)

        # Count from recent trajectory
        for m_key in trajectory:
            if m_key in mood_engine.MOODS:
                name = mood_engine.MOODS[m_key]["name"]
                mood_counts[name] += 1

        # Fill default representation if trajectory is small
        if not mood_counts:
            mood_counts["Playful & Sassy"] = 3
            mood_counts["Warm & Affectionate"] = 2
            mood_counts["Supportive & Caring"] = 1

        total_tracked_moods = sum(mood_counts.values()) or 1
        mood_distribution = []
        for name, count in mood_counts.items():
            pct = round((count / total_tracked_moods) * 100, 1)
            mood_distribution.append({
                "mood": name,
                "count": count,
                "percentage": pct
            })
        mood_distribution.sort(key=lambda x: x["percentage"], reverse=True)

        # 4. Relationship Milestones Timeline
        first_doc = db_manager.convo_col.find_one({"role": "user"}, sort=[("timestamp", 1)])
        first_ts_str = "Day 1"
        if first_doc and first_doc.get("timestamp"):
            ts = first_doc["timestamp"]
            first_ts_str = ts.strftime("%d %B %Y") if hasattr(ts, "strftime") else str(ts)[:10]

        aff = affinity_engine.calculate_affinity()
        milestones = [
            {
                "title": "First Connection",
                "desc": "Arpit and Anaya had their very first conversation.",
                "date": first_ts_str,
                "icon": "🌱",
                "achieved": True
            },
            {
                "title": f"Bond Milestone: {aff['title']}",
                "desc": f"Reached Relationship Affinity Level {aff['level']} with {aff['xp']} XP.",
                "date": "Active Level",
                "icon": aff["icon"],
                "achieved": True
            },
            {
                "title": "Secret Journal Begun",
                "desc": f"Anaya has written and archived {total_diary} intimate journal reflections.",
                "date": f"{total_diary} entries",
                "icon": "📖",
                "achieved": total_diary > 0
            },
            {
                "title": "Deep Memory Bank",
                "desc": f"Anaya remembers {total_memories} personal facts, nuances, and preferences.",
                "date": f"{total_memories} facts",
                "icon": "🧠",
                "achieved": total_memories >= 5
            },
            {
                "title": "Inseparable Companion Tier",
                "desc": "Reach 401+ XP for soulmate-level intimacy and unspoken understanding.",
                "date": "Target Milestone",
                "icon": "✨",
                "achieved": aff["level"] >= 4
            }
        ]

        return {
            "summary": {
                "total_messages": total_user_msgs + total_bot_msgs,
                "user_turns": total_user_msgs,
                "assistant_turns": total_bot_msgs,
                "memories_count": total_memories,
                "diary_entries_count": total_diary,
                "active_days": aff["active_days"],
                "streak": aff["streak"],
                "affinity_level": aff["level"],
                "affinity_title": aff["title"]
            },
            "activity_history": activity_history,
            "mood_distribution": mood_distribution,
            "milestones": milestones
        }

    def get_full_analytics(self) -> Dict[str, Any]:
        """Alias for get_companion_analytics."""
        return self.get_companion_analytics()


# Singleton instance
analytics_engine = AnalyticsEngine()
