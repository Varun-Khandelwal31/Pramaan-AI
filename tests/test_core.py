import unittest
from backend.core.chain import (
    calculate_content_hash,
    calculate_record_hash,
    verify_record_integrity,
    verify_case_chain,
    compute_merkle_root,
    generate_merkle_proof,
    verify_merkle_proof
)
from backend.database import db, seed

class TestPramaanCore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Force re-seed database before tests
        seed.seed_database(force=True)

    def test_seed_cases_count(self):
        cases = db.get_all_cases()
        self.assertGreaterEqual(len(cases), 7)
        case_nos = [c["case_no"] for c in cases]
        self.assertIn("MLC-2026-0042", case_nos)
        self.assertIn("MLC-2026-0038", case_nos)

    def test_clean_chain_verification(self):
        case = db.get_case_by_no("MLC-2026-0042")
        self.assertIsNotNone(case)
        records = db.get_case_records(case["id"])
        self.assertEqual(len(records), 4)

        result = verify_case_chain(records)
        self.assertTrue(result["is_intact"])
        self.assertIsNone(result["broken_record_id"])
        self.assertEqual(result["total_records"], 4)

    def test_tamper_and_detection(self):
        case = db.get_case_by_no("MLC-2026-0042")
        records = db.get_case_records(case["id"])
        r2 = records[1]

        # 1. Corrupt byte in Record #2
        corrupted_blob = r2["file_blob"].replace(b"12 Mar", b"10 Mar")
        db.tamper_record(r2["id"], corrupted_blob)

        # 2. Verify detection
        tampered_records = db.get_case_records(case["id"])
        res = verify_case_chain(tampered_records)
        self.assertFalse(res["is_intact"])
        self.assertEqual(res["broken_record_id"], r2["id"])
        self.assertEqual(res["broken_index"], 2)

        # 3. Untamper and verify restoration
        db.untamper_record(r2["id"])
        restored_records = db.get_case_records(case["id"])
        res_restored = verify_case_chain(restored_records)
        self.assertTrue(res_restored["is_intact"])

    def test_merkle_proof_verification(self):
        case = db.get_case_by_no("MLC-2026-0042")
        records = db.get_case_records(case["id"])
        hashes = [r["record_hash"] for r in records]
        
        target = hashes[0]
        proof_data = generate_merkle_proof(hashes, target)
        self.assertTrue(proof_data["is_valid"])
        self.assertEqual(proof_data["target_hash"], target)

        is_valid_math = verify_merkle_proof(target, proof_data["proof_steps"], proof_data["merkle_root"])
        self.assertTrue(is_valid_math)

    def test_justice_clock_calculation(self):
        case_overdue = db.get_case_by_no("MLC-2026-0038")
        self.assertIsNotNone(case_overdue)
        records = db.get_case_records(case_overdue["id"])
        status = db.compute_case_justice_status(case_overdue, records)
        self.assertTrue(status["is_overdue"])
        self.assertIn("Forensic Report", status["pending_docs"])

if __name__ == "__main__":
    unittest.main()
