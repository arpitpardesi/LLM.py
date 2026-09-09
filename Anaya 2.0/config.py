"""
Production Configuration for Anaya 2.0
Centralizes database, model, prompt, user profile, and memory configurations.
All static/hardcoded values are replaced with dynamic environment overrides
and persisted profile configuration (profile.json).
"""

import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# Base directory paths
ANAYA_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANAYA_DIR.parent
PROFILE_CONFIG_FILE = ANAYA_DIR / "profile.json"

# Ensure root directory is in sys.path to discover cred.py if present
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Attempt to load credentials from cred.py or environment variables
DB_USERNAME = os.getenv("MONGO_USER", "")
DB_PASSWORD = os.getenv("MONGO_PASS", "")
DB_APP_NAME = os.getenv("MONGO_APP_NAME", "Cosmos")

try:
    import cred
    if not DB_USERNAME and hasattr(cred, "db_username"):
        DB_USERNAME = cred.db_username
    if not DB_PASSWORD and hasattr(cred, "db_password"):
        DB_PASSWORD = cred.db_password
    if hasattr(cred, "db_app_name"):
        DB_APP_NAME = cred.db_app_name
except ImportError:
    pass


@dataclass
class DatabaseConfig:
    """MongoDB Connection and Collection Configuration"""
    username: str = DB_USERNAME
    password: str = DB_PASSWORD
    cluster_host: str = field(default_factory=lambda: os.getenv("MONGO_CLUSTER_HOST", "cosmos.f2pie.mongodb.net"))
    app_name: str = field(default_factory=lambda: os.getenv("MONGO_APP_NAME", DB_APP_NAME))
    database_name: str = field(default_factory=lambda: os.getenv("MONGO_DATABASE", "cosmosBot"))
    
    # Collections
    conversation_collection: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION_ANAYA", "anaya"))
    memories_collection: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION_MEMORIES", "anaya_memories"))
    sessions_collection: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION_SESSIONS", "anaya_sessions"))
    life_threads_collection: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION_THREADS", "anaya_life_threads"))
    state_collection: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION_STATE", "anaya_state"))
    
    # Connection pooling and timeouts
    max_pool_size: int = field(default_factory=lambda: int(os.getenv("MONGO_MAX_POOL_SIZE", "50")))
    server_selection_timeout_ms: int = field(default_factory=lambda: int(os.getenv("MONGO_SERVER_TIMEOUT_MS", "6000")))
    connect_timeout_ms: int = field(default_factory=lambda: int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "6000")))

    @property
    def uri(self) -> str:
        if self.username and self.password:
            return (
                f"mongodb+srv://{self.username}:{self.password}@"
                f"{self.cluster_host}/?retryWrites=true&w=majority&appName={self.app_name}"
            )
        # Fallback local connection if no cloud credentials provided
        return os.getenv("MONGO_LOCAL_URI", "mongodb://localhost:27017/")


@dataclass
class LLMConfig:
    """Ollama Model & Inference Configuration"""
    default_model: str = field(default_factory=lambda: os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:latest"))
    uncensored_model: str = field(default_factory=lambda: os.getenv("OLLAMA_UNCENSORED_MODEL", "artifish/llama3.2-uncensored:latest"))
    active_model: str = field(default_factory=lambda: os.getenv("OLLAMA_ACTIVE_MODEL", "llama3.2:latest"))
    temperature: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TEMPERATURE", "0.75")))
    top_p: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TOP_P", "0.9")))
    stream_output: bool = field(default_factory=lambda: os.getenv("OLLAMA_STREAM_OUTPUT", "True").lower() == "true")
    context_window_turns: int = field(default_factory=lambda: int(os.getenv("OLLAMA_CONTEXT_TURNS", "14")))
    max_facts_in_prompt: int = field(default_factory=lambda: int(os.getenv("OLLAMA_MAX_FACTS", "6")))
    num_ctx: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "2048")))
    num_ctx_internal: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX_INTERNAL", "768")))
    keep_alive: str = field(default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "3m"))
    num_threads: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_THREADS", "6")))


