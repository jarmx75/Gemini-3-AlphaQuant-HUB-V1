import sqlite3
from pathlib import Path
import pprint

def audit_memory(db_path: str = "src/memory/automaton_memory.db"):
    print("=" * 60)
    print("🧠 AUTOMATON MEMORY AUDIT REPORT")
    print("=" * 60)
    
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Counts per table
    tables = ['raw_memory', 'atomic_memory', 'scene_memory', 'core_memory', 'memory_links']
    print("\n--- RECORD COUNTS ---")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table.ljust(15)}: {count} records")
        
    # 2. Known Families
    print("\n--- KNOWN FAMILIES (ACROSS ALL MEMORIES) ---")
    cursor.execute("""
        SELECT family, COUNT(*) 
        FROM (
            SELECT family FROM raw_memory
            UNION ALL SELECT family FROM atomic_memory
            UNION ALL SELECT family FROM scene_memory
            UNION ALL SELECT family FROM core_memory
        )
        GROUP BY family
        ORDER BY COUNT(*) DESC
    """)
    for row in cursor.fetchall():
        print(f"- {row[0]}: {row[1]} references")
        
    # 3. Known Batches
    print("\n--- KNOWN BATCHES ---")
    cursor.execute("SELECT batch_id, COUNT(*) FROM raw_memory GROUP BY batch_id ORDER BY batch_id")
    for row in cursor.fetchall():
        print(f"- {row[0]}: {row[1]} raw logs")
        
    # 4. Data Quality Checks
    print("\n--- DATA QUALITY ---")
    
    # Check for missing sources
    cursor.execute("""
        SELECT COUNT(*) FROM atomic_memory 
        WHERE source_path IS NULL OR source_path = ''
    """)
    orphan_atomic = cursor.fetchone()[0]
    print(f"Atomic memories without source path: {orphan_atomic}")
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    audit_memory()
