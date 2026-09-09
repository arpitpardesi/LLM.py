"""
Media & Cultural Atmosphere Engine for Anaya 2.0
Handles inline music detection, Spotify/YouTube search card generation,
and Anaya's visual daily moments / camera roll.
"""

import re
import urllib.parse
from typing import List, Dict, Any, Optional
import datetime


class MediaEngine:
    """Manages cultural music enrichment and visual atmospheric moments."""

    # Curated atmospheric snapshots corresponding to her daily routine phases
    MOMENTS = [
        {
            "id": "morning_chai",
            "period": "morning",
            "title": "Morning Chai on the Balcony",
            "time_hint": "7:30 AM",
            "mood": "Fresh & Calm",
            "caption": "Steaming ginger-cardamom chai, cool breeze, and listening to the city slowly wake up. ☕🌿",
            "gradient": "linear-gradient(135deg, #f59e0b, #fbbf24, #d97706)",
            "icon": "☕"
        },
        {
            "id": "afternoon_desk",
            "period": "afternoon",
            "title": "Afternoon Work & Coffee",
            "time_hint": "2:45 PM",
            "mood": "Playful & Focused",
            "caption": "Fighting the post-lunch slump with an iced latte and 47 open browser tabs. Send snacks! 💻🥪",
            "gradient": "linear-gradient(135deg, #6366f1, #8b5cf6, #3b82f6)",
            "icon": "💻"
        },
        {
            "id": "evening_walk",
            "period": "evening",
            "title": "Sunset Neighborhood Walk",
            "time_hint": "6:15 PM",
            "mood": "Grounded & Vibrant",
            "caption": "The sky turned this unbelievable shade of peach and violet today. Worth stepping out for. 🌅🚶‍♀️",
            "gradient": "linear-gradient(135deg, #ec4899, #f43f5e, #fb923c)",
            "icon": "🌅"
        },
        {
            "id": "midnight_cozy",
            "period": "night",
            "title": "Midnight Cozy Headspace",
            "time_hint": "11:45 PM",
            "mood": "Soulful & Intimate",
            "caption": "Warm fairy lights dimmed, soft lo-fi in headphones, and staring at the ceiling thinking about life. ✨📖",
            "gradient": "linear-gradient(135deg, #1e1b4b, #312e81, #4c1d95)",
            "icon": "🌙"
        }
    ]

    def extract_music_card(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detects song mentions in Anaya's message (e.g. **'Alag Aasmaan' by Anuv Jain**)
        and produces structured media card payload.
        """
        # Pattern 1: **'Title' by Artist** or **"Title" by Artist**
        match = re.search(r"[\*\"']{1,2}(.+?)[\*\"']{1,2}\s+by\s+([A-Za-z0-9\s&]+)", text, re.IGNORECASE)
        if not match:
            # Pattern 2: 'Title' - Artist
            match = re.search(r"['\"]([^'\"]{3,40})['\"]\s*[-–—]\s*([A-Za-z0-9\s&]{2,30})", text)

        if match:
            title = match.group(1).strip()
            artist = match.group(2).strip()
            # Clean possible markdown asterisks and surrounding quotes
            title = re.sub(r"[\*\_]", "", title).strip("\"' ")
            artist = re.sub(r"[\*\_]", "", artist).strip("\"' ")

            if len(title) >= 2 and len(artist) >= 2:
                query = f"{title} {artist}"
                encoded_q = urllib.parse.quote_plus(query)
                return {
                    "has_media": True,
                    "media_type": "music",
                    "title": title,
                    "artist": artist,
                    "youtube_url": f"https://www.youtube.com/results?search_query={encoded_q}",
                    "spotify_url": f"https://open.spotify.com/search/{encoded_q}"
                }

        return None

    def get_moments(self) -> List[Dict[str, Any]]:
        """Returns all curated camera roll moments."""
        return self.MOMENTS

    def get_all_moments(self) -> List[Dict[str, Any]]:
        """Alias for get_moments."""
        return self.get_moments()

    def detect_song_recommendation(self, text: str) -> Optional[Dict[str, Any]]:
        """Alias for extract_music_card."""
        return self.extract_music_card(text)

    def get_current_moment(self) -> Dict[str, Any]:
        """Returns the moment that corresponds to the active hour."""
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return self.MOMENTS[0]
        elif 12 <= hour < 17:
            return self.MOMENTS[1]
        elif 17 <= hour < 21:
            return self.MOMENTS[2]
        else:
            return self.MOMENTS[3]


# Singleton instance
media_engine = MediaEngine()
