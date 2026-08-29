import unittest
import db
import seed
from chain import verify_case_chain, verify_record_integrity, calculate_content_hash, calculate_record_hash

class TestPramaanCore(unittest.TestCase):
    def setUp(self):
        seed.seed_database(force=True)

    def test_seed_cases_count(self):
        cases = db.get_all_cases()
        self.assertEqual(len(cases), 7)
        case_nos = [c["case_no"] for c in cases]
        self.assertIn("MLC-2026-0042", case_nos)
        self.assertIn("MLC-2026-0038", case_nos)

    def test_clean_chain_verification(self):
        cases = db.get_all_cases()
        for case in cases:
            records = db.get_case_records(case["id"])
            res = verify_case_chain(records)
            self.assertTrue(res["is_intact"], f"Case {case['case_no']} should be intact initially")
            self.assertIsNone(res["broken_record_id"])

    def test_tamper_and_detection(self):
        case1 = db.get_case_by_no("MLC-2026-0042")
        records = db.get_case_records(case1["id"])
        # Record 2 is the Injury Certificate
        rec2 = records[1]
        self.assertEqual(rec2["record_type"], "Injury Certificate")

        # Corrupt record 2: change '12 Mar' to '10 Mar'
        original_blob = rec2["file_blob"]
        corrupted_blob = original_blob.replace(b"12 Mar", b"10 Mar")
        self.assertNotEqual(original_blob, corrupted_blob)

        db.tamper_record(rec2["id"], corrupted_blob)

        # Re-verify chain
        updated_records = db.get_case_records(case1["id"])
        res = verify_case_chain(updated_records)
        self.assertFalse(res["is_intact"])
        self.assertEqual(res["broken_record_id"], rec2["id"])
        self.assertEqual(res["broken_index"], 2)

        # Untamper and check recovery
        db.untamper_record(rec2["id"])
        recovered_records = db.get_case_records(case1["id"])
        recovered_res = verify_case_chain(recovered_records)
        self.assertTrue(recovered_res["is_intact"])

    def test_justice_clock(self):
        stats = db.get_aggregate_stats()
        self.assertTrue(stats["has_overdue"])
        self.assertEqual(len(stats["overdue_cases"]), 1)
        overdue_entry = stats["overdue_cases"][0]
        self.assertEqual(overdue_entry["case"]["case_no"], "MLC-2026-0038")
        self.assertEqual(overdue_entry["status"]["overdue_days"], 47)
        self.assertEqual(overdue_entry["status"]["overdue_doc"], "Forensic Report")

    def test_amendment_record_chaining(self):
        case1 = db.get_case_by_no("MLC-2026-0042")
        records_before = db.get_case_records(case1["id"])
        head_record = records_before[-1]

        # Add correction record pointing to Record 2
        amendment_blob = b"CORRECTION: Injury size revised to 4.5cm on specialist re-examination."
        amendment_time = "2026-08-29T14:00:00+00:00"
        amendment_chash = calculate_content_hash(amendment_blob)
        amendment_rhash = calculate_record_hash(head_record["record_hash"], amendment_chash, "Dr. K. Verma", amendment_time)

        db.insert_record(
            case_id=case1["id"],
            record_type="Injury Certificate (Addendum)",
            uploaded_by="Dr. K. Verma",
            uploaded_role="Hospital",
            file_blob=amendment_blob,
            file_name="Injury_Addendum_0042.txt",
            content_hash=amendment_chash,
            prev_hash=head_record["record_hash"],
            record_hash=amendment_rhash,
            created_at=amendment_time,
            corrects_record_id=records_before[1]["id"]
        )

        records_after = db.get_case_records(case1["id"])
        self.assertEqual(len(records_after), len(records_before) + 1)
        res = verify_case_chain(records_after)
        self.assertTrue(res["is_intact"])
        self.assertEqual(records_after[-1]["corrects_record_id"], records_before[1]["id"])

if __name__ == "__main__":
    unittest.main()