@dataclass
class UserProfile:
    """User and Companion Profile Definitions.
    Dynamically configurable via environment variables, profile.json, and in-app settings.
    No hardcoded static locks.
    """
    user_name: str = field(default_factory=lambda: os.getenv("ANAYA_USER_NAME", os.getenv("USER_NAME", "Arpit")))
    user_full_name: str = field(default_factory=lambda: os.getenv("ANAYA_USER_FULL_NAME", os.getenv("USER_FULL_NAME", "Arpit Pardesi")))
    user_age: int = field(default_factory=lambda: int(os.getenv("ANAYA_USER_AGE", os.getenv("USER_AGE", "28"))))
    user_gender: str = field(default_factory=lambda: os.getenv("ANAYA_USER_GENDER", os.getenv("USER_GENDER", "Male")))
    user_timezone: str = field(default_factory=lambda: os.getenv("ANAYA_USER_TIMEZONE", os.getenv("USER_TIMEZONE", "Asia/Kolkata")))
    
    companion_name: str = field(default_factory=lambda: os.getenv("ANAYA_COMPANION_NAME", os.getenv("COMPANION_NAME", "Anaya")))
    companion_age: int = field(default_factory=lambda: int(os.getenv("ANAYA_COMPANION_AGE", os.getenv("COMPANION_AGE", "27"))))
    companion_gender: str = field(default_factory=lambda: os.getenv("ANAYA_COMPANION_GENDER", os.getenv("COMPANION_GENDER", "Female")))
    relationship: str = field(default_factory=lambda: os.getenv("ANAYA_RELATIONSHIP", os.getenv("RELATIONSHIP", "Closest Friend & Confidante")))

    def load_from_file(self, filepath: Optional[Path] = None) -> bool:
        """Loads configuration values from JSON file if present."""
        target = filepath or PROFILE_CONFIG_FILE
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(self, k) and v is not None:
                        if "age" in k:
                            try:
                                v = int(v)
                            except (ValueError, TypeError):
                                pass
                        setattr(self, k, v)
                return True
            except Exception as e:
                print(f"[config] Warning: Failed to load profile from {target}: {e}")
        return False

    def save(self, filepath: Optional[Path] = None) -> bool:
        """Persists current user profile values to JSON file."""
        target = filepath or PROFILE_CONFIG_FILE
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[config] Warning: Failed to save profile to {target}: {e}")
            return False

    def update(self, **kwargs) -> bool:
        """Updates profile attributes and immediately persists to disk."""
        changed = False
        for k, v in kwargs.items():
            if hasattr(self, k) and v is not None:
                if "age" in k:
                    try:
                        v = int(v)
                    except (ValueError, TypeError):
                        pass
                setattr(self, k, v)
                changed = True
        if changed:
            return self.save()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Returns dictionary representation of profile."""
        return asdict(self)


@dataclass
class AppConfig:
    """Master Application Configuration"""
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    user: UserProfile = field(default_factory=UserProfile)
    
    # Paths
    personality_file: Path = field(default_factory=lambda: ANAYA_DIR / "personality.txt")
    log_dir: Path = field(default_factory=lambda: ANAYA_DIR / "logs")
    export_dir: Path = field(default_factory=lambda: ANAYA_DIR / "exports")
    profile_file: Path = field(default_factory=lambda: PROFILE_CONFIG_FILE)
    
    # Logging & Features
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    enable_fact_extraction: bool = field(default_factory=lambda: os.getenv("ENABLE_FACT_EXTRACTION", "True").lower() == "true")

    def __post_init__(self):
        # Load profile if profile.json exists, otherwise create it
        if self.profile_file.exists():
            self.user.load_from_file(self.profile_file)
        else:
            self.user.save(self.profile_file)


# Global configuration instance
config = AppConfig()

# Ensure required directories exist
config.log_dir.mkdir(parents=True, exist_ok=True)
config.export_dir.mkdir(parents=True, exist_ok=True)
