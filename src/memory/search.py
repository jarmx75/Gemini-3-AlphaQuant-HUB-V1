from typing import List, Optional
from src.memory.schemas import MemoryQueryResult
from src.memory.memory_store import AutomatonMemoryStore

class MemorySearch:
    def __init__(self, store: AutomatonMemoryStore):
        self.store = store

    def search(self, query: str, family: Optional[str] = None, batch_id: Optional[str] = None, top_k: int = 10) -> List[MemoryQueryResult]:
        """
        Búsqueda por palabra clave usando FTS5, filtrando por family/batch_id si es necesario,
        y ranqueando por relevancia y confidence.
        """
        # Escape special characters that break FTS5
        escaped_query = query.replace("(", "").replace(")", "").replace(">", "").replace("<", "").replace("=", "").replace("-", " ")
        escaped_query = " ".join([f'"{word}"' for word in escaped_query.split() if word])
        if not escaped_query:
            return []
            
        # Fetch more to allow filtering
        raw_results = self.store.search_fts(escaped_query, top_k=top_k * 5)
        
        filtered = []
        for res in raw_results:
            if family and res.record.family != family:
                continue
            if batch_id and res.record.batch_id != batch_id:
                continue
            
            # Combine FTS score and confidence for final ranking
            res.score = res.score * res.record.confidence
            filtered.append(res)
            
        # Sort again by adjusted score
        filtered.sort(key=lambda x: x.score, reverse=True)
        return filtered[:top_k]
