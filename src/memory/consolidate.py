from src.memory.memory_router import AutomatonMemory
from src.memory.schemas import MemoryType

class MemoryConsolidator:
    def __init__(self, memory: AutomatonMemory):
        self.memory = memory

    def consolidate(self):
        """
        Analiza las memorias RAW/ATOMIC y las promueve a SCENE o CORE.
        Esto es un placeholder para lógica más compleja de clustering de agentes.
        Por ahora, podemos promover familias confirmadas a CORE.
        """
        # Example logic: Promote REJECTED families to CORE memory automatically
        atomics = self.memory.retriever.store.get_all_records("atomic_memory")
        for rec in atomics:
            if "REJECTED" in rec.tags:
                self.memory.write(
                    memory_type=MemoryType.CORE,
                    family=rec.family,
                    batch_id=rec.batch_id,
                    claim_text=f"Rule: Family {rec.family} is REJECTED. Do not repeat without structural changes.",
                    source_path=rec.source_path,
                    source_commit=rec.source_commit,
                    tags=["RULE", "REJECTED_CONSTRAINT", rec.family],
                    confidence=1.0
                )
