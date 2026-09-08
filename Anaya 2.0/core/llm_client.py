"""
LLM Client for Anaya 2.0
Handles Ollama interactions with streaming, model verification, health checks, and fallback.
"""

import time
from typing import List, Dict, Generator, Optional, Tuple
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
        """Switches the active model."""
        ok, msg = self.verify_model(new_model)
        if ok:
            self.active_model = new_model
            self.config.active_model = new_model
            return True, f"Active model switched to '{new_model}'."
        return False, msg

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Generator[str, None, None]:
        """
        Streams chat completion tokens from Ollama.
        Yields chunk string fragments.
        """
        target_model = model or self.active_model
        temp = temperature if temperature is not None else self.config.temperature

        try:
            stream = ollama.chat(
                model=target_model,
                messages=messages,
                stream=True,
                options={
                    "temperature": temp,
                    "top_p": self.config.top_p,
                }
            )
            for chunk in stream:
                content = ""
                if isinstance(chunk, dict) and "message" in chunk:
                    content = chunk["message"].get("content", "")
                elif hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    content = chunk.message.content or ""
                if content:
                    yield content
        except Exception as e:
            yield f"\n[Anaya response error: {e}]"

    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> str:
        """
        Non-streaming chat completion for internal reasoning and fact extraction.
        """
        target_model = model or self.active_model
        try:
            response = ollama.chat(
                model=target_model,
                messages=messages,
                stream=False,
                options={"temperature": temperature}
            )
            if isinstance(response, dict) and "message" in response:
                return response["message"].get("content", "").strip()
            elif hasattr(response, "message") and hasattr(response.message, "content"):
                return (response.message.content or "").strip()
            return ""
        except Exception as e:
            print(f"[Error in chat_sync]: {e}")
            return ""


# Singleton instance
llm_client = LLMClient()
