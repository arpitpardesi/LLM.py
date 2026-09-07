"""
Voice Engine for Anaya 2.0
Provides high-fidelity Neural Text-To-Speech (TTS) using edge-tts
with expressive Indian English and Hindi neural voices.
"""

import os
import re
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

CURRENT_DIR = Path(__file__).resolve().parent
STATIC_AUDIO_DIR = CURRENT_DIR.parent / "web" / "static" / "audio_cache"
STATIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

AVAILABLE_VOICES = [
    {
        "id": "en-IN-NeerjaExpressiveNeural",
        "name": "Neerja (Expressive & Warm)",
        "lang": "en-IN",
        "gender": "Female",
        "vibe": "Warm, emotional, authentic Indian English"
    },
    {
        "id": "en-IN-NeerjaNeural",
        "name": "Neerja (Calm & Friendly)",
        "lang": "en-IN",
        "gender": "Female",
        "vibe": "Gentle, balanced conversational"
    },
    {
        "id": "hi-IN-SwaraNeural",
        "name": "Swara (Bilingual Warmth)",
        "lang": "hi-IN",
        "gender": "Female",
        "vibe": "Sweet, expressive Hindi/English flow"
    },
    {
        "id": "en-IN-PrabhatNeural",
        "name": "Prabhat (Male)",
        "lang": "en-IN",
        "gender": "Male",
        "vibe": "Friendly, confident Indian English"
    }
]

DEFAULT_VOICE = "en-IN-NeerjaExpressiveNeural"


class VoiceEngine:
    """Manages neural voice synthesis and audio caching."""

    def __init__(self):
        self.default_voice = DEFAULT_VOICE
        self.audio_dir = STATIC_AUDIO_DIR

    def get_voices(self) -> List[Dict[str, Any]]:
        """Returns list of available Indian neural voices."""
        return AVAILABLE_VOICES

    def clean_text_for_speech(self, text: str) -> str:
        """
        Removes emojis, markdown artifacts, action descriptors (*smiles*, *sighs*),
        and burst separators (|||) so the neural voice sounds completely natural.
        """
        if not text:
            return ""

        # Remove burst separators
        clean = text.replace("|||", ". ")

        # Remove stage actions inside asterisks like *laughs softly*, *grins*
        clean = re.sub(r"\*[^*]+\*", "", clean)

        # Remove URLs
        clean = re.sub(r"https?://\S+", "", clean)

        # Remove markdown symbols: #, `, _, ~
        clean = re.sub(r"[#`_~>]", "", clean)

        # Remove common emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # Supplemental symbols
            "\U0001FA00-\U0001FA6F"  # Chess / symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and pictographs extended-A
            "]+",
            flags=re.UNICODE,
        )
        clean = emoji_pattern.sub("", clean)

        # Clean multiple spaces and newlines
        clean = re.sub(r"\s+", " ", clean).strip()

        return clean

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generates or retrieves cached MP3 audio for given text.
        Returns audio URL, duration estimate, and metadata.
        """
        clean = self.clean_text_for_speech(text)
        if not clean:
            return None

        chosen_voice = voice or self.default_voice

        # Check if chosen voice is valid, else fallback
        valid_voice_ids = [v["id"] for v in AVAILABLE_VOICES]
        if chosen_voice not in valid_voice_ids:
            chosen_voice = self.default_voice

        # Create unique MD5 hash for (voice + cleaned text)
        hash_input = f"{chosen_voice}:{clean}".encode("utf-8")
        file_hash = hashlib.md5(hash_input).hexdigest()
        filename = f"anaya_{file_hash}.mp3"
        file_path = self.audio_dir / filename
        audio_url = f"/static/audio_cache/{filename}"

        if file_path.exists() and file_path.stat().st_size > 0:
            return {
                "audio_url": audio_url,
                "text": clean,
                "voice": chosen_voice,
                "cached": True
            }

        try:
            import edge_tts
            communicate = edge_tts.Communicate(clean, chosen_voice)
            await communicate.save(str(file_path))

            # Standardize MP3 encoding to 44.1kHz stereo to ensure universal browser & CoreAudio compatibility
            std_path = file_path.with_suffix(".std.mp3")
            try:
                import shutil
                conv_bin = shutil.which("ffmpeg")
                if conv_bin:
                    proc = await asyncio.create_subprocess_exec(
                        conv_bin, "-y", "-i", str(file_path), "-ar", "44100", "-ac", "2", str(std_path),
                        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                    )
                    await proc.communicate()
                    if std_path.exists() and std_path.stat().st_size > 0:
                        std_path.replace(file_path)
            except Exception as conv_err:
                print(f"[VoiceEngine Warning] Audio standardization skipped: {conv_err}")

            return {
                "audio_url": audio_url,
                "text": clean,
                "voice": chosen_voice,
                "cached": False
            }
        except Exception as e:
            print(f"[VoiceEngine Error] Synthesis failed: {e}")
            return None


# Singleton instance
voice_engine = VoiceEngine()
