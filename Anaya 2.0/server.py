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

from fastapi import FastAPI, Request, HTTPException, Response
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
from core.affinity_engine import affinity_engine
from core.activities_engine import activities_engine
from core.semantic_memory import semantic_memory_engine

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


class PersonaUpdateRequest(BaseModel):
    companion_name: Optional[str] = "Anaya"
    user_name: Optional[str] = "Arpit"
    relationship: Optional[str] = "Closest Friend"
    language_blend: Optional[str] = "Contemporary Indian English & subtle Hinglish"
    tone_vibe: Optional[str] = "Warm, intuitive, and playful"
    personality_text: str


class AdminDeleteRequest(BaseModel):
    mode: str  # "messages", "turns", "dialog_threshold", "session", "date_range", "reset_chat"
    count: Optional[int] = 1
    threshold: Optional[int] = 2
    session_id: Optional[str] = ""
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""
    confirm_text: Optional[str] = ""


class TraitRequest(BaseModel):
    trait: str
    description: str
    category: Optional[str] = "core"
    order: Optional[int] = 0


class SuggestTraitsRequest(BaseModel):
    prompt: str


class RefineTraitRequest(BaseModel):
    trait: str
    description: str


class LLMConfigUpdateRequest(BaseModel):
    num_ctx: Optional[int] = None
    num_ctx_internal: Optional[int] = None
    keep_alive: Optional[str] = None
    num_threads: Optional[int] = None
    context_window_turns: Optional[int] = None
    max_facts_in_prompt: Optional[int] = None
    enable_fact_extraction: Optional[bool] = None
    active_model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream_output: Optional[bool] = None


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
    loaded_models = llm_client.get_loaded_models()

    return {
        "online": True,
        "database_connected": db_ok,
        "active_model": llm_client.active_model,
        "available_models": llm_client.list_models(),
        "loaded_models": loaded_models,
        "llm_memory": {
            "num_ctx": getattr(config.llm, "num_ctx", 2048),
            "keep_alive": getattr(config.llm, "keep_alive", "3m"),
            "active_vram_mb": sum(m.get("vram_mb", 0) for m in loaded_models) if loaded_models else 0,
            "is_loaded": len(loaded_models) > 0
        },
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
            "mood_momentum": mood_info.get("momentum", 0.8),
            "mood_intensity": mood_info.get("intensity", "moderate"),
            "mood_trajectory": mood_info.get("trajectory", []),
        },
        "affinity": affinity_engine.calculate_affinity(),
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

    # 2. Instant rule-based mood shift (0.05ms regex, no LLM call)
    try:
        mood_engine.evaluate_conversational_shift(user_text)
    except Exception:
        pass

    # 3. Assemble chat context with capped sliding window and episodic memory
    messages = memory_engine.build_chat_context(session_id=session_id, current_query=user_text)

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

            # 6. Post-stream processing: Run fact extraction and proactive checks
            # only AFTER streaming finishes to eliminate GPU contention and stuttering!
            asyncio.create_task(asyncio.to_thread(memory_engine.extract_and_save_facts, user_text))

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


@app.post("/api/llm/unload")
async def unload_llm_model():
    """Unloads active LLM from memory (VRAM/RAM) immediately."""
    ok, msg = llm_client.unload_model()
    return {
        "success": ok,
        "message": msg,
        "loaded_models": llm_client.get_loaded_models()
    }


@app.get("/api/llm/status")
async def get_llm_status():
    """Returns memory footprint, context length, and loaded models."""
    loaded = llm_client.get_loaded_models()
    return {
        "active_model": llm_client.active_model,
        "loaded_models": loaded,
        "num_ctx": getattr(config.llm, "num_ctx", 2048),
        "keep_alive": getattr(config.llm, "keep_alive", "3m"),
        "total_vram_mb": sum(m.get("vram_mb", 0) for m in loaded) if loaded else 0
    }


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


@app.delete("/api/memories")
@app.delete("/api/admin/memories")
async def clear_all_memories():
    """Clears all stored memories from MongoDB."""
    count = db_manager.clear_all_memories()
    return {"success": True, "deleted_count": count}


@app.delete("/api/memories/{key:path}")
@app.delete("/api/admin/memories/{key:path}")
async def delete_memory(key: str):
    """Deletes a memory fact."""
    from urllib.parse import unquote
    clean_k = unquote(key).strip()
    ok = db_manager.delete_memory(clean_k)
    if not ok:
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


