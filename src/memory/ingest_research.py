import csv
import json
import logging
from pathlib import Path
from src.memory.schemas import MemoryType
from src.memory.memory_router import AutomatonMemory
from src.memory.consolidate import MemoryConsolidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_research_log(memory: AutomatonMemory, csv_path: str):
    logger.info(f"Ingesting {csv_path}...")
    if not Path(csv_path).exists():
        logger.warning(f"{csv_path} does not exist.")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch_id = row.get("batch_id", "UNKNOWN")
            family = row.get("family", "UNKNOWN")
            hypothesis = row.get("hypothesis", "")
            outcome = row.get("outcome", "")
            rejection_reason = row.get("rejection_reason", "")
            
            # 1. Raw Memory (Exact line)
            raw_text = json.dumps(row)
            memory.write(
                memory_type=MemoryType.RAW,
                family=family,
                batch_id=batch_id,
                claim_text=raw_text,
                source_path=csv_path,
                source_commit="INITIAL_INGESTION",
                tags=["RAW_LOG"]
            )
            
            # 2. Atomic Memory (Extracted Facts)
            if hypothesis:
                memory.write(
                    memory_type=MemoryType.ATOMIC,
                    family=family,
                    batch_id=batch_id,
                    claim_text=f"Hypothesis: {hypothesis}",
                    source_path=csv_path,
                    source_commit="INITIAL_INGESTION",
                    tags=["HYPOTHESIS", family]
                )
                
            if outcome == "REJECTED" and rejection_reason:
                memory.write(
                    memory_type=MemoryType.ATOMIC,
                    family=family,
                    batch_id=batch_id,
                    claim_text=f"Rejection Reason: {rejection_reason}",
                    source_path=csv_path,
                    source_commit="INITIAL_INGESTION",
                    tags=["REJECTED", "AUTOPSY", family]
                )
            elif outcome == "ACCEPTED":
                memory.write(
                    memory_type=MemoryType.ATOMIC,
                    family=family,
                    batch_id=batch_id,
                    claim_text=f"Survivors promoted to PAPER_ACTIVE.",
                    source_path=csv_path,
                    source_commit="INITIAL_INGESTION",
                    tags=["SURVIVOR", family]
                )

def ingest_registry(memory: AutomatonMemory, json_path: str):
    logger.info(f"Ingesting {json_path}...")
    if not Path(json_path).exists():
        logger.warning(f"{json_path} does not exist.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
        for cand in data.get("active_paper_strategies", []):
            family = cand.get("family", "UNKNOWN")
            cand_id = cand.get("id", "UNKNOWN")
            
            # Atomic Memory
            memory.write(
                memory_type=MemoryType.ATOMIC,
                family=family,
                batch_id=cand_id,
                claim_text=f"Strategy {cand_id} is PAPER_ACTIVE.",
                source_path=json_path,
                source_commit="INITIAL_INGESTION",
                tags=["PAPER_ACTIVE", "SURVIVOR", family]
            )

if __name__ == "__main__":
    mem = AutomatonMemory()
    ingest_research_log(mem, "src/factory/research_log.csv")
    ingest_registry(mem, "src/factory/registry.json")
    
    logger.info("Consolidating memory...")
    cons = MemoryConsolidator(mem)
    cons.consolidate()
    
    mem.close()
    logger.info("Ingestion complete.")
