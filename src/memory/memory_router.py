from typing import List, Optional
from src.memory.memory_store import AutomatonMemoryStore
from src.memory.memory_writer import MemoryWriter
from src.memory.memory_retriever import MemoryRetriever
from src.memory.search import MemorySearch
from src.memory.schemas import MemoryType, MemoryRecord, MemoryQueryResult

class AutomatonMemory:
    """
    Facade principal del sistema de memoria Automaton.
    """
    def __init__(self, db_path: str = "src/memory/automaton_memory.db"):
        self.store = AutomatonMemoryStore(db_path)
        self.writer = MemoryWriter(self.store)
        self.retriever = MemoryRetriever(self.store)
        self.searcher = MemorySearch(self.store)

    def write(self, memory_type: MemoryType, family: str, batch_id: str, claim_text: str, 
              source_path: str, source_commit: str, tags: List[str] = None, confidence: float = 1.0) -> str:
        return self.writer.write(memory_type, family, batch_id, claim_text, source_path, source_commit, tags, confidence)

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        return self.retriever.get(memory_id)

    def search(self, query: str, family: Optional[str] = None, batch_id: Optional[str] = None, top_k: int = 10) -> List[MemoryQueryResult]:
        return self.searcher.search(query, family, batch_id, top_k)
        
    def link(self, source_id: str, target_id: str, link_type: str = "DERIVED_FROM"):
        self.writer.link(source_id, target_id, link_type)
        
    def close(self):
        self.store.close()
