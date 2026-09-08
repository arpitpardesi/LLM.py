"""
Database Administration & Maintenance Tool for Anaya 2.0
Consolidates and modernizes deleteData, fetchData, and uploadData with safe CRUD, export, and search.
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Optional

# Auto-detect and switch to project .venv python if started with system python missing dependencies
CURRENT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = CURRENT_DIR.parent
VENV_PY = ROOT_DIR / ".venv" / "bin" / "python3"
if VENV_PY.exists() and sys.executable != str(VENV_PY):
    try:
        import pymongo, rich
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

# Ensure Anaya 2.0 directory is in sys.path
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import config
from core.database import db_manager
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


def show_db_stats():
    """Displays detailed database stats."""
    stats = db_manager.get_session_stats()
    table = Table(title="Anaya 2.0 Database Statistics", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Database Name", config.db.database_name)
    table.add_row("Primary Collection", config.db.conversation_collection)
    table.add_row("Memories Collection", config.db.memories_collection)
    table.add_row("Total Messages", str(stats.get("total_messages", 0)))
    table.add_row("User Messages (Arpit)", str(stats.get("user_messages", 0)))
    table.add_row("Companion Messages (Anaya)", str(stats.get("bot_messages", 0)))
    table.add_row("Long-Term Memories", str(stats.get("total_memories", 0)))
    table.add_row("Total Sessions", str(stats.get("total_sessions", 0)))
    table.add_row("Days Known", f"{stats.get('days_known', 0)} days")

    console.print(table)


def search_messages():
    """Searches messages by keyword."""
    query = Prompt.ask("\n[bold cyan]Enter keyword to search[/bold cyan]")
    if not query.strip():
        return
    results = db_manager.search_messages(query.strip(), limit=25)
    if not results:
        console.print(f"[yellow]No messages found containing '{query}'.[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}' ({len(results)} matches)", border_style="magenta")
    table.add_column("DialogID", width=10)
    table.add_column("Role", width=10)
    table.add_column("Content")
    table.add_column("Timestamp", width=20)

    for r in results:
        ts = r.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else ""
        table.add_row(str(r.get("dialogID", "-")), r.get("role", ""), r.get("content", ""), ts_str)

    console.print(table)


def export_data():
    """Exports conversation data to JSON or Markdown."""
    fmt = Prompt.ask("Choose format", choices=["json", "markdown"], default="json")
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    messages = list(db_manager.convo_col.find().sort("timestamp", 1))

    if fmt == "json":
        outfile = config.export_dir / f"anaya_backup_{now_str}.json"
        # Convert ObjectId and datetime to serializable
        clean_docs = []
        for m in messages:
            doc = dict(m)
            doc["_id"] = str(doc["_id"])
            if isinstance(doc.get("timestamp"), datetime.datetime):
                doc["timestamp"] = doc["timestamp"].isoformat()
            clean_docs.append(doc)

        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(clean_docs, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Exported {len(clean_docs)} messages to JSON:[/green] {outfile}")

    else:
        outfile = config.export_dir / f"anaya_backup_{now_str}.md"
        with open(outfile, "w", encoding="utf-8") as f:
            f.write("# Anaya 2.0 Full Conversation Backup\n\n")
            for m in messages:
                role = "Arpit" if m.get("role") == "user" else "Anaya"
                ts = m.get("timestamp")
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else ""
                f.write(f"### {role} - {ts_str} (Dialog #{m.get('dialogID', '-')})\n\n")
                f.write(f"{m.get('content', '')}\n\n---\n\n")
        console.print(f"[green]Exported {len(messages)} messages to Markdown:[/green] {outfile}")


def delete_records():
    """Safely deletes records by various filters."""
    console.print("\n[bold red]Deletion Menu:[/bold red]")
    console.print("1. Delete last N messages (e.g. 1, 2, 3...)")
    console.print("2. Delete last N conversation turns (user + assistant pairs)")
    console.print("3. Delete by Dialog ID (>= threshold)")
    console.print("4. Delete by Session ID")
    console.print("5. Delete by Date Range")
    console.print("6. Clear entire conversation collection (Requires typed confirmation)")
    console.print("7. Cancel")

    choice = Prompt.ask("Select deletion type", choices=["1", "2", "3", "4", "5", "6", "7"])

    if choice == "1":
        n_str = Prompt.ask("How many last messages to delete? (e.g. 1, 2, 5)", default="1")
        try:
            n = max(1, int(n_str))
            # Preview last n messages
            cursor = db_manager.convo_col.find(
                {"metadata.is_seed_personality": {"$ne": True}}
            ).sort("timestamp", -1).limit(n)
            docs = list(cursor)
            if not docs:
                console.print("[yellow]No messages found to delete.[/yellow]")
                return

            table = Table(title=f"Preview: Last {len(docs)} Message(s) to Delete", border_style="red")
            table.add_column("DialogID", width=10)
            table.add_column("Role", width=10)
            table.add_column("Content")
            for d in docs:
                table.add_row(str(d.get("dialogID", "-")), d.get("role", ""), d.get("content", "")[:70])
            console.print(table)

            if Confirm.ask(f"Permanently delete these {len(docs)} message(s)?"):
                count, _ = db_manager.delete_last_n_messages(n=n)
                console.print(f"[bold green]Deleted {count} message(s) successfully.[/bold green]")
        except ValueError:
            console.print("[red]Invalid number.[/red]")

    elif choice == "2":
        turns_str = Prompt.ask("How many last conversation turns to delete? (1 turn = user+bot)", default="1")
        try:
            turns = max(1, int(turns_str))
            target_count = turns * 2
            cursor = db_manager.convo_col.find(
                {"metadata.is_seed_personality": {"$ne": True}}
            ).sort("timestamp", -1).limit(target_count)
            docs = list(cursor)
            if not docs:
                console.print("[yellow]No conversation turns found to delete.[/yellow]")
                return

            table = Table(title=f"Preview: Last {turns} Turn(s) ({len(docs)} messages) to Delete", border_style="red")
            table.add_column("Role", width=10)
            table.add_column("Content")
            for d in docs:
                table.add_row(d.get("role", ""), d.get("content", "")[:70])
            console.print(table)

            if Confirm.ask(f"Permanently delete these {len(docs)} message(s)?"):
                count, _ = db_manager.delete_last_n_turns(n_turns=turns)
                console.print(f"[bold green]Deleted {count} message(s) successfully.[/bold green]")
        except ValueError:
            console.print("[red]Invalid number.[/red]")

    elif choice == "3":
        dialog_id = Prompt.ask("Enter Dialog ID threshold", default="1")
        try:
            val = int(dialog_id)
            if Confirm.ask(f"Delete all documents with dialogID >= {val}?"):
                count = db_manager.delete_messages({"dialogID": {"$gte": val}})
                console.print(f"[green]Deleted {count} documents.[/green]")
        except ValueError:
            console.print("[red]Invalid Dialog ID.[/red]")

    elif choice == "4":
        session_id = Prompt.ask("Enter Session ID")
        if Confirm.ask(f"Delete all documents matching session_id '{session_id}'?"):
            count = db_manager.delete_messages({"session_id": session_id})
            console.print(f"[green]Deleted {count} documents.[/green]")

    elif choice == "5":
        date_str = Prompt.ask("Enter start date (YYYY-MM-DD)")
        days_str = Prompt.ask("Number of days from start date", default="1")
        try:
            start_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            days = int(days_str)
            end_date = start_date + datetime.timedelta(days=days)
            if Confirm.ask(f"Delete messages between {start_date} and {end_date}?"):
                count = db_manager.delete_messages({
                    "timestamp": {"$gte": start_date, "$lt": end_date}
                })
                console.print(f"[green]Deleted {count} documents.[/green]")
        except Exception as e:
            console.print(f"[red]Error parsing dates: {e}[/red]")

    elif choice == "6":
        confirm_text = Prompt.ask("[bold red]Type 'RESET_ANAYA' to confirm wiping the conversation history[/bold red]")
        if confirm_text == "RESET_ANAYA":
            count = db_manager.delete_messages({})
            console.print(f"[bold red]Collection cleared. Deleted {count} documents.[/bold red]")
        else:
            console.print("[yellow]Deletion cancelled.[/yellow]")


def show_llm_memory_status():
    """Displays Ollama model memory footprint and optimization parameters."""
    from core.llm_client import llm_client
    loaded = llm_client.get_loaded_models()
    table = Table(title="LLM Engine & Memory Status", border_style="magenta")
    table.add_column("Parameter / Metric", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Active Model", config.llm.active_model)
    table.add_row("Temperature (Sampling)", str(config.llm.temperature))
    table.add_row("Top-P (Nucleus Sampling)", str(config.llm.top_p))
    table.add_row("Chat Context Cap (num_ctx)", f"{config.llm.num_ctx} tokens")
    table.add_row("Internal Context Cap (num_ctx_internal)", f"{config.llm.num_ctx_internal} tokens")
    table.add_row("Sliding History Turns", f"{config.llm.context_window_turns} messages")
    table.add_row("Max Memory Facts In Prompt", str(config.llm.max_facts_in_prompt))
    table.add_row("Memory Keep-Alive Timeout", config.llm.keep_alive)
    table.add_row("CPU Performance Cores", str(config.llm.num_threads))
    table.add_row("Real-Time SSE Streaming", "Enabled" if config.llm.stream_output else "Disabled")
    table.add_row("Post-Stream Fact Extraction", "Enabled" if config.enable_fact_extraction else "Disabled")
    table.add_row("Loaded in VRAM/RAM", "Yes (Active)" if loaded else "No (Idle / Released)")
    if loaded:
        for m in loaded:
            table.add_row(f"  • {m['model']}", f"~{m['vram_mb']} MB (ctx: {m['context_length']})")

    console.print(table)
    if loaded:
        if Confirm.ask("\nPurge model from memory right now?"):
            ok, msg = llm_client.unload_model()
            if ok:
                console.print("[bold green]Model successfully purged from VRAM![/bold green]")
            else:
                console.print(f"[red]{msg}[/red]")


def manage_memories():
    """Allows viewing, searching, deleting individual memories, or clearing all memories."""
    while True:
        mems = db_manager.get_all_memories()
        console.print(f"\n[bold magenta]── Memory Vault Manager ({len(mems)} memories) ──[/bold magenta]")
        console.print("1. List all memories")
        console.print("2. Search memories by keyword")
        console.print("3. Delete a specific memory by key")
        console.print("4. Wipe / Clear all memories")
        console.print("5. Back to Main Menu")

        choice = Prompt.ask("\nEnter choice (1-5)", choices=["1", "2", "3", "4", "5"])
        if choice == "1":
            if not mems:
                console.print("[dim]No memories stored yet.[/dim]")
            else:
                table = Table(title=f"All Stored Memories ({len(mems)})", border_style="cyan")
                table.add_column("Key / Topic", style="bold cyan")
                table.add_column("Category", style="magenta")
                table.add_column("Details / Value", style="white")
                for m in mems:
                    table.add_row(str(m.get("key", "")), str(m.get("category", "general")), str(m.get("value", "")))
                console.print(table)
        elif choice == "2":
            q = Prompt.ask("Enter keyword to search in memories").strip().lower()
            if q:
                matches = [m for m in mems if q in str(m.get("key", "")).lower() or q in str(m.get("value", "")).lower()]
                console.print(f"[bold green]Found {len(matches)} matching memories:[/bold green]")
                for m in matches:
                    console.print(f"• [cyan]{m.get('key')}[/cyan] ({m.get('category')}): {m.get('value')}")
        elif choice == "3":
            key_to_del = Prompt.ask("Enter exact key / topic of memory to delete").strip()
            if key_to_del:
                if Confirm.ask(f"Are you sure you want to delete memory '{key_to_del}'?"):
                    if db_manager.delete_memory(key_to_del):
                        console.print(f"[bold green]Memory '{key_to_del}' successfully deleted![/bold green]")
                    else:
                        console.print(f"[bold red]Could not find or delete memory '{key_to_del}'[/bold red]")
        elif choice == "4":
            if Confirm.ask(f"[bold red]WARNING: Permanently delete all {len(mems)} memories?[/bold red]"):
                count = db_manager.clear_all_memories()
                console.print(f"[bold green]Cleared {count} memories from database.[/bold green]")
        elif choice == "5":
            break


def main_menu():
    """Main CLI driver for DB admin tool."""
    while True:
        console.print("\n[bold cyan]══════════════════════════════════════[/bold cyan]")
        console.print("[bold #ff79c6] Anaya 2.0 Administration & Maintenance [/bold #ff79c6]")
        console.print("[bold cyan]══════════════════════════════════════[/bold cyan]")
        console.print("1. View Database Statistics")
        console.print("2. Search Messages")
        console.print("3. Export Conversations (JSON / Markdown)")
        console.print("4. Safe Delete Messages")
        console.print("5. Manage Long-Term Memories (View / Delete / Clear)")
        console.print("6. View LLM & Memory Optimization Status / Free RAM")
        console.print("7. Exit")

        choice = Prompt.ask("\nEnter choice (1-7)", choices=["1", "2", "3", "4", "5", "6", "7"])

        if choice == "1":
            show_db_stats()
        elif choice == "2":
            search_messages()
        elif choice == "3":
            export_data()
        elif choice == "4":
            delete_records()
        elif choice == "5":
            manage_memories()
        elif choice == "6":
            show_llm_memory_status()
        elif choice == "7":
            console.print("[green]Exiting Admin tool.[/green]")
            break


if __name__ == "__main__":
    main_menu()
