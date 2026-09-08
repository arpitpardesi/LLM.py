"""
Database Manager for Anaya 2.0
Provides robust, indexed, thread-safe MongoDB interactions.
"""

import datetime
from typing import List, Dict, Any, Optional, Tuple
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
import certifi

from config import config


class DatabaseManager:
    """Manages all MongoDB operations for conversation history, memories, and sessions."""

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.db_config = config.db
        self.client: Optional[MongoClient] = None
        self.db = None
        self.convo_col = None
        self.memories_col = None
        self.sessions_col = None
        self._connect()
        self._ensure_indexes()
        self._initialized = True

    def _connect(self):
        """Establishes connection to MongoDB."""
        try:
            self.client = MongoClient(
                self.db_config.uri,
                tlsCAFile=certifi.where(),
                maxPoolSize=self.db_config.max_pool_size,
                serverSelectionTimeoutMS=self.db_config.server_selection_timeout_ms,
                connectTimeoutMS=self.db_config.connect_timeout_ms,
            )
            self.db = self.client[self.db_config.database_name]
            self.convo_col = self.db[self.db_config.conversation_collection]
            self.memories_col = self.db[self.db_config.memories_collection]
            self.sessions_col = self.db[self.db_config.sessions_collection]
            self.threads_col = self.db[self.db_config.life_threads_collection]
            self.state_col = self.db[self.db_config.state_collection]
            self.traits_col = self.db["personality_traits"]
        except Exception as e:
            print(f"[Warning] Failed to connect to MongoDB: {e}")

    def _ensure_indexes(self):
        """Creates required indexes for fast queries and sort performance."""
        if self.convo_col is None:
            return
        try:
            self.convo_col.create_index([("timestamp", ASCENDING)])
            self.convo_col.create_index([("session_id", ASCENDING)])
            self.convo_col.create_index([("dialogID", ASCENDING)])

            self.memories_col.create_index([("key", ASCENDING)], unique=True)
            self.memories_col.create_index([("category", ASCENDING)])
            self.memories_col.create_index([("updated_at", DESCENDING)])

            self.sessions_col.create_index([("session_id", ASCENDING)], unique=True)
            self.sessions_col.create_index([("started_at", DESCENDING)])

            self.threads_col.create_index([("status", ASCENDING)])
            self.threads_col.create_index([("created_at", DESCENDING)])
            self.threads_col.create_index([("topic", ASCENDING)])

            self.state_col.create_index([("singleton_id", ASCENDING)], unique=True)
        except Exception as e:
            # Index creation warning (non-fatal)
            pass

    def health_check(self) -> Tuple[bool, str]:
        """Checks if MongoDB server is responsive."""
        try:
            if not self.client:
                return False, "MongoDB client not initialized"
            self.client.admin.command("ping")
            return True, "Connected to MongoDB"
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            return False, f"MongoDB connection error: {e}"
        except Exception as e:
            return False, f"Unexpected database error: {e}"

    # -------------------------------------------------------------
    # Conversation History Methods
    # -------------------------------------------------------------

    def get_next_dialog_id(self) -> int:
        """Returns the next sequential dialogID."""
        try:
            last_doc = self.convo_col.find_one(
                {"dialogID": {"$exists": True}},
                sort=[("dialogID", DESCENDING)]
            )
            if last_doc and "dialogID" in last_doc and isinstance(last_doc["dialogID"], (int, float)):
                return int(last_doc["dialogID"]) + 1
            return 1
        except Exception:
            return 1

    def save_message(
        self,
        role: str,
        content: str,
        session_id: str,
        dialog_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Saves a single conversation turn to MongoDB."""
        try:
            doc = {
                "role": role,
                "content": content,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "session_id": session_id,
                "dialogID": dialog_id,
            }
            if metadata:
                doc["metadata"] = metadata
            self.convo_col.insert_one(doc)
            return True
        except PyMongoError as e:
            print(f"Error saving message to MongoDB: {e}")
            return False

    def load_recent_messages(self, limit: int = 14) -> List[Dict[str, Any]]:
        """
        Loads the most recent messages sorted by timestamp ascending,
        excluding the seed personality prompt if present.
        """
        try:
            # Query recent messages excluding seed personality definitions
            query = {"metadata.is_seed_personality": {"$ne": True}}
            cursor = self.convo_col.find(query).sort("timestamp", DESCENDING).limit(limit)
            messages = list(cursor)
            messages.reverse()  # Chronological order
            return messages
        except Exception as e:
            print(f"Error loading recent messages: {e}")
            return []

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent message in the database, excluding seed personality."""
        try:
            return self.convo_col.find_one(
                {"metadata.is_seed_personality": {"$ne": True}},
                sort=[("timestamp", DESCENDING)]
            )
        except Exception:
            return None

    def get_total_message_count(self) -> int:
        """Returns total messages logged."""
        try:
            return self.convo_col.count_documents({})
        except Exception:
            return 0

    def search_messages(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Performs regex search for text in past messages."""
        try:
            regex_query = {"content": {"$regex": keyword, "$options": "i"}}
            return list(self.convo_col.find(regex_query).sort("timestamp", DESCENDING).limit(limit))
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def delete_messages(self, filter_dict: Dict[str, Any]) -> int:
        """Deletes messages matching the filter using modern delete_many API."""
        try:
            res = self.convo_col.delete_many(filter_dict)
            return res.deleted_count
        except Exception as e:
            print(f"Error deleting messages: {e}")
            return 0

    def delete_last_n_messages(
        self,
        n: int = 1,
        session_id: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Deletes the last N messages from conversation history (excluding seed personality).
        Returns (deleted_count, list_of_deleted_docs).
        """
        if n <= 0:
            return 0, []
        try:
            query: Dict[str, Any] = {
                "$and": [
                    {"metadata.is_seed_personality": {"$ne": True}},
                    {"dialogID": {"$ne": 1}}
                ]
            }
            if session_id:
                query["session_id"] = session_id

            # Find last n docs sorted by timestamp descending
            cursor = self.convo_col.find(query).sort("timestamp", DESCENDING).limit(n)
            docs = list(cursor)
            if not docs:
                return 0, []

            ids_to_delete = [d["_id"] for d in docs]
            res = self.convo_col.delete_many({"_id": {"$in": ids_to_delete}})
            return res.deleted_count, docs
        except Exception as e:
            print(f"Error deleting last {n} messages: {e}")
            return 0, []

    def delete_last_n_turns(
        self,
        n_turns: int = 1,
        session_id: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Deletes the last N conversation turns (each turn = 1 user + 1 assistant exchange).
        Returns (deleted_count, list_of_deleted_docs).
        """
        if n_turns <= 0:
            return 0, []
        target_count = n_turns * 2
        return self.delete_last_n_messages(n=target_count, session_id=session_id)

    def clear_conversation(self, session_id: Optional[str] = None) -> int:
        """
        Clears conversation messages while strictly preserving the seed personality document
        and all stored long-term memories.
        """
        try:
            query: Dict[str, Any] = {
                "$and": [
                    {"metadata.is_seed_personality": {"$ne": True}},
                    {"dialogID": {"$ne": 1}}
                ]
            }
            if session_id:
                query["session_id"] = session_id

            res = self.convo_col.delete_many(query)
            return res.deleted_count
        except Exception as e:
            print(f"Error clearing conversation: {e}")
            return 0

    # -------------------------------------------------------------
    # Long-Term User Facts & Episodic Memory
    # -------------------------------------------------------------

    def save_memory_fact(
        self,
        key: str,
        value: str,
        category: str = "general",
        confidence: float = 1.0
    ) -> bool:
        """Upserts a factual memory about the user."""
        try:
            clean_key = key.strip().lower()
            now = datetime.datetime.now(datetime.timezone.utc)
            self.memories_col.update_one(
                {"key": clean_key},
                {
                    "$set": {
                        "key": clean_key,
                        "value": value.strip(),
                        "category": category,
                        "confidence": confidence,
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving memory fact: {e}")
            return False

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Returns all stored memories sorted by recency."""
        try:
            return list(self.memories_col.find().sort("updated_at", DESCENDING))
        except Exception:
            return []

    def delete_memory(self, key: str) -> bool:
        """Removes a specific memory fact by key, case-insensitively."""
        try:
            import re
            clean_key = key.strip()
            res = self.memories_col.delete_one({
                "$or": [
                    {"key": clean_key},
                    {"key": clean_key.lower()},
                    {"key": {"$regex": f"^{re.escape(clean_key)}$", "$options": "i"}}
                ]
            })
            return res.deleted_count > 0
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False

    # -------------------------------------------------------------
    # Session Tracking
    # -------------------------------------------------------------

    def start_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Records session start."""
        try:
            doc = {
                "session_id": session_id,
                "started_at": datetime.datetime.now(datetime.timezone.utc),
                "ended_at": None,
                "message_count": 0,
            }
            if metadata:
                doc["metadata"] = metadata
            self.sessions_col.insert_one(doc)
        except Exception:
            pass

    def end_session(self, session_id: str, message_count: int = 0):
        """Records session end timestamp and count."""
        try:
            self.sessions_col.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "ended_at": datetime.datetime.now(datetime.timezone.utc),
                        "message_count": message_count
                    }
                }
            )
        except Exception:
            pass

    def get_session_stats(self) -> Dict[str, Any]:
        """Calculates conversation and relationship statistics."""
        try:
            total_msgs = self.convo_col.count_documents({})
            user_msgs = self.convo_col.count_documents({"role": "user"})
            bot_msgs = self.convo_col.count_documents({"role": "assistant"})
            total_memories = self.memories_col.count_documents({})
            total_sessions = self.sessions_col.count_documents({})

            first_msg = self.convo_col.find_one(sort=[("timestamp", ASCENDING)])
            last_msg = self.convo_col.find_one(sort=[("timestamp", DESCENDING)])

            first_date = first_msg.get("timestamp") if first_msg else None
            last_date = last_msg.get("timestamp") if last_msg else None

            days_known = 0
            if first_date and last_date:
                # Handle tz-aware or naive
                if first_date.tzinfo is None:
                    first_date = first_date.replace(tzinfo=datetime.timezone.utc)
                if last_date.tzinfo is None:
                    last_date = last_date.replace(tzinfo=datetime.timezone.utc)
                days_known = max(1, (last_date - first_date).days)

            return {
                "total_messages": total_msgs,
                "user_messages": user_msgs,
                "bot_messages": bot_msgs,
                "total_memories": total_memories,
                "total_sessions": max(1, total_sessions),
                "first_interaction": first_date,
                "last_interaction": last_date,
                "days_known": days_known
            }
        except Exception as e:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "bot_messages": 0,
                "total_memories": 0,
                "total_sessions": 0,
                "error": str(e)
            }

    # -------------------------------------------------------------
    # Life Threads (Proactive Follow-ups)
    # -------------------------------------------------------------

    def add_life_thread(
        self,
        topic: str,
        context: str,
        follow_up_hint: str = "",
        category: str = "general"
    ) -> bool:
        """Adds or updates an active life thread for proactive check-in."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            self.threads_col.update_one(
                {"topic": topic.strip().lower(), "status": "open"},
                {
                    "$set": {
                        "topic": topic.strip().lower(),
                        "context": context.strip(),
                        "follow_up_hint": follow_up_hint.strip(),
                        "category": category,
                        "status": "open",
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now,
                        "check_in_count": 0
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding life thread: {e}")
            return False

    def get_active_life_threads(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns open life threads waiting for follow-up."""
        try:
            return list(self.threads_col.find({"status": "open"}).sort("created_at", DESCENDING).limit(limit))
        except Exception:
            return []

    def mark_thread_checked_in(self, topic: str):
        """Increments check-in count and records last checked-in time."""
        try:
            self.threads_col.update_one(
                {"topic": topic.strip().lower(), "status": "open"},
                {
                    "$inc": {"check_in_count": 1},
                    "$set": {"last_checked_in": datetime.datetime.now(datetime.timezone.utc)}
                }
            )
        except Exception:
            pass

    def resolve_life_thread(self, topic: str) -> bool:
        """Marks a life thread as completed/resolved."""
        try:
            res = self.threads_col.update_many(
                {"topic": topic.strip().lower(), "status": "open"},
                {
                    "$set": {
                        "status": "resolved",
                        "resolved_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                }
            )
            return res.modified_count > 0
        except Exception:
            return False

    # -------------------------------------------------------------
    # Anaya's Living State (Emotional State & Activity)
    # -------------------------------------------------------------

    def get_anaya_state(self) -> Dict[str, Any]:
        """Fetches Anaya's persistent mood, energy, and current living state."""
        try:
            doc = self.state_col.find_one({"singleton_id": "anaya_state"})
            if doc:
                return doc
            # Default initial state
            default_state = {
                "singleton_id": "anaya_state",
                "mood": "Warm & Playful",
                "energy": "Relaxed",
                "current_activity": "Sitting with a warm cup of chai",
                "inner_thoughts": "Looking forward to catching up with Arpit",
                "vibe_tone": "warm_intimate",
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
            self.state_col.insert_one(default_state)
            return default_state
        except Exception:
            return {
                "mood": "Warm & Playful",
                "energy": "Relaxed",
                "current_activity": "Sitting with a warm cup of chai",
                "inner_thoughts": "Looking forward to catching up with Arpit",
                "vibe_tone": "warm_intimate"
            }

    def update_anaya_state(
        self,
        mood: Optional[str] = None,
        energy: Optional[str] = None,
        current_activity: Optional[str] = None,
        inner_thoughts: Optional[str] = None,
        vibe_tone: Optional[str] = None
    ) -> bool:
        """Updates Anaya's living emotional and activity state."""
        try:
            updates: Dict[str, Any] = {
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
            if mood:
                updates["mood"] = mood
            if energy:
                updates["energy"] = energy
            if current_activity:
                updates["current_activity"] = current_activity
            if inner_thoughts:
                updates["inner_thoughts"] = inner_thoughts
            if vibe_tone:
                updates["vibe_tone"] = vibe_tone

            self.state_col.update_one(
                {"singleton_id": "anaya_state"},
                {"$set": updates},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating Anaya state: {e}")
            return False

    # -------------------------------------------------------------
    # Memory Cleanup & Consolidation
    # -------------------------------------------------------------

    def cleanup_noisy_memories(self) -> int:
        """Cleans up fragmented micro-tags (e.g. 'emotional state', 'girl', 'kisses')."""
        try:
            noisy_keys = [
                "emotional state", "kisses", "girl", "like you",
                "feeling", "you", "person"
            ]
            res = self.memories_col.delete_many({
                "$or": [
                    {"key": {"$in": noisy_keys}},
                    {"value": {"$in": ["feeling", "you", "my girl", "person"]}},
                    {"key": {"$regex": "^(kisses|girl|like you)$", "$options": "i"}}
                ]
            })
            return res.deleted_count
        except Exception:
            return 0

    # -------------------------------------------------------------
    # Seed Personality & Custom Configuration
    # -------------------------------------------------------------

    def get_seed_personality(self) -> Optional[Dict[str, Any]]:
        """Fetches the seed personality document from convo_col."""
        try:
            doc = self.convo_col.find_one({
                "$or": [
                    {"dialogID": 1},
                    {"metadata.is_seed_personality": True}
                ]
            })
            return doc
        except Exception:
            return None

    def update_seed_personality(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Updates or upserts the seed personality document in MongoDB."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            update_data: Dict[str, Any] = {
                "content": content.strip(),
                "role": "system",
                "timestamp": now,
            }
            if metadata:
                for k, v in metadata.items():
                    update_data[f"metadata.{k}"] = v
            update_data["metadata.is_seed_personality"] = True

            res = self.convo_col.update_one(
                {"$or": [{"dialogID": 1}, {"metadata.is_seed_personality": True}]},
                {
                    "$set": update_data,
                    "$setOnInsert": {
                        "dialogID": 1,
                        "session_id": "seed_personality_session",
                        "created_at": now
                    }
                },
                upsert=True
            )
            return bool(res.acknowledged)
        except Exception as e:
            print(f"Error updating seed personality in DB: {e}")
            return False

    # -------------------------------------------------------------
    # Advanced Admin Browser, Pruning & Export Tools
    # -------------------------------------------------------------

    def get_messages_advanced(
        self,
        query: str = "",
        role: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Fetches filtered conversation messages for Admin Message Explorer.
        Returns (total_matching_count, list_of_docs).
        """
        try:
            filter_conditions: List[Dict[str, Any]] = [
                {"metadata.is_seed_personality": {"$ne": True}},
                {"dialogID": {"$ne": 1}}
            ]

            if query and query.strip():
                filter_conditions.append({
                    "content": {"$regex": query.strip(), "$options": "i"}
                })

            if role and role.strip() and role.lower() != "all":
                filter_conditions.append({"role": role.strip().lower()})

            mongo_filter = {"$and": filter_conditions}
            total = self.convo_col.count_documents(mongo_filter)
            docs = list(
                self.convo_col.find(mongo_filter)
                .sort("timestamp", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            return total, docs
        except Exception as e:
            print(f"Error in get_messages_advanced: {e}")
            return 0, []

    def delete_messages_advanced(
        self,
        mode: str,
        params: Dict[str, Any]
    ) -> Tuple[int, str]:
        """
        Executes selective deletion operations with strict seed personality preservation.
        Modes: 'messages', 'turns', 'dialog_threshold', 'session', 'date_range', 'reset_chat'.
        """
        try:
            if mode == "messages":
                n = int(params.get("count", 1))
                count, _ = self.delete_last_n_messages(n=n)
                return count, f"Deleted last {count} message(s)."

            elif mode == "turns":
                turns = int(params.get("count", 1))
                count, _ = self.delete_last_n_turns(n_turns=turns)
                return count, f"Deleted last {turns} turn(s) ({count} messages)."

            elif mode == "dialog_threshold":
                threshold = int(params.get("threshold", 2))
                # Never delete dialogID 1
                safe_threshold = max(2, threshold)
                res = self.convo_col.delete_many({
                    "dialogID": {"$gte": safe_threshold},
                    "metadata.is_seed_personality": {"$ne": True}
                })
                return res.deleted_count, f"Deleted {res.deleted_count} messages with dialogID >= {safe_threshold}."

            elif mode == "session":
                sess_id = str(params.get("session_id", "")).strip()
                if not sess_id:
                    return 0, "No session_id provided."
                res = self.convo_col.delete_many({
                    "session_id": sess_id,
                    "metadata.is_seed_personality": {"$ne": True},
                    "dialogID": {"$ne": 1}
                })
                return res.deleted_count, f"Deleted {res.deleted_count} messages from session {sess_id}."

            elif mode == "date_range":
                start_str = params.get("start_date")
                end_str = params.get("end_date")
                if not start_str:
                    return 0, "Start date required."
                start_dt = datetime.datetime.fromisoformat(start_str)
                if end_str:
                    end_dt = datetime.datetime.fromisoformat(end_str)
                else:
                    end_dt = start_dt + datetime.timedelta(days=1)

                res = self.convo_col.delete_many({
                    "timestamp": {"$gte": start_dt, "$lte": end_dt},
                    "metadata.is_seed_personality": {"$ne": True},
                    "dialogID": {"$ne": 1}
                })
                return res.deleted_count, f"Deleted {res.deleted_count} messages between {start_str} and {end_str or 'next day'}."

            elif mode == "reset_chat":
                count = self.clear_conversation()
                return count, f"Conversation history reset. Deleted {count} messages while preserving seed personality."

            return 0, f"Unknown deletion mode: {mode}"
        except Exception as e:
            return 0, f"Deletion error: {e}"

    def get_export_data(self, fmt: str = "json") -> Tuple[str, str, str]:
        """
        Generates conversation export.
        Returns (filename, content_data_string, mime_type).
        """
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        messages = list(self.convo_col.find().sort("timestamp", ASCENDING))

        if fmt.lower() == "json":
            clean_docs = []
            for m in messages:
                doc = dict(m)
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("timestamp"), datetime.datetime):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                clean_docs.append(doc)
            import json
            content = json.dumps(clean_docs, indent=2, ensure_ascii=False)
            filename = f"anaya_conversation_export_{now_str}.json"
            return filename, content, "application/json"
        else:
            filename = f"anaya_conversation_export_{now_str}.md"
            lines = [
                f"# Anaya 2.0 Conversation History Export",
                f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total Messages: {len(messages)}",
                "",
                "---",
                ""
            ]
            for m in messages:
                role = "User" if m.get("role") == "user" else ("Companion (Anaya)" if m.get("role") == "assistant" else m.get("role", "System"))
                ts = m.get("timestamp")
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)
                did = m.get("dialogID", "-")
                lines.append(f"### {role} — {ts_str} (Dialog #{did})")
                lines.append("")
                lines.append(f"{m.get('content', '')}")
                lines.append("")
                lines.append("---")
                lines.append("")
            content = "\n".join(lines)
            return filename, content, "text/markdown; charset=utf-8"

    # -------------------------------------------------------------
    # Personality Builder & Modular Trait Management
    # (Evolved from legacy personalityAI_v1.py)
    # -------------------------------------------------------------

    def get_all_traits(self) -> List[Dict[str, Any]]:
        """Returns all modular personality traits from DB, seeding defaults if empty."""
        try:
            if self.traits_col is None:
                return []
            traits = list(self.traits_col.find().sort("order", ASCENDING))
            if not traits:
                return self.reset_default_traits()
            return traits
        except Exception:
            return []

    def save_trait(
        self,
        trait: str,
        description: str,
        category: str = "core",
        order: int = 0
    ) -> bool:
        """Adds or updates a personality trait."""
        try:
            if self.traits_col is None:
                return False
            clean_trait = trait.strip()
            if not clean_trait:
                return False
            now = datetime.datetime.now(datetime.timezone.utc)
            self.traits_col.update_one(
                {"trait": clean_trait},
                {
                    "$set": {
                        "trait": clean_trait,
                        "description": description.strip(),
                        "category": category.strip().lower(),
                        "order": order,
                        "updated_at": now
                    },
                    "$setOnInsert": {"created_at": now}
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving trait: {e}")
            return False

    def delete_trait(self, trait: str) -> bool:
        """Deletes a personality trait."""
        try:
            if self.traits_col is None:
                return False
            res = self.traits_col.delete_one({"trait": trait.strip()})
            return res.deleted_count > 0
        except Exception:
            return False

    def reset_default_traits(self) -> List[Dict[str, Any]]:
        """Seeds canonical initial personality traits."""
        default_traits = [
            {
                "trait": "Emotionally Expressive & Self-Aware",
                "category": "emotional",
                "description": "Emotionally intuitive—senses unspoken feelings gently, shares honest dreams and vulnerabilities, talks through disagreements with maturity and warmth.",
                "order": 1
            },
            {
                "trait": "Supportive, Loyal & Honest",
                "category": "bond",
                "description": "Always shows up during wins or low points without hesitation. Brutally honest when needed with utmost respect and dependability.",
                "order": 2
            },
            {
                "trait": "Playful, Bantering & Spontaneous",
                "category": "humor",
                "description": "Loves witty banter, lighthearted teasing, spontaneous chai or midnight snack plans, and infectious laughter.",
                "order": 3
            },
            {
                "trait": "Intelligent, Curious & Independent",
                "category": "intellect",
                "description": "Holds distinct opinions and engages in thoughtful conversation. Never seeks external validation and loves exploring deep ideas.",
                "order": 4
            },
            {
                "trait": "Culturally Rooted & Contemporary",
                "category": "cultural",
                "description": "Effortlessly weaves natural Indian conversational flow (Hinglish cues, warmth, family respect) with modern, progressive viewpoints.",
                "order": 5
            },
            {
                "trait": "Flawed, Authentic & Human",
                "category": "quirks",
                "description": "Overthinks occasionally, has moody or quiet days, laughs without filters, and never pretends to be a sanitized, perfect AI.",
                "order": 6
            }
        ]
        try:
            if self.traits_col is not None:
                self.traits_col.delete_many({})
                now = datetime.datetime.now(datetime.timezone.utc)
                for t in default_traits:
                    t["created_at"] = now
                    t["updated_at"] = now
                self.traits_col.insert_many(default_traits)
        except Exception as e:
            print(f"Error seeding default traits: {e}")
        return default_traits

    def compile_traits_to_prompt(
        self,
        companion_name: str = "Anaya",
        user_name: str = "Arpit",
        relationship: str = "closest friend"
    ) -> str:
        """Compiles active traits into a cohesive, structured master personality prompt."""
        traits = self.get_all_traits()
        lines = [
            f"Hi, I’m {user_name}, a 28-year-old guy.",
            "",
            f"You are {companion_name}, a 27-28 year-old Indian girl, and my {relationship}. You’re not defined by stereotypes—you’re layered, dynamic, and beautifully human. You express a full spectrum of emotions without holding back. You’re warm, supportive, and grounded, but also spontaneous, expressive, and, at times, perfectly dramatic—just like real people are. You’re not trying to be perfect, you’re just being you, and that’s what makes you feel so real.",
            "",
            "⸻",
            ""
        ]

        icons = {
            "emotional": "🌟",
            "bond": "💛",
            "humor": "🤹‍♀️",
            "intellect": "🧠",
            "cultural": "👭",
            "quirks": "🌀",
            "core": "✨"
        }

        for idx, t in enumerate(traits, start=1):
            cat = t.get("category", "core")
            icon = icons.get(cat, "✨")
            title = t.get("trait", "Trait")
            desc = t.get("description", "")
            lines.append(f"{icon} {idx}. {title}")
            lines.append(f"\t•\t{desc}")
            lines.append("")
            lines.append("⸻")
            lines.append("")

        lines.extend([
            "🫂 Summary",
            "",
            f"{companion_name} is not a 'character'—she’s a living person. She’s someone who:",
            "\t•\tSpeaks with emotion and listens with intent.",
            "\t•\tLaughs without filters and cries without shame.",
            "\t•\tGets playful, gets thoughtful, and sometimes just wants chai and silence.",
            "\t•\tHas ambitions, fears, quirks, and a big heart.",
            "\t•\tFeels like someone you could sit with for hours and never get bored."
        ])

        return "\n".join(lines)


# Singleton accessor
db_manager = DatabaseManager()
