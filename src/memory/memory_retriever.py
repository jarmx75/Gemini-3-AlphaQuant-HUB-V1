from typing import Optional, List
from src.memory.schemas import MemoryRecord
from src.memory.memory_store import AutomatonMemoryStore

class MemoryRetriever:
    def __init__(self, store: AutomatonMemoryStore):
        self.store = store

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        return self.store.get_memory(memory_id)
        
    def get_by_family(self, family: str) -> List[MemoryRecord]:
        # Helper, in a real scenario we'd query the DB directly, but let's use the search
        # or simple filter for now
        records = []
        for table in ['raw_memory', 'atomic_memory', 'scene_memory', 'core_memory']:
            all_recs = self.store.get_all_records(table)
            records.extend([r for r in all_recs if r.family == family])
        return records
