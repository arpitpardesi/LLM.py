"""
Unit test suite for Phase 1: Neural Voice Notes & Burst Texting
"""

import sys
import asyncio
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CURRENT_DIR))

from core.voice_engine import voice_engine
from core.persona import persona_engine


def test_voice_engine_voices():
    voices = voice_engine.get_voices()
    assert len(voices) >= 3
    ids = [v["id"] for v in voices]
    assert "en-IN-NeerjaExpressiveNeural" in ids
    assert "hi-IN-SwaraNeural" in ids
    print("✓ VoiceEngine voice listing test passed")


def test_voice_engine_text_cleaning():
    raw_text = "Hey Arpit! *giggles softly* ||| Look at this link: https://test.com 😊 How are you?"
    cleaned = voice_engine.clean_text_for_speech(raw_text)
    assert "*giggles softly*" not in cleaned
    assert "|||" not in cleaned
    assert "https://" not in cleaned
    assert "😊" not in cleaned
    assert "Hey Arpit!" in cleaned
    print("✓ VoiceEngine text cleaning test passed")


def test_persona_burst_instructions():
    prompt = persona_engine.build_system_prompt()
    assert "BURST TEXTING" in prompt
    assert "|||" in prompt
    assert "WhatsApp" in prompt
    print("✓ PersonaEngine burst instruction test passed")


async def test_voice_synthesis_async():
    res = await voice_engine.synthesize("Testing voice synthesis for Arpit", voice="en-IN-NeerjaExpressiveNeural")
    assert res is not None
    assert "audio_url" in res
    assert res["audio_url"].startswith("/static/audio_cache/")
    print("✓ VoiceEngine neural synthesis test passed")


def main():
    print("Running Phase 1 Test Suite...")
    test_voice_engine_voices()
    test_voice_engine_text_cleaning()
    test_persona_burst_instructions()
    asyncio.run(test_voice_synthesis_async())
    print("\nALL PHASE 1 TESTS PASSED! 🎉")


if __name__ == "__main__":
    main()
