"""
Terminal UI Engine for Anaya 2.0
Provides modern, rich terminal presentation, streaming responses, panels, and badges.
"""

import sys
import datetime
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.markdown import Markdown

from config import config

# Custom theme for Anaya 2.0
custom_theme = Theme({
    "anaya": "bold italic #ff79c6",
    "arpit": "bold #8be9fd",
    "timestamp": "dim #6272a4",
    "system": "dim #50fa7b",
    "warning": "bold #ffb86c",
    "error": "bold #ff5555",
    "badge": "reverse #bd93f9",
})

console = Console(theme=custom_theme)


def print_banner(model_name: str, db_status: bool, session_id: str):
    """Renders the startup banner with real-time status badges."""
    now_str = datetime.datetime.now().strftime("%I:%M %p | %A, %d %b %Y")
    
    status_icon = "[#50fa7b]● Online[/#50fa7b]" if db_status else "[#ff5555]● Offline[/#ff5555]"
    
    from core.life_engine import life_engine
    from core.mood_engine import mood_engine
    life_info = life_engine.get_current_activity()
    mood_info = mood_engine.get_current_mood()

    banner_content = (
        f"[bold #ff79c6]✨ A N A Y A   2 . 0 ✨[/bold #ff79c6]\n"
        f"[italic #f8f8f2]Your Intelligent, Emotionally Intuitive AI Companion[/italic #f8f8f2]\n\n"
        f"🤖 [bold]Model:[/bold] [#bd93f9]{model_name}[/#bd93f9]   "
        f"💾 [bold]Database:[/bold] {status_icon}   "
        f"🕒 [bold]Time:[/bold] [#8be9fd]{now_str}[/#8be9fd]\n"
        f"🌸 [bold]Currently:[/bold] [italic #f8f8f2]{life_info['activity']}[/italic #f8f8f2]\n"
        f"🎭 [bold]Mood:[/bold] [#ff79c6]{mood_info['name']}[/#ff79c6]   "
        f"🎧 [bold]Music:[/bold] [dim]{life_info.get('music', 'Melodies')}[/dim]\n\n"
        f"💡 Type [bold cyan]/help[/bold cyan] for commands, [bold red]/bye[/bold red] to exit."
    )
    
    panel = Panel(
        banner_content,
        title="[bold #ff79c6]Personal AI Friend[/bold #ff79c6]",
        subtitle="[dim]Talking with Arpit Pardesi (28)[/dim]",
        border_style="#bd93f9",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def print_user_prompt() -> str:
    """Displays Arpit's prompt label and returns user input."""
    try:
        user_input = console.input("[bold #8be9fd]Arpit › [/bold #8be9fd]")
        return user_input.strip()
    except (KeyboardInterrupt, EOFError):
        return "/bye"


def start_anaya_stream():
    """Prints the Anaya prefix prior to streaming tokens."""
    console.print("[bold #ff79c6]Anaya › [/bold #ff79c6]", end="")


def stream_token(token: str):
    """Outputs a single streamed token to stdout immediately, formatting burst bubbles cleanly."""
    if "|||" in token:
        parts = token.split("|||")
        for i, p in enumerate(parts):
            if i > 0:
                console.print("\n[bold #ff79c6]Anaya › [/bold #ff79c6]", end="")
            sys.stdout.write(p)
            sys.stdout.flush()
    else:
        sys.stdout.write(token)
        sys.stdout.flush()


def end_anaya_stream():
    """Outputs clean line breaks after streaming finishes."""
    sys.stdout.write("\n\n")
    sys.stdout.flush()


def print_system_message(msg: str):
    """Prints an informational system badge."""
    console.print(f"[system]ℹ {msg}[/system]")


def print_warning_message(msg: str):
    """Prints a warning badge."""
    console.print(f"[warning]⚠ {msg}[/warning]")


def print_error_message(msg: str):
    """Prints an error badge."""
    console.print(f"[error]✖ {msg}[/error]")


def print_help_menu():
    """Displays available slash commands in a stylish table."""
    table = Table(
        title="[bold #bd93f9]Anaya 2.0 Command Center[/bold #bd93f9]",
        border_style="#6272a4",
        header_style="bold #50fa7b",
        show_lines=True
    )
    table.add_column("Command", style="bold #8be9fd", width=22)
    table.add_column("Description", style="#f8f8f2")

    table.add_row("/help", "Show this command help menu")
    table.add_row("/facts or /memory", "View everything Anaya remembers about you")
    table.add_row("/remember <fact>", "Teach Anaya a specific personal fact or preference")
    table.add_row("/forget <key>", "Remove a remembered fact from Anaya's memory")
    table.add_row("/model [name]", "Switch or view Ollama models (e.g. llama3.2, uncensored)")
    table.add_row("/history [n]", "View the last N messages of conversation")
    table.add_row("/search <term>", "Search through all past conversations with Anaya")
    table.add_row("/stats", "View friendship statistics, total chats, and timeline")
    table.add_row("/undo [n]", "Undo last N conversation turns (default: 1 turn = user+bot)")
    table.add_row("/delete [n]", "Delete last N messages (e.g. /delete 1, /delete 2, /delete turns 1)")
    table.add_row("/life", "See what Anaya is currently up to in her day & music")
    table.add_row("/mood", "View Anaya's active emotional state & vibe")
    table.add_row("/threads", "View upcoming events & check-in topics Anaya is tracking")
    table.add_row("/diary", "Read Anaya's personal journal note about you & your bond")
    table.add_row("/export", "Export conversation history to a clean Markdown file")
    table.add_row("/clear", "Start a fresh new conversation session")
    table.add_row("/bye or /exit", "Say goodbye and save the session")

    console.print(table)
    console.print()


def print_memories_table(memories: List[Dict[str, Any]]):
    """Renders all remembered facts in a clean table."""
    if not memories:
        console.print("[dim]Anaya hasn't stored any memories yet. Talk with her or use /remember to add one![/dim]\n")
        return

    table = Table(
        title=f"[bold #ff79c6]Anaya's Memory Bank ({len(memories)} facts)[/bold #ff79c6]",
        border_style="#bd93f9",
        header_style="bold #8be9fd",
        show_lines=True
    )
    table.add_column("#", width=4, justify="right", style="dim")
    table.add_column("Category", width=14, style="#50fa7b")
    table.add_column("Fact Key", style="bold #f8f8f2", width=22)
    table.add_column("Details", style="#f8f8f2")
    table.add_column("Updated", width=14, style="dim")

    for idx, m in enumerate(memories, 1):
        cat = m.get("category", "general").capitalize()
        key = m.get("key", "")
        val = m.get("value", "")
        updated = m.get("updated_at")
        date_str = updated.strftime("%d %b %Y") if hasattr(updated, "strftime") else "-"
        table.add_row(str(idx), cat, key, val, date_str)

    console.print(table)
    console.print()


def print_stats_panel(stats: Dict[str, Any]):
    """Renders conversation and relationship statistics."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold #8be9fd")
    grid.add_column(style="#f8f8f2")

    grid.add_row("💬 Total Messages:", f"[bold]{stats.get('total_messages', 0)}[/bold]")
    grid.add_row("👤 Arpit's Messages:", f"{stats.get('user_messages', 0)}")
    grid.add_row("🌸 Anaya's Responses:", f"{stats.get('bot_messages', 0)}")
    grid.add_row("🧠 Long-Term Memories:", f"[#50fa7b]{stats.get('total_memories', 0)} facts[/#50fa7b]")
    grid.add_row("🔄 Total Sessions:", f"{stats.get('total_sessions', 1)}")

    first_int = stats.get("first_interaction")
    last_int = stats.get("last_interaction")
    first_str = first_int.strftime("%d %B %Y") if hasattr(first_int, "strftime") else "Today"
    last_str = last_int.strftime("%d %B %Y, %I:%M %p") if hasattr(last_int, "strftime") else "Now"

    grid.add_row("📅 First Connected:", first_str)
    grid.add_row("🕒 Last Interaction:", last_str)
    grid.add_row("⏳ Friendship Timeline:", f"[bold #ff79c6]{stats.get('days_known', 1)} days[/bold #ff79c6]")

    panel = Panel(
        grid,
        title="[bold #bd93f9]Anaya & Arpit - Relationship Statistics[/bold #bd93f9]",
        border_style="#bd93f9",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()


def print_history_table(messages: List[Dict[str, Any]]):
    """Renders conversation history in a styled table."""
    if not messages:
        console.print("[dim]No conversation history found.[/dim]\n")
        return

    table = Table(
        title="[bold #8be9fd]Recent Conversation History[/bold #8be9fd]",
        border_style="#6272a4",
        header_style="bold #bd93f9",
        show_lines=True
    )
    table.add_column("Speaker", width=12)
    table.add_column("Message")
    table.add_column("Timestamp", width=18, style="dim")

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        ts = msg.get("timestamp")
        ts_str = ts.strftime("%d %b %I:%M %p") if hasattr(ts, "strftime") else ""

        if role == "user":
            table.add_row("[bold #8be9fd]Arpit[/bold #8be9fd]", content, ts_str)
        else:
            table.add_row("[bold #ff79c6]Anaya[/bold #ff79c6]", content, ts_str)

    console.print(table)
    console.print()


def print_life_panel(life_info: Dict[str, Any]):
    """Renders Anaya's personal daily life activities and thoughts."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold #ff79c6", width=20)
    grid.add_column(style="#f8f8f2")

    grid.add_row("🌸 Current Activity:", life_info.get("activity", "Relaxing"))
    grid.add_row("💭 On Her Mind:", f"[italic]\"{life_info.get('thoughts', '')}\"[/italic]")
    grid.add_row("🎧 In Her Headphones:", life_info.get("music", "Acoustic playlist"))
    grid.add_row("✨ Current Vibe:", f"[bold #50fa7b]{life_info.get('vibe', 'Warm')}[/bold #50fa7b]")

    panel = Panel(
        grid,
        title="[bold #ff79c6]Anaya's Personal Day & Activities[/bold #ff79c6]",
        subtitle="[dim]What Anaya is up to in her own life[/dim]",
        border_style="#ff79c6",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()


def print_mood_panel(mood_info: Dict[str, Any]):
    """Renders Anaya's persistent emotional mood state."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold #bd93f9", width=18)
    grid.add_column(style="#f8f8f2")

    grid.add_row("🎭 Emotional State:", f"[bold #ff79c6]{mood_info.get('name', 'Playful')}[/bold #ff79c6]")
    grid.add_row("📖 Inner Feeling:", mood_info.get("desc", ""))
    grid.add_row("💬 Conversational Tone:", f"[italic]{mood_info.get('hint', '')}[/italic]")

    panel = Panel(
        grid,
        title="[bold #bd93f9]Anaya's Emotional Heart & Mood[/bold #bd93f9]",
        subtitle="[dim]Current emotional momentum with Arpit[/dim]",
        border_style="#bd93f9",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()


def print_threads_table(threads: List[Dict[str, Any]]):
    """Renders open life threads and upcoming events Anaya is tracking."""
    if not threads:
        console.print("[dim]No active life threads right now. Share an upcoming event or plan and Anaya will remember to follow up![/dim]\n")
        return

    table = Table(
        title=f"[bold #50fa7b]Anaya's Life Check-In Tracker ({len(threads)} active)[/bold #50fa7b]",
        border_style="#50fa7b",
        header_style="bold #8be9fd",
        show_lines=True
    )
    table.add_column("#", width=4, justify="right", style="dim")
    table.add_column("Life Event / Topic", style="bold #f8f8f2", width=22)
    table.add_column("Details", style="#f8f8f2")
    table.add_column("Follow-Up Question", style="italic #ff79c6")
    table.add_column("Check-Ins", width=10, justify="center", style="dim")

    for idx, t in enumerate(threads, 1):
        topic = t.get("topic", "").capitalize()
        context = t.get("context", "")
        hint = t.get("follow_up_hint", "-")
        count = str(t.get("check_in_count", 0))
        table.add_row(str(idx), topic, context, hint, count)

    console.print(table)
    console.print()


def print_diary_panel(diary_text: str):
    """Renders Anaya's personal journal note."""
    panel = Panel(
        f"[italic #f8f8f2]{diary_text}[/italic #f8f8f2]",
        title="[bold #ff79c6]Anaya's Secret Diary Entry[/bold #ff79c6]",
        subtitle="[dim]Her real thoughts on Arpit & today[/dim]",
        border_style="#ff79c6",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()
