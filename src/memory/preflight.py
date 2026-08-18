from typing import Dict, Any, List
from src.memory.memory_router import AutomatonMemory
from src.memory.schemas import MemoryType

class MemoryPreflight:
    def __init__(self, memory: AutomatonMemory):
        self.memory = memory

    def check_hypothesis(self, family: str, hypothesis_text: str) -> Dict[str, Any]:
        """
        Consulta la memoria antes de ejecutar un batch para prevenir duplicación
        y evaluar conocimiento estructural sobre la familia de estrategias.
        """
        results = {
            "RELATED_TESTS": [],
            "REJECTED_CONSTRAINTS": [],
            "SURVIVING_KNOWLEDGE": [],
            "DUPLICATE_RISK": False
        }
        
        # 1. Search for similar hypotheses
        search_results = self.memory.search(query=hypothesis_text, top_k=5)
        for res in search_results:
            if res.record.family == family and res.score > 0.8:  # High similarity threshold
                results["DUPLICATE_RISK"] = True
            
            summary = f"[{res.record.family}] {res.record.claim_text} (Score: {res.score:.2f})"
            results["RELATED_TESTS"].append(summary)
            
        # 2. Check Core Rules and Rejections for this family
        core_records = self.memory.retriever.store.get_all_records("core_memory")
        for rec in core_records:
            if rec.family == family or rec.family in hypothesis_text:
                if "REJECTED_CONSTRAINT" in rec.tags:
                    results["REJECTED_CONSTRAINTS"].append(rec.claim_text)
                elif "RULE" in rec.tags:
                    results["SURVIVING_KNOWLEDGE"].append(rec.claim_text)
                    
        return results

    def is_family_rejected(self, family: str) -> bool:
        """
        Hard check si la familia entera está REJECTED en la memoria CORE.
        """
        core_records = self.memory.retriever.store.get_all_records("core_memory")
        for rec in core_records:
            if (rec.family == family or family in rec.family or rec.family in family) and "REJECTED_CONSTRAINT" in rec.tags:
                return True
        return False

def enforce_preflight(family: str, hypothesis: str = "") -> bool:
    """
    Función obligatoria para todos los loops.
    Retorna True si puede continuar, False si debe detenerse (MEMORY_BLOCKED).
    """
    memory = AutomatonMemory()
    preflight = MemoryPreflight(memory)
    
    if preflight.is_family_rejected(family):
        print(f"🛑 MEMORY_BLOCKED: La familia {family} está REJECTED en la memoria CORE.")
        memory.close()
        return False
        
    if hypothesis:
        pf_res = preflight.check_hypothesis(family, hypothesis)
        if pf_res["DUPLICATE_RISK"]:
            print(f"🛑 MEMORY_BLOCKED: Alto riesgo de duplicación detectado para la hipótesis: {hypothesis}")
            memory.close()
            return False
            
    memory.close()
    return True