@app.get("/api/affinity")
async def get_affinity():
    """Returns Anaya & Arpit's relationship affinity level, streak, and perks."""
    return affinity_engine.calculate_affinity()


@app.get("/api/proactive-check")
async def get_proactive_check():
    """Evaluates whether Anaya has a proactive greeting or thread follow-up."""
    return proactive_engine.get_proactive_checkin()


@app.post("/api/proactive-check/ack")
async def ack_proactive(payload: Dict[str, Any]):
    """Acknowledges a proactive check-in thread."""
    thread_id = payload.get("thread_id")
    if thread_id:
        proactive_engine.mark_thread_checked(thread_id)
    return {"success": True}


@app.get("/api/activities")
async def get_activities():
    """Lists available interactive companion mini-activities."""
    return {"activities": activities_engine.list_activities()}


class ActivityStartRequest(BaseModel):
    activity_id: str


@app.post("/api/activities/start")
async def start_activity(payload: ActivityStartRequest):
    """Starts an interactive mini-activity."""
    result = activities_engine.start_activity(
        activity_id=payload.activity_id,
        companion_name=config.user.companion_name,
        user_name=config.user.user_name
    )
    return result


@app.get("/api/diary")
async def get_diary(force: bool = False):
    """
    Returns today's secret personal diary entry.
    If not yet generated today, uses Ollama to synthesize reflections and archives it in MongoDB.
    """
    today_doc = db_manager.get_today_diary()
    if today_doc and not force:
        return {
            "diary_entry": today_doc.get("content", ""),
            "date": today_doc.get("display_date", ""),
            "title": today_doc.get("title", ""),
            "mood": today_doc.get("mood", ""),
            "is_cached": True
        }

    recent = db_manager.load_recent_messages(limit=8)
    recent_summary = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in recent])
    prompt = (
        f"Write a short, intimate personal diary entry as {config.user.companion_name} (27-28), "
        f"writing in her private journal about {config.user.user_name} (28) and their bond. "
        "Reflect on how much she values having him in her life, recent moments, her quirks, "
        "and how comfortable she feels around him.\n"
        f"Recent context:\n{recent_summary}\n\n"
        "Keep it heartfelt, poetic yet grounded, 1-2 paragraphs max."
    )
    entry = await asyncio.to_thread(llm_client.chat_sync, [{"role": "user", "content": prompt}], None, 0.7)
    
    activity = life_engine.get_current_activity().get("activity", "")
    mood_name = mood_engine.get_current_mood().get("name", "Warm")
    saved = db_manager.save_diary_entry(
        entry=entry,
        title=f"Reflections with {config.user.user_name}",
        mood=mood_name,
        activity=activity
    )
    return {
        "diary_entry": entry,
        "date": saved.get("display_date", ""),
        "title": saved.get("title", ""),
        "mood": mood_name,
        "is_cached": False
    }


@app.get("/api/diary/history")
async def get_diary_history():
    """Retrieves chronological diary history entries."""
    entries = db_manager.get_diary_entries(limit=15)
    return {"entries": entries}


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


# -------------------------------------------------------------
# Companion Persona & Setup Endpoints
# -------------------------------------------------------------

@app.get("/api/persona")
async def get_persona_config():
    """Returns the current companion profile and personality configuration."""
    seed_doc = db_manager.get_seed_personality()
    meta = seed_doc.get("metadata", {}) if seed_doc else {}

    companion_name = meta.get("companion_name", persona_engine.companion_name)
    user_name = meta.get("user_name", persona_engine.user_name)
    relationship = meta.get("relationship", persona_engine.relationship)
    language_blend = meta.get("language_blend", persona_engine.language_blend)
    tone_vibe = meta.get("tone_vibe", persona_engine.tone_vibe)
    personality_text = persona_engine.base_persona

    # First run is True if no seed doc exists or user has never customized
    is_first_run = (seed_doc is None)

    return {
        "companion_name": companion_name,
        "user_name": user_name,
        "relationship": relationship,
        "language_blend": language_blend,
        "tone_vibe": tone_vibe,
        "personality_text": personality_text,
        "is_first_run": is_first_run
    }


