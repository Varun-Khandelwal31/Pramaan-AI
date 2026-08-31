import os
import sqlite3
from datetime import datetime, timezone, timedelta

def generate_file_content(record_type: str, case_no: str, patient_alias: str, details: str) -> bytes:
    """Generates standardized, byte-exact medico-legal report content."""
    lines = [
        f"MEDICO-LEGAL RECORD: {record_type.upper()}",
        f"Case Number: {case_no}",
        f"Patient Identifier / Alias: {patient_alias}",
        f"Hospital Node: Govt. District Hospital, Civil Lines",
        "-" * 50,
        "CLINICAL FINDINGS & OBSERVATIONS:",
        details.strip(),
        "-" * 50,
        "STATUTORY NOTICE: Sealed at creation under Section 63 BSA 2023.",
        "Tamper-evident raw byte digest computed upon entry."
    ]
    return "\n".join(lines).encode('utf-8')

def seed_database(force=False):
    try:
        from backend.database import db
        from backend.core import chain, blockchain
        from backend.services import kyc
    except Exception:
        import db
        import chain
        import blockchain
        import kyc

    db.init_db()
    db._is_seeding = True

    try:
        conn = db._raw_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM cases")
            row = cursor.fetchone()
            if row and row["count"] > 0 and not force:
                return

            cursor.execute("DELETE FROM records")
            cursor.execute("DELETE FROM cases")
            cursor.execute("DELETE FROM audit_log")
            cursor.execute("DELETE FROM anchors")
            try:
                cursor.execute("DELETE FROM sqlite_sequence")
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()

        now = datetime.now(timezone.utc)

        # 1. Case 1: Road Accident (Complete 4-record chain)
        c1_time = now - timedelta(days=2, hours=4)
        c1_id = db.create_case(
            case_no="MLC-2026-0042",
            case_type="Road Accident",
            patient_alias="Ramesh Kumar, 34M",
            hospital="Govt. District Hospital, Civil Lines",
            incident_date=(c1_time - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
            injury_summary="Blunt trauma head, compound fracture right tibia-fibula, extensive abrasions. RTA hit-and-run at Ring Road Junction.",
            duty_doctor="Dr. A. Sharma, CMO",
            doctor_nmc_reg="NMC-2018-84920",
            entry_duration_seconds=42,
            created_at=c1_time.isoformat()
        )

        # R1: MLC Entry
        r1_time = (c1_time + timedelta(minutes=15)).isoformat()
        r1_blob = generate_file_content("MLC Entry", "MLC-2026-0042", "Ramesh Kumar, 34M", "Emergency intake: GCS 13/15. Pulse 112, BP 100/68. Active bleeding right lower limb and scalp.")
        r1_chash = chain.calculate_content_hash(r1_blob)
        r1_rhash = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, r1_chash, "Dr. A. Sharma, CMO", r1_time)
        r1_kyc = kyc.get_doctor_kyc("Dr. A. Sharma, CMO")
        r1_tx = blockchain.generate_tx_hash(r1_rhash, 1)
        r1_block = blockchain.get_onchain_block_number(1)
        r1_id = db.insert_record(c1_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", r1_blob, "mlc_entry_0042.txt", r1_chash, chain.GENESIS_PREV_HASH, r1_rhash, r1_time, None, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], r1_tx, r1_block)

        # R2: Injury Certificate (Contains "12 Mar" for tamper demo)
        r2_time = (c1_time + timedelta(hours=1, minutes=10)).isoformat()
        r2_blob = generate_file_content("Injury Certificate", "MLC-2026-0042", "Ramesh Kumar, 34M", "CERTIFICATE OF INJURIES: Date of Incident: 12 Mar 2026.\n1. Lacerated wound 6x2cm bone deep right parietal scalp.\n2. Compound fracture right tibia-fibula with puncture wound 3x2cm.\nNature: Grievous, caused by blunt vehicular impact.")
        r2_chash = chain.calculate_content_hash(r2_blob)
        r2_rhash = chain.calculate_record_hash(r1_rhash, r2_chash, "Dr. A. Sharma, CMO", r2_time)
        r2_tx = blockchain.generate_tx_hash(r2_rhash, 2)
        r2_block = blockchain.get_onchain_block_number(2)
        r2_id = db.insert_record(c1_id, "Injury Certificate", "Dr. A. Sharma, CMO", "Hospital", r2_blob, "injury_cert_0042.txt", r2_chash, r1_rhash, r2_rhash, r2_time, None, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], r2_tx, r2_block)

        # R3: X-Ray Report
        r3_time = (c1_time + timedelta(hours=3, minutes=30)).isoformat()
        r3_blob = generate_file_content("X-Ray Report", "MLC-2026-0042", "Ramesh Kumar, 34M", "RADIOLOGICAL REPORT: Complete comminuted fracture distal 1/3rd right tibia and fibula with significant displacement. Skull vault: No radio-opaque fracture line visualized.")
        r3_chash = chain.calculate_content_hash(r3_blob)
        r3_rhash = chain.calculate_record_hash(r2_rhash, r3_chash, "Dr. V. Rao, Radiologist", r3_time)
        r3_kyc = kyc.get_doctor_kyc("Dr. V. Rao, Radiologist")
        r3_tx = blockchain.generate_tx_hash(r3_rhash, 3)
        r3_block = blockchain.get_onchain_block_number(3)
        r3_id = db.insert_record(c1_id, "X-Ray Report", "Dr. V. Rao, Radiologist", "Hospital", r3_blob, "xray_report_0042.txt", r3_chash, r2_rhash, r3_rhash, r3_time, None, None, r3_kyc["nmc_reg"], r3_kyc["kyc_hash"], r3_tx, r3_block)

        # R4: Final Opinion
        r4_time = (c1_time + timedelta(hours=6)).isoformat()
        r4_blob = generate_file_content("Final Opinion", "MLC-2026-0042", "Ramesh Kumar, 34M", "FINAL OPINION AS TO CAUSE OF INJURIES: The injuries described in certificates 1 to 3 are consistent with high-energy Road Traffic Accident. Injury #2 is grievous in nature dangerous to life without surgical intervention.")
        r4_chash = chain.calculate_content_hash(r4_blob)
        r4_rhash = chain.calculate_record_hash(r3_rhash, r4_chash, "Dr. A. Sharma, CMO", r4_time)
        r4_tx = blockchain.generate_tx_hash(r4_rhash, 4)
        r4_block = blockchain.get_onchain_block_number(4)
        r4_id = db.insert_record(c1_id, "Final Opinion", "Dr. A. Sharma, CMO", "Hospital", r4_blob, "final_opinion_0042.txt", r4_chash, r3_rhash, r4_rhash, r4_time, None, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], r4_tx, r4_block)

        # 2. Case 2: Assault (2 records sealed, Forensic pending)
        c2_time = now - timedelta(days=5, hours=12)
        c2_id = db.create_case("MLC-2026-0039", "Assault", "Suresh Patel, 28M", "Govt. District Hospital, Civil Lines", (c2_time - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), "Multiple incised defense wounds on bilateral forearms, contusion on thorax following street altercation.", "Dr. S. K. Verma, CMO", "NMC-2012-45109", 38, c2_time.isoformat())
        c2_blob1 = generate_file_content("MLC Entry", "MLC-2026-0039", "Suresh Patel, 28M", "Emergency triage: Conscious, oriented. Incised wounds 4cm and 3cm on left forearm, active capillary bleed.")
        c2_chash1 = chain.calculate_content_hash(c2_blob1)
        c2_rec1 = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c2_chash1, "Dr. S. K. Verma, CMO", c2_time.isoformat())
        c2_kyc = kyc.get_doctor_kyc("Dr. S. K. Verma, CMO")
        db.insert_record(c2_id, "MLC Entry", "Dr. S. K. Verma, CMO", "Hospital", c2_blob1, "mlc_0039.txt", c2_chash1, chain.GENESIS_PREV_HASH, c2_rec1, c2_time.isoformat(), None, None, c2_kyc["nmc_reg"], c2_kyc["kyc_hash"], blockchain.generate_tx_hash(c2_rec1, 5), blockchain.get_onchain_block_number(5))

        c2_blob2 = generate_file_content("Injury Certificate", "MLC-2026-0039", "Suresh Patel, 28M", "INJURY CERTIFICATE: Sharp cutting weapon injuries over dorsal aspect left forearm. Simple in nature, age of injury within 6 hours.")
        c2_chash2 = chain.calculate_content_hash(c2_blob2)
        c2_rec2 = chain.calculate_record_hash(c2_rec1, c2_chash2, "Dr. S. K. Verma, CMO", (c2_time + timedelta(hours=2)).isoformat())
        db.insert_record(c2_id, "Injury Certificate", "Dr. S. K. Verma, CMO", "Hospital", c2_blob2, "injury_0039.txt", c2_chash2, c2_rec1, c2_rec2, (c2_time + timedelta(hours=2)).isoformat(), None, None, c2_kyc["nmc_reg"], c2_kyc["kyc_hash"], blockchain.generate_tx_hash(c2_rec2, 6), blockchain.get_onchain_block_number(6))

        # 3. Case 3: POCSO Case (47 DAYS OVERDUE Justice Clock highlight)
        c3_time = now - timedelta(days=47, hours=6)
        c3_id = db.create_case("MLC-2026-0038", "POCSO Case", "Minor Subject (Confidential)", "Govt. District Hospital, Civil Lines", (c3_time - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"), "Statutory medical examination under POCSO Act §33 / DPDP 2023. Biological swabs sealed.", "Dr. N. Joshi, Gynaecologist", "NMC-2016-72819", 58, c3_time.isoformat())
        c3_blob1 = generate_file_content("MLC Entry", "MLC-2026-0038", "Protected Identity", "POCSO Case intake registered in presence of female medical officer and legal aid counsel. Specimen kit #FSL-9081 sealed.")
        c3_chash1 = chain.calculate_content_hash(c3_blob1)
        c3_rec1 = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c3_chash1, "Dr. N. Joshi, Gynaecologist", c3_time.isoformat())
        c3_kyc = kyc.get_doctor_kyc("Dr. N. Joshi, Gynaecologist")
        db.insert_record(c3_id, "MLC Entry", "Dr. N. Joshi, Gynaecologist", "Hospital", c3_blob1, "mlc_0038.txt", c3_chash1, chain.GENESIS_PREV_HASH, c3_rec1, c3_time.isoformat(), None, None, c3_kyc["nmc_reg"], c3_kyc["kyc_hash"], blockchain.generate_tx_hash(c3_rec1, 7), blockchain.get_onchain_block_number(7))

        c3_blob2 = generate_file_content("Medical Examination", "MLC-2026-0038", "Protected Identity", "DETAILED CLINICAL FORENSIC EXAMINATION: Completed under Section 27 POCSO Act. Physical trauma documented, psychological trauma score high.")
        c3_chash2 = chain.calculate_content_hash(c3_blob2)
        c3_rec2 = chain.calculate_record_hash(c3_rec1, c3_chash2, "Dr. N. Joshi, Gynaecologist", (c3_time + timedelta(hours=3)).isoformat())
        db.insert_record(c3_id, "Medical Examination", "Dr. N. Joshi, Gynaecologist", "Hospital", c3_blob2, "med_exam_0038.txt", c3_chash2, c3_rec1, c3_rec2, (c3_time + timedelta(hours=3)).isoformat(), None, None, c3_kyc["nmc_reg"], c3_kyc["kyc_hash"], blockchain.generate_tx_hash(c3_rec2, 8), blockchain.get_onchain_block_number(8))

        # 4. Other 4 Cases (Diverse clinical intakes)
        c4_time = now - timedelta(days=1, hours=8)
        c4_id = db.create_case("MLC-2026-0044", "Road Accident", "Vikram Rathore, 42M", "Govt. District Hospital, Civil Lines", (c4_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "Pedestrian struck by heavy vehicle. Pelvic instability, hypovolemic shock.", "Dr. S. K. Verma, CMO", "NMC-2012-45109", 45, c4_time.isoformat())
        c4_blob = b"MLC EMERGENCY INTAKE: Vikram Rathore, 42M. Pelvic compression pain, vitals unstable. Fast ultrasound positive for free peritoneal fluid."
        c4_chash = chain.calculate_content_hash(c4_blob)
        c4_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c4_chash, "Dr. S. K. Verma, CMO", c4_time.isoformat())
        db.insert_record(c4_id, "MLC Entry", "Dr. S. K. Verma, CMO", "Hospital", c4_blob, "mlc_0044.txt", c4_chash, chain.GENESIS_PREV_HASH, c4_rec, c4_time.isoformat(), None, None, c2_kyc["nmc_reg"], c2_kyc["kyc_hash"], blockchain.generate_tx_hash(c4_rec, 9), blockchain.get_onchain_block_number(9))

        c5_time = now - timedelta(days=3, hours=2)
        c5_id = db.create_case("MLC-2026-0043", "Assault", "Anita Devi, 31F", "Govt. District Hospital, Civil Lines", (c5_time - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "Blunt object trauma to lumbar region and facial ecchymosis.", "Dr. A. Sharma, CMO", "NMC-2018-84920", 35, c5_time.isoformat())
        c5_blob = b"MLC INTAKE: Anita Devi, 31F. Soft tissue contusions over lower back and periorbital hematoma left eye."
        c5_chash = chain.calculate_content_hash(c5_blob)
        c5_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c5_chash, "Dr. A. Sharma, CMO", c5_time.isoformat())
        db.insert_record(c5_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", c5_blob, "mlc_0043.txt", c5_chash, chain.GENESIS_PREV_HASH, c5_rec, c5_time.isoformat(), None, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], blockchain.generate_tx_hash(c5_rec, 10), blockchain.get_onchain_block_number(10))

        c6_time = now - timedelta(days=7)
        c6_id = db.create_case("MLC-2026-0040", "Road Accident", "Mohd. Arshad, 22M", "Govt. District Hospital, Civil Lines", (c6_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "Two-wheeler skid. Abrasions right shoulder, knee laceration 3cm.", "Dr. M. Chawla, Resident", "NMC-2022-99301", 30, c6_time.isoformat())
        c6_blob = b"MLC INTAKE: Mohd. Arshad, 22M. Abrasions dressed, simple suturing over right patellar laceration."
        c6_chash = chain.calculate_content_hash(c6_blob)
        c6_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c6_chash, "Dr. M. Chawla, Resident", c6_time.isoformat())
        c6_kyc = kyc.get_doctor_kyc("Dr. M. Chawla, Resident")
        db.insert_record(c6_id, "MLC Entry", "Dr. M. Chawla, Resident", "Hospital", c6_blob, "mlc_0040.txt", c6_chash, chain.GENESIS_PREV_HASH, c6_rec, c6_time.isoformat(), None, None, c6_kyc["nmc_reg"], c6_kyc["kyc_hash"], blockchain.generate_tx_hash(c6_rec, 11), blockchain.get_onchain_block_number(11))

        c7_time = now - timedelta(hours=18)
        c7_id = db.create_case("MLC-2026-0041", "Assault", "Deepak Rawat, 39M", "Govt. District Hospital, Civil Lines", (c7_time - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "Fracture nasal bone with epistaxis following street brawl.", "Dr. A. Sharma, CMO", "NMC-2018-84920", 44, c7_time.isoformat())
        c7_blob = b"MLC INTAKE: Deepak Rawat, 39M. Epistaxis arrested, nasal bridge swelling and deformity."
        c7_chash = chain.calculate_content_hash(c7_blob)
        c7_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c7_chash, "Dr. A. Sharma, CMO", c7_time.isoformat())
        db.insert_record(c7_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", c7_blob, "mlc_0041.txt", c7_chash, chain.GENESIS_PREV_HASH, c7_rec, c7_time.isoformat(), None, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], blockchain.generate_tx_hash(c7_rec, 12), blockchain.get_onchain_block_number(12))

        # 5. Audit Log Seed Events
        db.log_audit_event(c1_id, r1_id, "Record Created & Sealed", "Dr. A. Sharma, CMO", "Hospital", r1_time)
        db.log_audit_event(c1_id, r2_id, "Record Created & Sealed", "Dr. A. Sharma, CMO", "Hospital", r2_time)
        db.log_audit_event(c1_id, r2_id, "Integrity Receipt Inspected via QR", "SI R. Meena (PS Civil Lines)", "Police", (c1_time + timedelta(hours=2)).isoformat())
        db.log_audit_event(c1_id, r3_id, "Record Created & Sealed", "Dr. V. Rao, Radiologist", "Hospital", r3_time)
        db.log_audit_event(c1_id, r4_id, "Record Created & Sealed", "Dr. A. Sharma, CMO", "Hospital", r4_time)
        db.log_audit_event(c1_id, None, "Section 63 BSA Certificate Issued", "Dr. A. Sharma, CMO", "Hospital", (c1_time + timedelta(hours=7)).isoformat())

        # 6. Anchors Registry (Past 5 days cumulative Merkle roots)
        for day_offset in range(5, 0, -1):
            anchor_date = now - timedelta(days=day_offset)
            snap_hash = chain.calculate_record_hash("DAILY_ANCHOR_PREV", f"DAILY_ROOT_SNAP_DAY_{day_offset}", "REGISTRY_PUBLIC_NODE", anchor_date.isoformat())
            db.create_anchor(snap_hash, 10 + day_offset * 3, anchor_date.isoformat())

        print("Successfully seeded 7 realistic cases, records, audit events, and 5 daily anchors with Blockchain & DigiLocker KYC.")
    finally:
        db._is_seeding = False

if __name__ == "__main__":
    seed_database(force=True)
