"""
Personality Builder & Manager for Anaya 2.0
Allows interactive viewing, adding, updating, and Ollama AI suggestion of traits.
Syncs changes directly with personality.txt and reloads persona in real time.
"""

import os
import sys
from pathlib import Path
from typing import Dict

# Auto-detect and switch to project .venv python if started with system python missing dependencies
CURRENT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = CURRENT_DIR.parent
VENV_PY = ROOT_DIR / ".venv" / "bin" / "python3"
if VENV_PY.exists() and sys.executable != str(VENV_PY):
    try:
        import pymongo, rich
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

# Ensure Anaya 2.0 is in sys.path
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import config
from core.llm_client import llm_client
from core.persona import persona_engine
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


def view_personality():
    """Prints the current personality file contents."""
    if not config.personality_file.exists():
        console.print("[red]personality.txt not found.[/red]")
        return
    with open(config.personality_file, "r", encoding="utf-8") as f:
        content = f.read()
    console.print("\n[bold magenta]Current Personality Definition:[/bold magenta]")
    console.print(content)


def suggest_traits_with_ai():
    """Uses Ollama to suggest dynamic, human-like traits for Anaya."""
    topic = Prompt.ask(
        "\n[bold cyan]What kind of trait or vibe would you like Anaya to have?[/bold cyan]\n"
        "(e.g., 'witty and sarcastic banter', 'philosophical midnight talks', 'shared music tastes')"
    )
    if not topic.strip():
        return

    prompt = (
        "You are an AI character designer refining 'Anaya', a 26-year-old Indian girl who is the user's (Arpit, 27) "
        "closest friend. She is warm, emotionally authentic, deeply loyal, playful, and human.\n"
        f"Suggest a new nuanced trait or dynamic regarding: \"{topic}\".\n"
        "Provide: 1) Trait Title with emoji, 2) 3-4 bullet points describing how she expresses it naturally in conversation.\n"
        "Keep it authentic, relatable, and grounded in Indian friendship dynamics."
    )

    console.print("\n[italic yellow]Brainstorming with Ollama...[/italic yellow]\n")
    suggestion = llm_client.chat_sync(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )
    console.print(suggestion)

    if Confirm.ask("\nWould you like to append this trait to personality.txt?"):
        append_to_personality(suggestion)


def append_to_personality(text: str):
    """Appends text to personality.txt and refreshes the persona engine."""
    try:
        with open(config.personality_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n⸻\n\n{text.strip()}\n")
        console.print("[green]Successfully updated personality.txt! ✨[/green]")
        persona_engine.reload_personality()
    except Exception as e:
        console.print(f"[red]Failed to update personality.txt: {e}[/red]")


def main_menu():
    """CLI Menu for Personality Builder."""
    while True:
        console.print("\n[bold magenta]══════════════════════════════════════[/bold magenta]")
        console.print("[bold #ff79c6] Anaya 2.0 Personality Builder [/bold #ff79c6]")
        console.print("[bold magenta]══════════════════════════════════════[/bold magenta]")
        console.print("1. View Current Personality Definition")
        console.print("2. Brainstorm & Add New Traits with AI")
        console.print("3. Append Custom Trait Manually")
        console.print("4. Reload & Verify Persona Engine")
        console.print("5. Exit")

        choice = Prompt.ask("\nEnter choice (1-5)", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            view_personality()
        elif choice == "2":
            suggest_traits_with_ai()
        elif choice == "3":
            custom_trait = Prompt.ask("Enter trait description to append")
            if custom_trait.strip():
                append_to_personality(custom_trait.strip())
        elif choice == "4":
            persona_engine.reload_personality()
            console.print("[green]Persona engine reloaded successfully.[/green]")
        elif choice == "5":
            break


if __name__ == "__main__":
    main_menu()
