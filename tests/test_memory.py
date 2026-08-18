import unittest
import os
from src.memory.memory_router import AutomatonMemory
from src.memory.schemas import MemoryType
from src.memory.preflight import MemoryPreflight

class TestAutomatonMemory(unittest.TestCase):
    def setUp(self):
        # Use an in-memory db or a temporary file
        self.db_path = "src/memory/test_memory.db"
        self.memory = AutomatonMemory(self.db_path)
        
    def tearDown(self):
        self.memory.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_write_and_read(self):
        mem_id = self.memory.write(
            memory_type=MemoryType.ATOMIC,
            family="TEST_FAMILY",
            batch_id="Batch_Test",
            claim_text="This is a test claim.",
            source_path="test.csv",
            source_commit="commit123",
            tags=["TEST"]
        )
        
        record = self.memory.get(mem_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.claim_text, "This is a test claim.")
        self.assertEqual(record.family, "TEST_FAMILY")

    def test_search(self):
        self.memory.write(
            memory_type=MemoryType.ATOMIC,
            family="TEST_FAMILY",
            batch_id="Batch_Test",
            claim_text="The funding rate strategy failed due to fees.",
            source_path="test.csv",
            source_commit="commit123",
            tags=["TEST"]
        )
        
        results = self.memory.search("funding rate fees")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].record.family, "TEST_FAMILY")
        
    def test_deduplication(self):
        id1 = self.memory.write(
            memory_type=MemoryType.ATOMIC,
            family="DEDUP_FAMILY",
            batch_id="Batch_1",
            claim_text="Same claim",
            source_path="test.csv",
            source_commit="c1",
        )
        
        id2 = self.memory.write(
            memory_type=MemoryType.ATOMIC,
            family="DEDUP_FAMILY",
            batch_id="Batch_1",
            claim_text="Same claim",
            source_path="test.csv",
            source_commit="c2", # Updated commit
        )
        
        self.assertEqual(id1, id2) # IDs should match because it updated the existing record
        rec = self.memory.get(id1)
        self.assertEqual(rec.source_commit, "c2")
        
    def test_preflight_rejected_family(self):
        self.memory.write(
            memory_type=MemoryType.CORE,
            family="REJECTED_FAMILY",
            batch_id="Batch_1",
            claim_text="Rule: Family REJECTED_FAMILY is REJECTED.",
            source_path="test.csv",
            source_commit="c1",
            tags=["RULE", "REJECTED_CONSTRAINT"]
        )
        
        preflight = MemoryPreflight(self.memory)
        self.assertTrue(preflight.is_family_rejected("REJECTED_FAMILY"))
        self.assertFalse(preflight.is_family_rejected("OTHER_FAMILY"))

if __name__ == '__main__':
    unittest.main()
