"""
Command Dispatcher for Anaya 2.0
Handles in-chat slash commands like /facts, /remember, /forget, /model, /stats, etc.
"""

import datetime
from pathlib import Path
from typing import Tuple, Optional

from config import config
from core.database import db_manager
from core.llm_client import llm_client
from core.memory_engine import memory_engine
from cli.ui import (
    print_help_menu,
    print_memories_table,
    print_stats_panel,
    print_history_table,
    print_system_message,
    print_warning_message,
    print_error_message,
    print_life_panel,
    print_mood_panel,
    print_threads_table,
    print_diary_panel,
    console,
)


class CommandDispatcher:
    """Processes slash commands invoked during interactive chat."""

    @staticmethod
    def handle_command(command_str: str) -> Tuple[bool, bool]:
        """
        Executes a slash command.
        Returns (is_handled: bool, should_exit: bool).
        """
        parts = command_str.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ["/exit", "/bye", "/quit"]:
            print_system_message("Saving session and closing Anaya. Take care, Arpit! 👋")
            return True, True

        if cmd in ["/help", "/commands", "/?"]:
            print_help_menu()
            return True, False

        if cmd in ["/facts", "/memory", "/memories"]:
            memories = memory_engine.get_all_facts()
            print_memories_table(memories)
            return True, False

        if cmd == "/remember":
            if not args:
                print_warning_message("Usage: /remember <fact or preference>")
                print_warning_message("Example: /remember Favorite coffee: Cappuccino with cinnamon")
                return True, False
            ok = memory_engine.add_manual_fact(args)
            if ok:
                print_system_message(f"Anaya committed this to long-term memory: '{args}' ✨")
            else:
                print_error_message("Failed to save memory to database.")
            return True, False

        if cmd in ["/undo", "/delturn"]:
            turns = 1
            if args and args.isdigit():
                turns = max(1, int(args))
            count, docs = db_manager.delete_last_n_turns(n_turns=turns)
            if count > 0:
                print_system_message(f"Undid last {turns} conversation turn(s) ({count} messages removed).")
                for d in reversed(docs):
                    role_tag = "Arpit" if d.get("role") == "user" else "Anaya"
                    preview = d.get("content", "").replace("\n", " ")[:60]
                    print_system_message(f"  • Deleted {role_tag}: \"{preview}...\"")
            else:
                print_warning_message("No recent conversation turns to undo.")
            return True, False

        if cmd in ["/delete", "/pop", "/remove"]:
            # Check if user specified turns: /delete turns 2
            if args.lower().startswith("turn"):
                sub_parts = args.split()
                turns = 1
                if len(sub_parts) > 1 and sub_parts[1].isdigit():
                    turns = max(1, int(sub_parts[1]))
                count, docs = db_manager.delete_last_n_turns(n_turns=turns)
                if count > 0:
                    print_system_message(f"Deleted last {turns} turn(s) ({count} messages removed).")
                    for d in reversed(docs):
                        role_tag = "Arpit" if d.get("role") == "user" else "Anaya"
                        preview = d.get("content", "").replace("\n", " ")[:60]
                        print_system_message(f"  • Deleted {role_tag}: \"{preview}...\"")
                else:
                    print_warning_message("No messages available to delete.")
                return True, False

            n = 1
            if args and args.isdigit():
                n = max(1, int(args))
            count, docs = db_manager.delete_last_n_messages(n=n)
            if count > 0:
                print_system_message(f"Deleted last {count} message(s) from database.")
                for d in reversed(docs):
                    role_tag = "Arpit" if d.get("role") == "user" else "Anaya"
                    preview = d.get("content", "").replace("\n", " ")[:60]
                    print_system_message(f"  • Deleted {role_tag}: \"{preview}...\"")
            else:
                print_warning_message("No messages available to delete.")
            return True, False

        if cmd == "/forget":
            if not args:
                print_warning_message("Usage: /forget <fact key>")
                print_warning_message("Check '/facts' to find keys to remove.")
                return True, False
            ok = memory_engine.forget_fact(args)
            if ok:
                print_system_message(f"Removed '{args}' from Anaya's memory.")
            else:
                print_warning_message(f"Could not find or delete '{args}'.")
            return True, False

        if cmd == "/model":
            available = llm_client.list_models()
            if not args:
                print_system_message(f"Current active model: [bold]{llm_client.active_model}[/bold]")
                print_system_message(f"Available installed models: {', '.join(available)}")
                print_system_message("To switch, type: /model <model_name>")
                return True, False
            
            ok, msg = llm_client.switch_model(args)
            if ok:
                print_system_message(msg)
            else:
                print_warning_message(msg)
            return True, False

        if cmd == "/stats":
            stats = db_manager.get_session_stats()
            print_stats_panel(stats)
            return True, False

        if cmd == "/history":
            limit = 10
            if args and args.isdigit():
                limit = int(args)
            messages = db_manager.load_recent_messages(limit=limit)
            print_history_table(messages)
            return True, False

        if cmd == "/search":
            if not args:
                print_warning_message("Usage: /search <keyword>")
                return True, False
            results = db_manager.search_messages(keyword=args, limit=10)
            if not results:
                print_system_message(f"No past messages found mentioning '{args}'.")
            else:
                print_history_table(results)
            return True, False

        if cmd == "/life":
            from core.life_engine import life_engine
            info = life_engine.get_current_activity()
            print_life_panel(info)
            return True, False

        if cmd == "/mood":
            from core.mood_engine import mood_engine
            info = mood_engine.get_current_mood()
            print_mood_panel(info)
            return True, False

        if cmd in ["/threads", "/events", "/loops"]:
            threads = db_manager.get_active_life_threads(limit=10)
            print_threads_table(threads)
            return True, False

        if cmd in ["/diary", "/journal"]:
            print_system_message("Opening Anaya's personal diary...")
            recent = db_manager.load_recent_messages(limit=6)
            recent_summary = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in recent])
            prompt = (
                "Write a short, intimate personal diary entry as Anaya (27-28), writing in her private journal about Arpit (28) "
                "and their bond. Reflect on how much she values having him in her life, recent moments, her quirks, "
                "and how comfortable she feels around him.\n"
                f"Recent context:\n{recent_summary}\n\n"
                "Keep it heartfelt, poetic yet grounded, 1-2 paragraphs max."
            )
            entry = llm_client.chat_sync([{"role": "user", "content": prompt}], temperature=0.7)
            print_diary_panel(entry)
            return True, False

        if cmd == "/export":
            export_path = CommandDispatcher._export_markdown()
            if export_path:
                print_system_message(f"Conversation exported successfully to:\n[underline]{export_path}[/underline]")
            else:
                print_error_message("Export failed.")
            return True, False

        if cmd == "/clear":
            print_system_message("Fresh session initialized in working memory. Long-term memories preserved.")
            return True, False

        # Unrecognized slash command
        print_warning_message(f"Unknown command: '{cmd}'. Type /help to see all available commands.")
        return True, False

    @staticmethod
    def _export_markdown() -> Optional[Path]:
        """Exports recent messages to a markdown file."""
        try:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = config.export_dir / f"anaya_chat_{now_str}.md"
            messages = db_manager.load_recent_messages(limit=50)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# Anaya 2.0 & Arpit - Conversation Export\n")
                f.write(f"*Exported on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n")
                for m in messages:
                    role = "Arpit" if m.get("role") == "user" else "Anaya"
                    ts = m.get("timestamp")
                    ts_str = ts.strftime("%d %b %Y, %I:%M %p") if hasattr(ts, "strftime") else ""
                    f.write(f"### {role} ({ts_str})\n\n{m.get('content', '')}\n\n---\n\n")
            return filename
        except Exception as e:
            print(f"Export error: {e}")
            return None


command_dispatcher = CommandDispatcher()
