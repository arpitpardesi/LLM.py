"""
LLM Client for Anaya 2.0
Handles Ollama interactions with streaming, model verification, health checks, and fallback.
"""

import time
from typing import List, Dict, Generator, Optional, Tuple, Any
import ollama

from config import config


class LLMClient:
    """Wraps Ollama chat APIs with streaming, performance tracking, and resiliency."""

    def __init__(self):
        self.config = config.llm
        self.active_model = self.config.active_model

    def list_models(self) -> List[str]:
        """Lists available local models in Ollama."""
        try:
            models_dict = ollama.list()
            # ollama.list() returns dict with 'models' key containing model objects or dicts
            names = []
            if isinstance(models_dict, dict) and "models" in models_dict:
                for m in models_dict["models"]:
                    name = m.get("model") or m.get("name")
                    if name:
                        names.append(name)
            elif hasattr(models_dict, "models"):
                for m in models_dict.models:
                    name = getattr(m, "model", None) or getattr(m, "name", None)
                    if name:
                        names.append(name)
            return names
        except Exception as e:
            print(f"[Warning] Failed to list Ollama models: {e}")
            return []

    def verify_model(self, model_name: Optional[str] = None) -> Tuple[bool, str]:
        """Verifies if the specified model is installed and accessible."""
        target = model_name or self.active_model
        available = self.list_models()
        
        # Check direct or prefix match (e.g. 'llama3.2' matches 'llama3.2:latest')
        for m in available:
            if m == target or m.startswith(target.split(":")[0]):
                return True, f"Model '{target}' is available."

        if not available:
            return False, "Ollama service may not be running or no models installed."
        
        return False, f"Model '{target}' not found. Available models: {', '.join(available)}"

    def switch_model(self, new_model: str) -> Tuple[bool, str]:
        """Switches the active model and frees memory from the old model."""
        ok, msg = self.verify_model(new_model)
        if ok:
            old_model = self.active_model
            if old_model and old_model != new_model:
                try:
                    ollama.chat(model=old_model, messages=[], keep_alive=0)
                except Exception:
                    pass
            self.active_model = new_model
            self.config.active_model = new_model
            return True, f"Active model switched to '{new_model}'."
        return False, msg

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        num_ctx: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        Streams chat completion tokens from Ollama.
        Yields chunk string fragments with strict context window limits.
        """
        target_model = model or self.active_model
        temp = temperature if temperature is not None else self.config.temperature
        ctx = num_ctx if num_ctx is not None else getattr(self.config, "num_ctx", 2048)

        options = {
            "temperature": temp,
            "top_p": getattr(self.config, "top_p", 0.9),
            "num_ctx": ctx,
            "repeat_penalty": getattr(self.config, "repeat_penalty", 1.18),
            "presence_penalty": getattr(self.config, "presence_penalty", 0.15),
            "stop": ["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>"]
        }
        if hasattr(self.config, "num_threads") and self.config.num_threads:
            options["num_thread"] = self.config.num_threads

        try:
            stream = ollama.chat(
                model=target_model,
                messages=messages,
                stream=True,
                keep_alive=getattr(self.config, "keep_alive", "3m"),
                options=options
            )
            
            # Sanitization buffer to intercept any leading 'assistant\n\n' or 'Anaya:' tokens
            prefix_buffer = ""
            is_initial = True
            STRIP_PREFIXES = ("assistant\n\n", "assistant:\n", "assistant:", "assistant\n", "anaya:\n", "anaya:", "anaya\n", "bot:\n", "bot:")

            for chunk in stream:
                content = ""
                if isinstance(chunk, dict) and "message" in chunk:
                    content = chunk["message"].get("content", "")
                elif hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    content = chunk.message.content or ""
                if not content:
                    continue

                if is_initial:
                    prefix_buffer += content
                    # Buffer until we have a newline or at least 18 characters
                    if "\n" in prefix_buffer or len(prefix_buffer) >= 18:
                        low = prefix_buffer.lower().lstrip()
                        for p in STRIP_PREFIXES:
                            if low.startswith(p):
                                # Strip prefix from buffer
                                prefix_buffer = prefix_buffer.lstrip()[len(p):].lstrip()
                                break
                        if prefix_buffer:
                            yield prefix_buffer
                        prefix_buffer = ""
                        is_initial = False
                else:
                    yield content

            # Flush remaining buffer if response was very short
            if is_initial and prefix_buffer:
                low = prefix_buffer.lower().lstrip()
                for p in STRIP_PREFIXES:
                    if low.startswith(p):
                        prefix_buffer = prefix_buffer.lstrip()[len(p):].lstrip()
                        break
                if prefix_buffer:
                    yield prefix_buffer
        except Exception as e:
            yield f"\n[Anaya response error: {e}]"

    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        num_ctx: Optional[int] = None,
    ) -> str:
        """
        Non-streaming chat completion for internal reasoning and fact extraction.
        Uses a lightweight context window to minimize memory allocation.
        """
        target_model = model or self.active_model
        ctx = num_ctx if num_ctx is not None else getattr(self.config, "num_ctx_internal", 768)

        options = {
            "temperature": temperature,
            "num_ctx": ctx,
        }
        if hasattr(self.config, "num_threads") and self.config.num_threads:
            options["num_thread"] = self.config.num_threads

        try:
            response = ollama.chat(
                model=target_model,
                messages=messages,
                stream=False,
                keep_alive=getattr(self.config, "keep_alive", "3m"),
                options=options
            )
            if isinstance(response, dict) and "message" in response:
                return response["message"].get("content", "").strip()
            elif hasattr(response, "message") and hasattr(response.message, "content"):
                return (response.message.content or "").strip()
            return ""
        except Exception as e:
            print(f"[Error in chat_sync]: {e}")
            return ""

    def unload_model(self, model_name: Optional[str] = None) -> Tuple[bool, str]:
        """Explicitly unloads the model from memory (RAM/VRAM) immediately."""
        target = model_name or self.active_model
        try:
            ollama.chat(model=target, messages=[], keep_alive=0)
            return True, f"Model '{target}' successfully unloaded from memory."
        except Exception as e:
            return False, f"Failed to unload model: {e}"

    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Returns currently loaded models and their memory/VRAM footprint in Ollama."""
        try:
            res = ollama.ps()
            loaded = []
            models_list = res.get("models", []) if isinstance(res, dict) else getattr(res, "models", [])
            for m in models_list:
                name = m.get("model") if isinstance(m, dict) else getattr(m, "model", "")
                size = m.get("size") if isinstance(m, dict) else getattr(m, "size", 0)
                size_vram = m.get("size_vram") if isinstance(m, dict) else getattr(m, "size_vram", 0)
                ctx_len = m.get("context_length") if isinstance(m, dict) else getattr(m, "context_length", 0)
                loaded.append({
                    "model": name,
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 1) if size else 0,
                    "vram_mb": round(size_vram / (1024 * 1024), 1) if size_vram else 0,
                    "context_length": ctx_len,
                })
            return loaded
        except Exception as e:
            return []


# Singleton instance
llm_client = LLMClient()
