import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from src.memory.schemas import MemoryRecord, MemoryType, MemoryQueryResult

logger = logging.getLogger(__name__)

class AutomatonMemoryStore:
    def __init__(self, db_path: str = "src/memory/automaton_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._initialize_tables()

    def _initialize_tables(self):
        cursor = self.conn.cursor()
        
        # Base table definition
        base_schema = """
            memory_id TEXT PRIMARY KEY,
            memory_type TEXT,
            family TEXT,
            batch_id TEXT,
            claim_text TEXT,
            source_path TEXT,
            source_commit TEXT,
            confidence REAL,
            created_at TEXT,
            updated_at TEXT,
            tags TEXT,
            UNIQUE(batch_id, family, claim_text)
        """
        
        tables = ['raw_memory', 'atomic_memory', 'scene_memory', 'core_memory']
        for table in tables:
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({base_schema})")
            
        # Memory links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                source_id TEXT,
                target_id TEXT,
                link_type TEXT,
                PRIMARY KEY (source_id, target_id, link_type)
            )
        """)

        # FTS5 table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                memory_id UNINDEXED,
                claim_text,
                tags
            )
        """)
        
        self.conn.commit()

    def _get_table(self, memory_type: MemoryType) -> str:
        return f"{memory_type.value.lower()}_memory"

    def upsert_memory(self, record: MemoryRecord):
        cursor = self.conn.cursor()
        table = self._get_table(record.memory_type)
        data = record.to_dict()
        
        # Check if exists by unique constraint
        cursor.execute(f"""
            SELECT memory_id FROM {table} 
            WHERE batch_id = ? AND family = ? AND claim_text = ?
        """, (record.batch_id, record.family, record.claim_text))
        
        existing = cursor.fetchone()
        if existing:
            # Update
            cursor.execute(f"""
                UPDATE {table} SET 
                    source_path = ?, source_commit = ?, confidence = ?, 
                    updated_at = ?, tags = ?
                WHERE memory_id = ?
            """, (record.source_path, record.source_commit, record.confidence, 
                  record.updated_at, data['tags'], existing['memory_id']))
            record.memory_id = existing['memory_id'] # update the passed object with correct ID
        else:
            # Insert
            cursor.execute(f"""
                INSERT INTO {table} 
                (memory_id, memory_type, family, batch_id, claim_text, source_path, source_commit, confidence, created_at, updated_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.memory_id, record.memory_type.value, record.family, record.batch_id, record.claim_text, 
                  record.source_path, record.source_commit, record.confidence, record.created_at, record.updated_at, data['tags']))
            
        # Update FTS
        cursor.execute("DELETE FROM memory_fts WHERE memory_id = ?", (record.memory_id,))
        cursor.execute("""
            INSERT INTO memory_fts (memory_id, claim_text, tags) VALUES (?, ?, ?)
        """, (record.memory_id, record.claim_text, data['tags']))
        
        self.conn.commit()

    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        cursor = self.conn.cursor()
        tables = ['raw_memory', 'atomic_memory', 'scene_memory', 'core_memory']
        for table in tables:
            cursor.execute(f"SELECT * FROM {table} WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def search_fts(self, query: str, top_k: int = 10) -> List[MemoryQueryResult]:
        cursor = self.conn.cursor()
        # Simple BM25 ranking provided by SQLite FTS5
        cursor.execute("""
            SELECT memory_id, bm25(memory_fts) as score 
            FROM memory_fts 
            WHERE memory_fts MATCH ? 
            ORDER BY score ASC 
            LIMIT ?
        """, (query, top_k * 2)) # Fetch more, then rank manually in python if needed
        
        results = []
        for row in cursor.fetchall():
            mem = self.get_memory(row['memory_id'])
            if mem:
                # SQLite bm25 returns negative values, more negative is better.
                # Let's invert it for our score so higher is better.
                score = -row['score'] 
                results.append(MemoryQueryResult(record=mem, score=score))
                
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        d = dict(row)
        d['memory_type'] = MemoryType(d['memory_type'])
        d['tags'] = json.loads(d['tags']) if d['tags'] else []
        return MemoryRecord(**d)
        
    def link_memories(self, source_id: str, target_id: str, link_type: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO memory_links (source_id, target_id, link_type)
            VALUES (?, ?, ?)
        """, (source_id, target_id, link_type))
        self.conn.commit()
        
    def get_all_records(self, table: str) -> List[MemoryRecord]:
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
