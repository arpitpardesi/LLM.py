#!/usr/bin/env python3
"""
Anaya 2.0 - Next-Gen Human-Like AI Companion
Main executable entry point.

Run:
    python3 anaya.py
"""

import os
import sys
import uuid
import signal
import argparse
from pathlib import Path

# Auto-detect and switch to project .venv python if started with system python missing dependencies
ANAYA_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANAYA_DIR.parent
VENV_PY = ROOT_DIR / ".venv" / "bin" / "python3"
if VENV_PY.exists() and sys.executable != str(VENV_PY):
    try:
        import pymongo, rich
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

# Add current directory to path
if str(ANAYA_DIR) not in sys.path:
    sys.path.insert(0, str(ANAYA_DIR))

from config import config
from core.database import db_manager
from core.llm_client import llm_client
from core.memory_engine import memory_engine
from core.persona import persona_engine
from cli.ui import (
    console,
    print_banner,
    print_user_prompt,
    start_anaya_stream,
    stream_token,
    end_anaya_stream,
    print_system_message,
    print_warning_message,
    print_error_message
)
from cli.commands import command_dispatcher


def initialize_environment(session_id: str):
    """Checks database, ensures personality document, and verifies models."""
    db_ok, db_msg = db_manager.health_check()
    if not db_ok:
        print_warning_message(f"Database warning: {db_msg}. Chat will proceed with local cache.")

    # Verify Ollama service & active model
    llm_ok, llm_msg = llm_client.verify_model()
    if not llm_ok:
        print_warning_message(f"Ollama warning: {llm_msg}")

    # Seed personality into MongoDB dialogID 1 if collection is empty
    ensure_personality_seed(session_id)

    # Record session start
    db_manager.start_session(session_id, metadata={"model": llm_client.active_model})
    return db_ok


def ensure_personality_seed(session_id: str):
    """Ensures document 1 exists with personality instructions if collection is fresh."""
    try:
        if db_manager.convo_col is not None and db_manager.convo_col.count_documents({}) == 0:
            personality_content = persona_engine.base_persona
            db_manager.save_message(
                role="assistant",
                content=personality_content,
                session_id=session_id,
                dialog_id=1,
                metadata={"is_seed_personality": True}
            )
    except Exception:
        pass


def chat_turn(user_input: str, session_id: str) -> str:
    """Executes a single conversational turn with streaming."""
    # 1. Save user input
    dialog_id = db_manager.get_next_dialog_id()
    db_manager.save_message(
        role="user",
        content=user_input,
        session_id=session_id,
        dialog_id=dialog_id
    )

    # 2. Extract facts in background
    try:
        memory_engine.extract_and_save_facts(user_input)
    except Exception:
        pass

    # 3. Assemble chat context
    messages = memory_engine.build_chat_context(session_id=session_id)

    # 4. Stream response from Ollama
    start_anaya_stream()
    full_response = ""
    try:
        for chunk in llm_client.stream_chat(messages=messages):
            stream_token(chunk)
            full_response += chunk
    except KeyboardInterrupt:
        print_system_message("\n(Response paused)")
    finally:
        end_anaya_stream()

    # 5. Save assistant response
    if full_response.strip():
        bot_dialog_id = db_manager.get_next_dialog_id()
        db_manager.save_message(
            role="assistant",
            content=full_response.strip(),
            session_id=session_id,
            dialog_id=bot_dialog_id
        )

    return full_response


def main():
    """Main conversational loop for Anaya 2.0."""
    parser = argparse.ArgumentParser(description="Anaya 2.0 AI Companion")
    parser.add_argument("--model", type=str, help="Override active Ollama model")
    parser.add_argument("--no-banner", action="store_true", help="Omit startup banner")
    parser.add_argument("--ui", "--web", action="store_true", dest="web_mode", help="Launch the Web UI in browser")
    parser.add_argument("--port", type=int, default=8000, help="Port for Web UI server (default: 8000)")
    args = parser.parse_args()

    if args.web_mode:
        import webbrowser
        from server import start_server
        print("=" * 50)
        print(f"✨ Launching Anaya 2.0 Web UI at http://localhost:{args.port} ✨")
        print("=" * 50)
        webbrowser.open(f"http://localhost:{args.port}")
        start_server(port=args.port)
        return

    if args.model:
        llm_client.switch_model(args.model)

    session_id = str(uuid.uuid4())
    db_status = initialize_environment(session_id)

    if not args.no_banner:
        print_banner(
            model_name=llm_client.active_model,
            db_status=db_status,
            session_id=session_id
        )

    # Handle graceful exit on SIGINT
    def signal_handler(sig, frame):
        print_system_message("\nClosing session. See you soon, Arpit! ✨")
        db_manager.end_session(session_id)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Check if there is an unaddressed message from previous session
    last_msg = db_manager.get_last_message()
    if last_msg and last_msg.get("role") == "user":
        unaddressed_content = last_msg.get("content", "")
        print_system_message("Responding to your last open message...")
        chat_turn(unaddressed_content, session_id)

    # Primary interaction loop
    message_count = 0
    while True:
        try:
            user_input = print_user_prompt()

            if not user_input:
                continue

            # Check for slash commands (/help, /facts, /remember, /bye, etc.)
            if user_input.startswith("/"):
                handled, should_exit = command_dispatcher.handle_command(user_input)
                if should_exit:
                    break
                if handled:
                    continue

            # Standard chat turn
            message_count += 1
            chat_turn(user_input, session_id)

        except (KeyboardInterrupt, EOFError):
            print_system_message("\nClosing session. See you soon, Arpit! ✨")
            break
        except Exception as e:
            print_error_message(f"Unexpected error: {e}")

    # End session cleanly
    db_manager.end_session(session_id, message_count=message_count)


if __name__ == "__main__":
    main()
