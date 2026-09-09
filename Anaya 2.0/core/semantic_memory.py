"""
Semantic & Episodic Memory Engine for Anaya 2.0
Provides zero-dependency BM25 + TF-IDF semantic retrieval across past conversations
and memories, ensuring authentic episodic recall without requiring external vector databases.
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
import datetime

from core.database import db_manager


class SemanticMemoryEngine:
    """
    Indexes and semantically retrieves historical conversation turns and memory facts
    using BM25 with n-gram overlap scoring.
    """

    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
        "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
        "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
        "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
        "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
        "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
        "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
        "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
        "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
        "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
        "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
        "they've", "this", "those", "through", "to", "too", "under", "until", "up",
        "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
        "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
        "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
        "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
        "yourself", "yourselves", "hai", "ka", "ki", "ke", "ko", "se", "aur", "bhi"
    }

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> List[str]:
        """Extracts meaningful lowercased alphanumeric tokens excluding stopwords."""
        words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
        return [w for w in words if w not in self.STOPWORDS]

    def _extract_bigrams(self, tokens: List[str]) -> List[str]:
        """Extracts adjacent bigram pairs for phrase-level semantic matching."""
        return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]

    def search_episodic_context(
        self,
        query: str,
        recent_cutoff_turns: int = 14,
        max_results: int = 3,
        min_score: float = 1.2
    ) -> List[Dict[str, Any]]:
        """
        Searches historical conversation turns (older than the sliding window) and memories
        that are semantically relevant to the current user query.
        """
        clean_query = query.strip()
        query_tokens = self._tokenize(clean_query)
        if not query_tokens:
            return []

        query_bigrams = set(self._extract_bigrams(query_tokens))

        # 1. Fetch candidate historical turns (excluding the recent context window)
        total_docs = 0
        try:
            total_docs = db_manager.convo_col.count_documents({})
        except Exception:
            return []

        # Skip if conversation history is too small to warrant episodic retrieval
        if total_docs <= recent_cutoff_turns:
            return []

        # Fetch up to 150 older conversational messages
        skip_count = min(recent_cutoff_turns, total_docs)
        try:
            cursor = db_manager.convo_col.find(
                {
                    "content": {"$exists": True},
                    "role": {"$in": ["user", "assistant"]}
                }
            ).sort("timestamp", -1).skip(skip_count).limit(120)
            candidates = list(cursor)
        except Exception:
            candidates = []

        if not candidates:
            return []

        # 2. Build corpus stats for BM25
        doc_tokens_list: List[List[str]] = []
        doc_lengths: List[int] = []
        doc_freq: Dict[str, int] = {}

        for doc in candidates:
            content = doc.get("content", "")
            tokens = self._tokenize(content)
            doc_tokens_list.append(tokens)
            doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                doc_freq[t] = doc_freq.get(t, 0) + 1

        n_docs = len(candidates)
        avg_doc_len = (sum(doc_lengths) / n_docs) if n_docs > 0 else 1.0

        # 3. Score candidates with BM25 + bigram boost
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for i, doc in enumerate(candidates):
            tokens = doc_tokens_list[i]
            d_len = doc_lengths[i]
            if d_len < 3:
                continue

            score = 0.0
            doc_token_counts: Dict[str, int] = {}
            for t in tokens:
                doc_token_counts[t] = doc_token_counts.get(t, 0) + 1

            for q_term in query_tokens:
                if q_term in doc_token_counts:
                    tf = doc_token_counts[q_term]
                    df = doc_freq.get(q_term, 1)
                    # Standard Robertson-Spärck Jones IDF
                    idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                    # BM25 TF formula
                    denom = tf + self.k1 * (1 - self.b + self.b * (d_len / avg_doc_len))
                    score += idf * ((tf * (self.k1 + 1)) / denom)

            # Bigram bonus
            doc_bigrams = set(self._extract_bigrams(tokens))
            common_bigrams = query_bigrams.intersection(doc_bigrams)
            if common_bigrams:
                score += len(common_bigrams) * 1.5

            if score >= min_score:
                scored.append((score, doc))

        # Sort descending by relevance score
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen_contents = set()
        for score, doc in scored[:max_results]:
            content = doc.get("content", "").strip()
            # Clean burst markers for clean display
            clean_content = content.replace(" ||| ", " ")
            if clean_content in seen_contents or len(clean_content) < 15:
                continue
            seen_contents.add(clean_content)

            # Calculate relative elapsed time
            ts = doc.get("timestamp")
            time_label = "Previously"
            if ts:
                now = datetime.datetime.now(datetime.timezone.utc) if getattr(ts, "tzinfo", None) else datetime.datetime.utcnow()
                diff = now - ts
                days = diff.days
                if days == 0:
                    time_label = "Earlier today"
                elif days == 1:
                    time_label = "Yesterday"
                elif days < 7:
                    time_label = f"{days} days ago"
                elif days < 30:
                    weeks = max(1, days // 7)
                    time_label = f"{weeks} week{'s' if weeks > 1 else ''} ago"
                else:
                    time_label = "A while back"

            results.append({
                "role": doc.get("role", "user"),
                "content": clean_content[:240],
                "time_label": time_label,
                "score": round(score, 2),
                "dialogID": doc.get("dialogID")
            })

        return results

    def generate_episodic_prompt(self, user_query: str) -> str:
        """
        Generates a concise episodic recall prompt injection based on the user's current message.
        """
        matches = self.search_episodic_context(user_query, max_results=2)
        if not matches:
            return ""

        lines = ["EPISODIC RECALL (Relevant Past Conversations from Memory):"]
        for m in matches:
            speaker = "Arpit" if m["role"] == "user" else "Anaya"
            lines.append(f"• [{m['time_label']}] {speaker}: \"{m['content']}\"")

        lines.append(
            "(Naturally connect with this past context if relevant, like an attentive close companion who truly remembers!)"
        )
        return "\n".join(lines)


# Singleton instance
semantic_memory_engine = SemanticMemoryEngine()
