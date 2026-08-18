from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import json

class MemoryType(Enum):
    RAW = "RAW"          # L0: Immutable logs, exact results
    ATOMIC = "ATOMIC"    # L1: Facts, metrics, extracted hypotheses
    SCENE = "SCENE"      # L2: Grouped by domain (trend, mean_reversion, etc.)
    CORE = "CORE"        # L3: Stable rules, rejected constraints, surviving knowledge

@dataclass
class MemoryRecord:
    memory_id: str
    memory_type: MemoryType
    family: str
    batch_id: str
    claim_text: str
    source_path: str
    source_commit: str
    confidence: float
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "family": self.family,
            "batch_id": self.batch_id,
            "claim_text": self.claim_text,
            "source_path": self.source_path,
            "source_commit": self.source_commit,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": json.dumps(self.tags)
        }

@dataclass
class MemoryQueryResult:
    record: MemoryRecord
    score: float
