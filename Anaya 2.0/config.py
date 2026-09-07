"""
Production Configuration for Anaya 2.0
Centralizes database, model, prompt, and memory configurations.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

# Base directory paths
ANAYA_DIR = Path(__file__).resolve().parent
ROOT_DIR = ANAYA_DIR.parent

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
    cluster_host: str = "cosmos.f2pie.mongodb.net"
    app_name: str = DB_APP_NAME
    database_name: str = "cosmosBot"
    
    # Collections
    conversation_collection: str = "anaya"
    memories_collection: str = "anaya_memories"
    sessions_collection: str = "anaya_sessions"
    life_threads_collection: str = "anaya_life_threads"
    state_collection: str = "anaya_state"
    
    # Connection pooling and timeouts
    max_pool_size: int = 50
    server_selection_timeout_ms: int = 6000
    connect_timeout_ms: int = 6000

    @property
    def uri(self) -> str:
        if self.username and self.password:
            return (
                f"mongodb+srv://{self.username}:{self.password}@"
                f"{self.cluster_host}/?retryWrites=true&w=majority&appName={self.app_name}"
            )
        # Fallback local connection if no cloud credentials provided
        return "mongodb://localhost:27017/"


@dataclass
class LLMConfig:
    """Ollama Model & Inference Configuration"""
    default_model: str = "llama3.2:latest"
    uncensored_model: str = "artifish/llama3.2-uncensored:latest"
    active_model: str = "llama3.2:latest"
    temperature: float = 0.75
    top_p: float = 0.9
    stream_output: bool = True
    context_window_turns: int = 14  # Number of recent message turns to include in context
    max_facts_in_prompt: int = 6    # Maximum relevant user memories injected into prompt


@dataclass
class UserProfile:
    """User and Companion Profile Definitions"""
    user_name: str = "Arpit"
    user_full_name: str = "Arpit Pardesi"
    user_age: int = 27
    user_timezone: str = "Asia/Kolkata"
    
    companion_name: str = "Anaya"
    companion_age: int = 26
    relationship: str = "Closest Friend"


@dataclass
class AppConfig:
    """Master Application Configuration"""
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    user: UserProfile = field(default_factory=UserProfile)
    
    # Paths
    personality_file: Path = ANAYA_DIR / "personality.txt"
    log_dir: Path = ANAYA_DIR / "logs"
    export_dir: Path = ANAYA_DIR / "exports"
    
    # Logging
    log_level: str = "INFO"
    enable_fact_extraction: bool = True


# Global configuration instance
config = AppConfig()

# Ensure required directories exist
config.log_dir.mkdir(parents=True, exist_ok=True)
config.export_dir.mkdir(parents=True, exist_ok=True)
