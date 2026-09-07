# Anaya 2.0 - Next-Gen Human-Like AI Companion

Anaya is an emotionally intuitive, warm, and authentic AI friend designed to talk and connect like a real human being.

---

## 🚀 Key Features in Anaya 2.0

1. **Dual-Tier Memory Engine**:
   - **Sliding Context Window**: Prevents context token overflow by keeping the most recent dialogue turns active and coherent.
   - **Long-Term Memory Bank**: Anaya automatically extracts and recalls personal facts, preferences, life updates, and emotional milestones about Arpit across sessions via MongoDB (`anaya_memories`).

2. **Temporal & Situational Awareness**:
   - Aware of the real-world local time (morning, afternoon, late night).
   - Dynamically calculates the time elapsed since you last chatted—reacting naturally if you were just talking or if you’ve been absent for days.

3. **Production Terminal UI (Rich)**:
   - Polished terminal interface with live token streaming, custom prompt badges, and color themes.
   - Built-in slash commands for total control.

4. **In-Chat Slash Commands**:
   - `/help` - View all available commands
   - `/facts` or `/memory` - Display everything Anaya remembers about you
   - `/remember <fact>` - Manually teach Anaya a preference or memory
   - `/forget <key>` - Remove a specific memory
   - `/model [name]` - Switch or inspect Ollama models (e.g., `llama3.2`, `artifish/llama3.2-uncensored`)
   - `/history [n]` - View recent messages
   - `/search <keyword>` - Search through your entire conversation history
   - `/stats` - View friendship timeline and conversation statistics
   - `/undo [n]` - Undo last N conversation turns (default: 1 turn = user + bot)
   - `/delete [n]` - Delete last N messages (e.g. `/delete 1`, `/delete 2`, `/delete turns 1`)
   - `/export` - Export conversation to Markdown
   - `/clear` - Start a fresh session cleanly
   - `/bye` or `/exit` - Gracefully close and save the session

5. **Integrated Database Administration**:
   - Run `python3 tools/db_admin.py` for full database management: search, backup, JSON/Markdown export, and safe filtered deletion.

6. **Interactive Personality Builder**:
   - Run `python3 tools/personality_admin.py` to inspect traits, brainstorm new dynamics with Ollama, and update `personality.txt` live.

---

## 📁 Directory Structure

```
Anaya 2.0/
├── anaya.py                 # Main application entry point
├── config.py                # Centralized configuration & environment loader
├── personality.txt          # Master personality description
├── requirements.txt         # Dependencies
├── core/
│   ├── database.py          # Indexed, connection-pooled MongoDB manager
│   ├── llm_client.py        # Ollama streaming client with fallback & health check
│   ├── memory_engine.py     # Dual-tier memory & fact extraction
│   └── persona.py           # Dynamic context & temporal prompt builder
├── cli/
│   ├── ui.py                # Rich terminal UI & streaming renderer
│   └── commands.py          # Slash command processor
├── tools/
│   ├── db_admin.py          # Unified database administration & backup tool
│   └── personality_admin.py # Interactive personality trait builder
├── tests/
│   ├── test_database.py     # Database tests
│   └── test_memory.py       # Memory & persona tests
├── exports/                 # Chat backups and exported logs
├── logs/                    # Runtime logs
└── legacy_v1/               # Preserved legacy v1 scripts
```

---

## 🛠️ Getting Started

### 1. Activate Virtual Environment
```bash
source ../.venv/bin/activate
```

### 2. Launch Full-Fledged Web UI (Recommended)
```bash
python3 anaya.py --ui
# Or start server directly:
python3 server.py
```
Open your browser at [http://localhost:8000](http://localhost:8000)

### 3. Run Anaya in Terminal CLI
```bash
python3 anaya.py
```

### 4. Run Database Admin Utility
```bash
python3 tools/db_admin.py
```

### 5. Run Personality Builder
```bash
python3 tools/personality_admin.py
```

### 6. Run Verification Tests
```bash
python3 tests/test_database.py
python3 tests/test_living_engines.py
```
