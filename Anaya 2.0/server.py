#!/usr/bin/env python3
"""
FastAPI Web Server for Anaya 2.0
Provides real-time SSE token streaming, REST endpoints, and serves the Web UI.
"""

import os
import sys
import json
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure virtual environment python
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
VENV_PY = ROOT_DIR / ".venv" / "bin" / "python3"
if VENV_PY.exists() and sys.executable != str(VENV_PY):
    try:
        import fastapi, uvicorn
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config
from core.database import db_manager
from core.llm_client import llm_client
from core.persona import persona_engine
from core.memory_engine import memory_engine
from core.life_engine import life_engine
from core.mood_engine import mood_engine
from core.proactive_engine import proactive_engine
from core.voice_engine import voice_engine

app = FastAPI(title="Anaya 2.0 Web Companion", version="2.0.0")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
WEB_DIR = CURRENT_DIR / "web"
STATIC_DIR = WEB_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class MemoryRequest(BaseModel):
    key: str
    value: str
    category: Optional[str] = "general"


class MoodRequest(BaseModel):
    mood_key: str


class ModelRequest(BaseModel):
    model: str


class ResolveThreadRequest(BaseModel):
    topic: str


class DeleteRequest(BaseModel):
    mode: str = "turn"  # "turn" or "message"
    count: int = 1


class ClearRequest(BaseModel):
    session_id: Optional[str] = None
    all_sessions: bool = True


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main single page web application."""
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/status")
async def get_status():
    """Returns Anaya's live activity, mood, music, and health."""
    db_ok, _ = db_manager.health_check()
    life_info = life_engine.get_current_activity()
    mood_info = mood_engine.get_current_mood()
    stats = db_manager.get_session_stats()
    open_threads = db_manager.get_active_life_threads()

    return {
        "online": True,
        "database_connected": db_ok,
        "active_model": llm_client.active_model,
        "available_models": llm_client.list_models(),
        "companion": {
            "name": config.user.companion_name,
            "age": config.user.companion_age,
            "relationship": config.user.relationship,
        },
        "user": {
            "name": config.user.user_name,
            "age": config.user.user_age,
        },
        "living_state": {
            "period": life_engine.get_current_period(),
            "activity": life_info.get("activity", ""),
            "thoughts": life_info.get("thoughts", ""),
            "music": life_info.get("music", ""),
            "vibe": life_info.get("vibe", ""),
            "mood_name": mood_info.get("name", ""),
            "mood_desc": mood_info.get("desc", ""),
            "mood_key": mood_info.get("key", ""),
        },
        "stats": stats,
        "open_threads_count": len(open_threads),
    }