@app.post("/api/persona")
async def update_persona_config(payload: PersonaUpdateRequest):
    """Updates companion identity, relationship dynamic, and personality text."""
    ok = persona_engine.update_personality(
        new_content=payload.personality_text,
        companion_name=payload.companion_name,
        user_name=payload.user_name,
        relationship=payload.relationship,
        language_blend=payload.language_blend,
        tone_vibe=payload.tone_vibe
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update persona")

    return {
        "success": True,
        "companion_name": persona_engine.companion_name,
        "user_name": persona_engine.user_name,
        "relationship": persona_engine.relationship,
        "message": "Companion personality successfully saved and reloaded!"
    }


# -------------------------------------------------------------
# Personality Builder Endpoints (Modular Traits & AI Suggester)
# -------------------------------------------------------------

@app.get("/api/traits")
async def get_traits():
    """Returns all active modular personality traits."""
    traits = db_manager.get_all_traits()
    cleaned = []
    for t in traits:
        cleaned.append({
            "trait": t.get("trait", ""),
            "description": t.get("description", ""),
            "category": t.get("category", "core"),
            "order": t.get("order", 0)
        })
    return {"traits": cleaned}


@app.post("/api/traits")
async def save_trait(payload: TraitRequest):
    """Adds or updates a personality trait."""
    ok = db_manager.save_trait(
        trait=payload.trait,
        description=payload.description,
        category=payload.category or "core",
        order=payload.order or 0
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to save personality trait")
    return {"success": True, "trait": payload.trait}


@app.delete("/api/traits/{trait_name}")
async def delete_trait(trait_name: str):
    """Deletes a personality trait."""
    ok = db_manager.delete_trait(trait_name)
    return {"success": ok}


@app.post("/api/traits/reset")
async def reset_traits():
    """Resets traits to canonical defaults."""
    traits = db_manager.reset_default_traits()
    cleaned = []
    for t in traits:
        cleaned.append({
            "trait": t.get("trait", ""),
            "description": t.get("description", ""),
            "category": t.get("category", "core"),
            "order": t.get("order", 0)
        })
    return {"success": True, "traits": cleaned}


@app.post("/api/traits/suggest")
async def suggest_traits(payload: SuggestTraitsRequest):
    """
    Uses Ollama to suggest 3-4 personality traits based on user prompt / theme.
    Equivalent to askOllama personality maker in legacy personalityAI_v1.py.
    """
    user_theme = payload.prompt.strip()
    if not user_theme:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    prompt = (
        "You are an AI personality maker that helps users create and manage personality traits for AI companion bots.\n"
        f"The user wants traits based on this theme: \"{user_theme}\".\n"
        "Suggest exactly 3 to 4 distinct, vivid, authentic personality traits.\n"
        "Return ONLY a JSON list of objects without markdown formatting or code fences. Each object must have keys:\n"
        "\"trait\": Short name of the trait (e.g. 'Playful Banterer', 'Midnight Confidante')\n"
        "\"category\": One of ['emotional', 'humor', 'bond', 'intellect', 'cultural', 'quirks']\n"
        "\"description\": A rich, authentic 1-2 sentence description of how this trait manifests in real conversation.\n"
        "JSON format: [{\"trait\": \"...\", \"category\": \"...\", \"description\": \"...\"}]"
    )

    try:
        raw = await asyncio.to_thread(llm_client.chat_sync, [{"role": "user", "content": prompt}], None, 0.7)
        # Clean potential markdown fences
        clean = raw.strip()
        if "```" in clean:
            match = re.search(r"\[.*\]", clean, re.DOTALL)
            if match:
                clean = match.group(0)
            else:
                clean = clean.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(clean)
        if isinstance(parsed, list):
            return {"suggestions": parsed}
    except Exception as e:
        print(f"[Warning] Failed to parse suggestions JSON: {e}")

    # Fallback default suggestions if LLM returned non-JSON text
    return {
        "suggestions": [
            {
                "trait": f"{user_theme.title()} Energy",
                "category": "core",
                "description": f"Infuses conversations with a distinct {user_theme} presence and lively engagement."
            }
        ]
    }


@app.post("/api/traits/refine")
async def refine_trait(payload: RefineTraitRequest):
    """
    Uses Ollama to polish or expand a trait description.
    Directly reflects option 1 in legacy personalityAI_v1.py.
    """
    trait_name = payload.trait.strip()
    draft_desc = payload.description.strip()

    prompt = (
        "You are an AI personality maker.\n"
        f"Suggest a refined, vibrant, and realistic conversational description for the personality trait '{trait_name}'.\n"
        f"Current draft: '{draft_desc}'.\n\n"
        "Keep it concise (1 to 2 sentences max), authentic, grounded, and written in second-person or third-person. "
        "Return ONLY the refined description text without preamble."
    )

    refined = await asyncio.to_thread(llm_client.chat_sync, [{"role": "user", "content": prompt}], None, 0.7)
    clean_refined = refined.strip() if refined else draft_desc
    return {
        "refined": clean_refined,
        "refined_description": clean_refined
    }


@app.post("/api/traits/compile")
async def compile_traits():
    """
    Compiles all active personality traits into a cohesive master personality prompt,
    saves to personality.txt, updates MongoDB seed doc dialogID #1, and reloads persona engine.
    """
    compiled_prompt = db_manager.compile_traits_to_prompt(
        companion_name=persona_engine.companion_name,
        user_name=persona_engine.user_name,
        relationship=persona_engine.relationship
    )

    ok = persona_engine.update_personality(
        new_content=compiled_prompt,
        companion_name=persona_engine.companion_name,
        user_name=persona_engine.user_name,
        relationship=persona_engine.relationship
    )

    if not ok:
        raise HTTPException(status_code=500, detail="Failed to compile and save personality")

    return {
        "success": True,
        "compiled_prompt": compiled_prompt,
        "message": "Traits successfully compiled and applied to your companion!"
    }


# -------------------------------------------------------------
# Web Admin Console Endpoints
# -------------------------------------------------------------

@app.get("/api/admin/stats")
async def get_admin_stats():
    """Returns deep database and system diagnostics for Admin Console."""
    db_ok, db_msg = db_manager.health_check()
    db_stats = db_manager.get_session_stats()
    cache_stats = voice_engine.get_cache_stats()

    first_dt = db_stats.get("first_interaction")
    last_dt = db_stats.get("last_interaction")

    return {
        "database_connected": db_ok,
        "database_message": db_msg,
        "database_name": config.db.database_name,
        "total_messages": db_stats.get("total_messages", 0),
        "user_messages": db_stats.get("user_messages", 0),
        "bot_messages": db_stats.get("bot_messages", 0),
        "total_memories": db_stats.get("total_memories", 0),
        "total_sessions": db_stats.get("total_sessions", 0),
        "days_known": db_stats.get("days_known", 0),
        "first_interaction": first_dt.isoformat() if hasattr(first_dt, "isoformat") else str(first_dt or ""),
        "last_interaction": last_dt.isoformat() if hasattr(last_dt, "isoformat") else str(last_dt or ""),
        "audio_cache": cache_stats,
        "active_model": llm_client.active_model
    }


@app.get("/api/admin/messages")
async def get_admin_messages(
    query: str = "",
    role: str = "all",
    limit: int = 50,
    skip: int = 0
):
    """Returns paginated/searchable message explorer data for Admin Console."""
    safe_limit = min(200, max(1, limit))
    safe_skip = max(0, skip)
    total, docs = db_manager.get_messages_advanced(query=query, role=role, limit=safe_limit, skip=safe_skip)

    cleaned = []
    for d in docs:
        ts = d.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts or "")
        cleaned.append({
            "id": str(d.get("_id", "")),
            "dialogID": d.get("dialogID", "-"),
            "role": d.get("role", "unknown"),
            "content": d.get("content", ""),
            "session_id": d.get("session_id", ""),
            "timestamp": ts_str
        })

    return {
        "total": total,
        "limit": safe_limit,
        "skip": safe_skip,
        "messages": cleaned
    }


@app.post("/api/admin/delete")
async def admin_delete(payload: AdminDeleteRequest):
    """Executes safe selective deletion with seed personality protection."""
    if payload.mode == "reset_chat" and payload.confirm_text != "RESET_ANAYA":
        raise HTTPException(
            status_code=400,
            detail="Reset confirmation failed. You must provide confirm_text='RESET_ANAYA'."
        )

    params = {
        "count": payload.count,
        "threshold": payload.threshold,
        "session_id": payload.session_id,
        "start_date": payload.start_date,
        "end_date": payload.end_date
    }
    count, msg = db_manager.delete_messages_advanced(mode=payload.mode, params=params)
    return {"success": True, "deleted_count": count, "message": msg}


@app.get("/api/admin/export")
async def admin_export(format: str = "json"):
    """Downloads conversation export as JSON or Markdown."""
    fmt = format.lower()
    if fmt not in ["json", "markdown", "md"]:
        fmt = "json"

    filename, content, mime_type = db_manager.get_export_data(fmt=fmt)
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/admin/clear-cache")
async def admin_clear_audio_cache():
    """Purges synthesized audio cache files."""
    deleted_count = voice_engine.clear_cache()
    return {"success": True, "deleted_files": deleted_count}


@app.post("/api/admin/clean-memories")
async def admin_clean_memories():
    """Removes noisy or fragmented memories."""
    cleaned_count = db_manager.cleanup_noisy_memories()
    return {"success": True, "cleaned_count": cleaned_count}


@app.get("/api/admin/llm-config")
async def get_admin_llm_config():
    """Returns detailed LLM memory and inference configuration."""
    loaded = llm_client.get_loaded_models()
    return {
        "active_model": llm_client.active_model,
        "available_models": llm_client.list_models(),
        "loaded_models": loaded,
        "total_vram_mb": sum(m.get("vram_mb", 0) for m in loaded) if loaded else 0,
        "is_loaded": len(loaded) > 0,
        "temperature": getattr(config.llm, "temperature", 0.75),
        "top_p": getattr(config.llm, "top_p", 0.9),
        "stream_output": getattr(config.llm, "stream_output", True),
        "num_ctx": getattr(config.llm, "num_ctx", 2048),
        "num_ctx_internal": getattr(config.llm, "num_ctx_internal", 768),
        "keep_alive": getattr(config.llm, "keep_alive", "3m"),
        "num_threads": getattr(config.llm, "num_threads", 6),
        "context_window_turns": getattr(config.llm, "context_window_turns", 14),
        "max_facts_in_prompt": getattr(config.llm, "max_facts_in_prompt", 6),
        "enable_fact_extraction": getattr(config, "enable_fact_extraction", True),
    }


@app.post("/api/admin/llm-config")
async def update_admin_llm_config(payload: LLMConfigUpdateRequest):
    """Updates LLM inference parameters and memory constraints at runtime."""
    if payload.active_model and payload.active_model != llm_client.active_model:
        ok, msg = llm_client.switch_model(payload.active_model)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)

    if payload.temperature is not None:
        config.llm.temperature = max(0.0, min(2.0, float(payload.temperature)))
    if payload.top_p is not None:
        config.llm.top_p = max(0.05, min(1.0, float(payload.top_p)))
    if payload.stream_output is not None:
        config.llm.stream_output = bool(payload.stream_output)
    if payload.num_ctx is not None:
        config.llm.num_ctx = max(512, min(32768, payload.num_ctx))
    if payload.num_ctx_internal is not None:
        config.llm.num_ctx_internal = max(256, min(8192, payload.num_ctx_internal))
    if payload.keep_alive is not None:
        config.llm.keep_alive = payload.keep_alive.strip()
    if payload.num_threads is not None:
        config.llm.num_threads = max(1, min(32, payload.num_threads))
    if payload.context_window_turns is not None:
        config.llm.context_window_turns = max(2, min(50, payload.context_window_turns))
    if payload.max_facts_in_prompt is not None:
        config.llm.max_facts_in_prompt = max(0, min(20, payload.max_facts_in_prompt))
    if payload.enable_fact_extraction is not None:
        config.enable_fact_extraction = payload.enable_fact_extraction

    return {
        "success": True,
        "message": "All LLM parameters and optimizations updated successfully!",
        "config": {
            "active_model": llm_client.active_model,
            "temperature": config.llm.temperature,
            "top_p": config.llm.top_p,
            "stream_output": config.llm.stream_output,
            "num_ctx": config.llm.num_ctx,
            "num_ctx_internal": config.llm.num_ctx_internal,
            "keep_alive": config.llm.keep_alive,
            "num_threads": config.llm.num_threads,
            "context_window_turns": config.llm.context_window_turns,
            "max_facts_in_prompt": config.llm.max_facts_in_prompt,
            "enable_fact_extraction": config.enable_fact_extraction,
        }
    }


def start_server(port: int = 8000, host: str = "0.0.0.0"):
    """Starts the Uvicorn web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
