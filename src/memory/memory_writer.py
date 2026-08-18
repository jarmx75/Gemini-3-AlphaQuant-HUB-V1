import uuid
from datetime import datetime
from typing import List, Optional
from src.memory.schemas import MemoryRecord, MemoryType
from src.memory.memory_store import AutomatonMemoryStore

class MemoryWriter:
    def __init__(self, store: AutomatonMemoryStore):
        self.store = store

    def write(self, memory_type: MemoryType, family: str, batch_id: str, claim_text: str, 
              source_path: str, source_commit: str, tags: List[str] = None, confidence: float = 1.0) -> str:
        """
        Escribe un recuerdo nuevo o actualiza uno existente.
        Aplica reglas anti-duplicación utilizando la restricción única (batch_id, family, claim_text).
        """
        now = datetime.utcnow().isoformat()
        
        record = MemoryRecord(
            memory_id=str(uuid.uuid4()),
            memory_type=memory_type,
            family=family,
            batch_id=batch_id,
            claim_text=claim_text,
            source_path=source_path,
            source_commit=source_commit,
            confidence=confidence,
            created_at=now,
            updated_at=now,
            tags=tags or []
        )
        
        # upsert_memory handles deduplication via the unique constraint
        self.store.upsert_memory(record)
        return record.memory_id
        
    def link(self, source_id: str, target_id: str, link_type: str = "DERIVED_FROM"):
        self.store.link_memories(source_id, target_id, link_type)
