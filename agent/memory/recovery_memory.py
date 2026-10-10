import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings


DB_PATH = Path("recovery_memory.db")
CHROMA_DIR = Path("chroma_recovery")


class RecoveryMemory:
    def __init__(self):
        # SQLite for full records
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS recoveries (
                signature TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT
            )
        """)
        self._conn.commit()

        # Chroma for vector search
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="recovery_strategies",
        )

    # ---------- Store / update ----------

    def store_success(self, signature: str, payload: dict) -> None:
        """Record that a strategy worked for this signature."""
        existing = self._get(signature)
        if existing:
            payload = existing["payload"]  # keep the working strategy
            success = existing["success_count"] + 1
            failure = existing["failure_count"]
        else:
            success = 1
            failure = 0

        record = {
            "signature": signature,
            "payload": payload,
            "success_count": success,
            "failure_count": failure,
            "last_used": datetime.utcnow().isoformat(),
        }
        self._conn.execute(
            "INSERT OR REPLACE INTO recoveries VALUES (?, ?, ?, ?, ?)",
            (signature, json.dumps(payload), success, failure, record["last_used"]),
        )
        self._conn.commit()

        # Upsert into Chroma
        self._collection.upsert(
            ids=[signature],
            documents=[signature],
            metadatas=[{"success_count": success, "failure_count": failure}],
        )

    def store_failure(self, signature: str) -> None:
        """Record that a strategy failed."""
        existing = self._get(signature)
        if not existing:
            return
        self._conn.execute(
            "UPDATE recoveries SET failure_count = failure_count + 1 WHERE signature = ?",
            (signature,),
        )
        self._conn.commit()

    # ---------- Retrieve ----------

    def find_similar(self, signature: str, top_k: int = 3) -> list[dict]:
        """Return similar past failures, sorted by similarity."""
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[signature],
            n_results=min(top_k, self._collection.count()),
        )

        out = []
        for sig in results["ids"][0]:
            rec = self._get(sig)
            if rec:
                out.append(rec)
        return out

    # ---------- Internal ----------

    def _get(self, signature: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT signature, payload, success_count, failure_count, last_used "
            "FROM recoveries WHERE signature = ?",
            (signature,),
        ).fetchone()
        if not row:
            return None
        return {
            "signature": row[0],
            "payload": json.loads(row[1]),
            "success_count": row[2],
            "failure_count": row[3],
            "last_used": row[4],
        }


# Singleton
_instance: Optional[RecoveryMemory] = None


def get_recovery_memory() -> RecoveryMemory:
    global _instance
    if _instance is None:
        _instance = RecoveryMemory()
    return _instance