@app.get("/api/history")
async def get_history(limit: int = 30):
    """Returns recent message history excluding seed personality."""
    messages = db_manager.load_recent_messages(limit=limit)
    cleaned = []
    for m in messages:
        ts = m.get("timestamp")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        cleaned.append({
            "id": str(m.get("_id", "")),
            "role": m.get("role", ""),
            "content": m.get("content", ""),
            "timestamp": ts_str,
            "dialogID": m.get("dialogID", 0)
        })
    return {"messages": cleaned}


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """
    Streams LLM tokens in real-time via Server-Sent Events (SSE).
    """
    user_text = payload.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = payload.session_id or str(uuid.uuid4())

    # 1. Save user message to database
    dialog_id = db_manager.get_next_dialog_id()
    db_manager.save_message(
        role="user",
        content=user_text,
        session_id=session_id,
        dialog_id=dialog_id
    )

    # 2. Extract facts in background task
    asyncio.create_task(asyncio.to_thread(memory_engine.extract_and_save_facts, user_text))

    # 3. Assemble chat context
    messages = memory_engine.build_chat_context(session_id=session_id)

    # 4. Generator function for SSE stream
    async def sse_generator():
        full_response = ""
        try:
            for token in llm_client.stream_chat(messages=messages):
                full_response += token
                event_payload = json.dumps({"token": token})
                yield f"data: {event_payload}\n\n"
                await asyncio.sleep(0.005)  # Tiny yield pause for smooth client rendering

            # 5. Save assistant response
            if full_response.strip():
                bot_dialog_id = db_manager.get_next_dialog_id()
                db_manager.save_message(
                    role="assistant",
                    content=full_response.strip(),
                    session_id=session_id,
                    dialog_id=bot_dialog_id
                )

            done_payload = json.dumps({
                "done": True,
                "full_response": full_response.strip(),
                "mood": mood_engine.get_current_mood()
            })
            yield f"data: {done_payload}\n\n"
        except Exception as e:
            err_payload = json.dumps({"error": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/memories")
async def get_memories():
    """Returns stored user and relationship memories."""
    mems = db_manager.get_all_memories()
    cleaned = []
    for m in mems:
        up = m.get("updated_at")
        cleaned.append({
            "key": m.get("key", ""),
            "value": m.get("value", ""),
            "category": m.get("category", "general"),
            "updated_at": up.isoformat() if hasattr(up, "isoformat") else ""
        })
    return {"memories": cleaned}


@app.post("/api/memories")
async def add_memory(payload: MemoryRequest):
    """Adds a new fact to Anaya's memory."""
    ok = db_manager.save_memory_fact(
        key=payload.key,
        value=payload.value,
        category=payload.category or "general"
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save memory")
    return {"success": True, "key": payload.key}


@app.delete("/api/memories/{key}")
async def delete_memory(key: str):
    """Deletes a memory fact."""
    ok = db_manager.delete_memory(key)
    return {"success": ok}


@app.get("/api/threads")
async def get_threads():
    """Returns active and pending life check-in threads."""
    threads = db_manager.get_active_life_threads(limit=15)
    cleaned = []
    for t in threads:
        cleaned.append({
            "topic": t.get("topic", "").capitalize(),
            "context": t.get("context", ""),
            "follow_up_hint": t.get("follow_up_hint", ""),
            "check_in_count": t.get("check_in_count", 0),
            "status": t.get("status", "open")
        })
    return {"threads": cleaned}


@app.post("/api/threads/resolve")
async def resolve_thread(payload: ResolveThreadRequest):
    """Marks a life thread as completed/resolved."""
    ok = db_manager.resolve_life_thread(payload.topic)
    return {"success": ok}


@app.get("/api/diary")
async def get_diary():
    """Generates Anaya's secret personal diary entry."""
    recent = db_manager.load_recent_messages(limit=6)
    recent_summary = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in recent])
    prompt = (
        "Write a short, intimate personal diary entry as Anaya (27-28), writing in her private journal about Arpit (28) "
        "and their bond. Reflect on how much she values having him in her life, recent moments, her quirks, "
        "and how comfortable she feels around him.\n"
        f"Recent context:\n{recent_summary}\n\n"
        "Keep it heartfelt, poetic yet grounded, 1-2 paragraphs max."
    )
    entry = await asyncio.to_thread(llm_client.chat_sync, [{"role": "user", "content": prompt}], 0.7)
    return {
        "diary_entry": entry,
        "date": life_engine.get_current_activity().get("activity", "")
    }


@app.post("/api/mood")
async def set_mood(payload: MoodRequest):
    """Manually changes Anaya's emotional mood."""
    mood_engine.update_mood(payload.mood_key)
    return {"success": True, "mood": mood_engine.get_current_mood()}


@app.post("/api/model")
async def set_model(payload: ModelRequest):
    """Switches active Ollama model."""
    ok, msg = llm_client.switch_model(payload.model)
    return {"success": ok, "message": msg, "active_model": llm_client.active_model}


@app.post("/api/delete-last")
async def delete_last(payload: DeleteRequest):
    """Deletes last conversation turn or message."""
    if payload.mode == "turn":
        count, docs = db_manager.delete_last_n_turns(n_turns=payload.count)
    else:
        count, docs = db_manager.delete_last_n_messages(n=payload.count)
    return {"success": True, "deleted_count": count}


@app.post("/api/clear")
async def clear_chat(payload: Optional[ClearRequest] = None):
    """
    Clears non-seed conversation messages from MongoDB while keeping
    seed personality and memories safe.
    """
    all_sessions = payload.all_sessions if payload else True
    sess_id = None if all_sessions else (payload.session_id if payload else None)
    count = db_manager.clear_conversation(session_id=sess_id)
    return {"success": True, "deleted_count": count}


@app.get("/api/voices")
async def get_voices():
    """Returns available Indian neural voices."""
    return {"voices": voice_engine.get_voices(), "default": voice_engine.default_voice}


@app.post("/api/tts")
async def synthesize_speech(payload: TTSRequest):
    """
    Synthesizes speech using edge-tts neural voice.
    Returns audio URL (cached if already synthesized).
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    res = await voice_engine.synthesize(text=text, voice=payload.voice)
    if not res:
        raise HTTPException(status_code=500, detail="Voice synthesis failed")

    return res


def start_server(port: int = 8000, host: str = "0.0.0.0"):
    """Starts the Uvicorn web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
