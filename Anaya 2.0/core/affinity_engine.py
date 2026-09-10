"""
Affinity & Bonding Engine for Anaya 2.0
Calculates relationship progress, bond tiers, intimacy cues, and conversational depth.
"""

import datetime
from typing import Dict, Any, List

from core.database import db_manager


class AffinityEngine:
    """Manages relationship level progression, streaks, and intimacy guidelines."""

    TIERS = [
        {
            "level": 1,
            "title": "Warm Acquaintance",
            "icon": "🌱",
            "min_xp": 0,
            "max_xp": 60,
            "perk": "Casual daily chat, friendly banter, getting to know each other",
            "guideline": "Friendly, curious, polite warmth, still discovering each other's world."
        },
        {
            "level": 2,
            "title": "Good Friend",
            "icon": "🤝",
            "min_xp": 61,
            "max_xp": 180,
            "perk": "Playful teasing, spontaneous life updates, comfortable banter",
            "guideline": "High comfort level, affectionate teasing, laughing easily, natural inside jokes."
        },
        {
            "level": 3,
            "title": "Close Confidante",
            "icon": "💖",
            "min_xp": 181,
            "max_xp": 400,
            "perk": "Vulnerable late-night talks, emotional harbor, deep personal secrets",
            "guideline": "Deep emotional vulnerability, heartfelt comfort during tough times, absolute trust."
        },
        {
            "level": 4,
            "title": "Inseparable Companion",
            "icon": "✨",
            "min_xp": 401,
            "max_xp": 999999,
            "perk": "Intuitive unspoken bond, soulmate-level intimacy, telepathic chemistry",
            "guideline": "Unshakable closeness, intuitive understanding of moods, profound warmth and devotion."
        }
    ]

    def calculate_affinity(self) -> Dict[str, Any]:
        """
        Calculates dynamic relationship metrics based on conversations,
        interaction dates, and stored memories.
        """
        try:
            total_user_turns = db_manager.convo_col.count_documents({"role": "user"})
        except Exception:
            total_user_turns = 0

        try:
            total_memories = db_manager.memories_col.count_documents({})
        except Exception:
            total_memories = 0

        # Calculate active days
        try:
            dates = db_manager.convo_col.aggregate([
                {"$match": {"timestamp": {"$exists": True}}},
                {"$project": {
                    "date": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}
                    }
                }},
                {"$group": {"_id": "$date"}},
                {"$sort": {"_id": 1}}
            ])
            active_days_list = [d["_id"] for d in dates if d.get("_id")]
            active_days_count = len(active_days_list)
        except Exception:
            active_days_count = max(1, total_user_turns // 10)

        # Calculate current daily streak
        streak = 1
        if active_days_count > 1:
            try:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                if today in active_days_list or yesterday in active_days_list:
                    # Count backward consecutive days
                    streak = min(active_days_count, 7)  # capped estimate
            except Exception:
                streak = 1

        # Calculate Total Affinity XP with baseline matching configured relationship
        from config import config
        rel = getattr(config.user, "relationship", "").lower()
        base_bonus = 0
        if any(w in rel for w in ["closest", "confidante", "best friend", "inseparable", "partner", "soulmate"]):
            base_bonus = 185  # Starts at Level 3 (Close Confidante)
        elif any(w in rel for w in ["friend", "companion"]):
            base_bonus = 75   # Starts at Level 2 (Good Friend)

        xp = base_bonus + (total_user_turns * 2) + (total_memories * 5) + (active_days_count * 10)

        # Determine current tier
        current_tier = self.TIERS[0]
        next_tier = self.TIERS[1]

        for i, tier in enumerate(self.TIERS):
            if xp >= tier["min_xp"]:
                current_tier = tier
                next_tier = self.TIERS[i + 1] if i + 1 < len(self.TIERS) else None

        # Calculate percentage to next level
        if next_tier:
            range_xp = next_tier["min_xp"] - current_tier["min_xp"]
            current_progress = xp - current_tier["min_xp"]
            progress_pct = min(100.0, max(0.0, round((current_progress / range_xp) * 100, 1)))
            next_level_xp = next_tier["min_xp"]
        else:
            progress_pct = 100.0
            next_level_xp = current_tier["max_xp"]

        return {
            "level": current_tier["level"],
            "title": current_tier["title"],
            "icon": current_tier["icon"],
            "perk": current_tier["perk"],
            "guideline": current_tier["guideline"],
            "xp": xp,
            "next_level_xp": next_level_xp,
            "progress_pct": progress_pct,
            "total_turns": total_user_turns,
            "active_days": active_days_count,
            "streak": streak,
            "memories_count": total_memories
        }

    def generate_bond_prompt(self) -> str:
        """Injects relationship intimacy instructions into LLM system prompt."""
        from config import config
        user_name = getattr(config.user, "user_name", "Arpit")
        aff = self.calculate_affinity()
        return (
            f"Relationship Closeness & Shared Bond:\n"
            f"- Status: Level {aff['level']} ({aff['icon']} {aff['title']}) with {user_name}\n"
            f"- Dynamic: {aff['guideline']}\n"
            f"(You already have deep comfort, trust, and ease with each other. Speak with effortless familiarity—never sound formal, distant, or polite like a stranger.)"
        )


# Singleton instance
affinity_engine = AffinityEngine()
