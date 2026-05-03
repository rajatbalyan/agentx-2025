"""Optional vector memory for agents — never crashes the pipeline if Chroma is unavailable."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class AgentMemory:
    """
    Minimal optional memory wrapper. When disabled or Chroma fails to load,
    all operations are safe no-ops.
    """

    def __init__(
        self,
        agent_name: str,
        db_path: str = "",
        enabled: bool = True,
        collection_prefix: str = "sentry",
    ) -> None:
        self.agent_name = agent_name
        self.db_path = db_path
        self.collection_prefix = collection_prefix
        self._enabled = bool(enabled)
        self._client: Any = None
        self._collection: Any = None

        if not self._enabled:
            return

        try:
            import chromadb  # noqa: F401

            self._client = chromadb.PersistentClient(path=db_path)
            coll_name = f"{collection_prefix}_{agent_name}"
            self._collection = self._client.get_or_create_collection(name=coll_name)
        except Exception as exc:
            logger.warning(
                "AgentMemory disabled (Chroma unavailable)",
                agent=agent_name,
                error=str(exc),
            )
            self._enabled = False
            self._client = None
            self._collection = None

    def store(self, data: Dict[str, Any], doc_type: str) -> None:
        if not self._enabled or self._collection is None:
            return
        try:
            payload = json.dumps(data, default=str)
            doc_id = f"{self.agent_name}_{doc_type}_{uuid.uuid4().hex}"
            self._collection.add(
                ids=[doc_id],
                documents=[payload],
                metadatas=[{"doc_type": doc_type, "agent": self.agent_name}],
            )
        except Exception as exc:
            logger.warning(
                "AgentMemory.store failed",
                agent=self.agent_name,
                doc_type=doc_type,
                error=str(exc),
            )

    def add(self, documents: List[str], metadatas: Optional[List[dict]] = None) -> None:
        if not self._enabled or self._collection is None:
            return
        try:
            ids = [f"{self.agent_name}_{uuid.uuid4().hex}" for _ in documents]
            self._collection.add(documents=documents, metadatas=metadatas, ids=ids)
        except Exception as exc:
            logger.warning("AgentMemory.add failed", agent=self.agent_name, error=str(exc))

    def query(self, query_texts: List[str], n_results: int = 5) -> dict:
        if not self._enabled or self._collection is None:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        try:
            return self._collection.query(query_texts=query_texts, n_results=n_results)
        except Exception as exc:
            logger.warning("AgentMemory.query failed", agent=self.agent_name, error=str(exc))
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
