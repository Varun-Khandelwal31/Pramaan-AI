import os
import sqlite3
from datetime import datetime, timezone, timedelta
import chain
import db
import kyc
import blockchain

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
    db.init_db()

    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM cases")
        row = cursor.fetchone()
        if row["count"] > 0 and not force:
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

    r1_blob = b"MEDICO-LEGAL CERTIFICATE (EMERGENCY INTAKE)\nPatient: Ramesh Kumar, 34/M\nDate: 12 Mar 2026 02:15 AM\nType: RTA Hit & Run\nVitals: BP 90/60, Pulse 118 bpm, GCS 13/15 (E3V4M6)\nInjuries: Deep laceration over right parietal scalp (6x2cm bone deep), deformed right lower limb with active bleeding."
    r1_content_hash = chain.calculate_content_hash(r1_blob)
    r1_prev = chain.GENESIS_PREV_HASH
    r1_time = c1_time.isoformat()
    r1_kyc = kyc.get_doctor_kyc("Dr. A. Sharma, CMO")
    r1_rec_hash = chain.calculate_record_hash(r1_prev, r1_content_hash, "Dr. A. Sharma, CMO", r1_time)
    r1_tx = blockchain.generate_tx_hash(r1_rec_hash, 1)
    
    r1_id = db.insert_record(c1_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", r1_blob, "mlc_entry_0042.txt", r1_content_hash, r1_prev, r1_rec_hash, r1_time, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], r1_tx, blockchain.get_onchain_block_number(1))

    # Record 2: Injury Certificate (TAMPER TARGET)
    r2_blob = b"INJURY CERTIFICATE & WOUND ASSESSMENT\nDate: 12 Mar 2026 03:30 AM\nExamining Officer: Dr. A. Sharma, CMO\nPrimary Findings: Wound #1: Incised-looking lacerated wound 6cm x 2cm x bone-deep over right temporoparietal region. Bleeding controlled.\nWound #2: Compound grade-II fracture right tibia-fibula with puncture wound 2cm x 1cm.\nWound #3: Multiple friction burns and road gravel embedded over right forearm and flank."
    r2_content_hash = chain.calculate_content_hash(r2_blob)
    r2_prev = r1_rec_hash
    r2_time = (c1_time + timedelta(hours=1, minutes=15)).isoformat()
    r2_rec_hash = chain.calculate_record_hash(r2_prev, r2_content_hash, "Dr. A. Sharma, CMO", r2_time)
    r2_tx = blockchain.generate_tx_hash(r2_rec_hash, 2)
    r2_id = db.insert_record(c1_id, "Injury Certificate", "Dr. A. Sharma, CMO", "Hospital", r2_blob, "injury_cert_0042.txt", r2_content_hash, r2_prev, r2_rec_hash, r2_time, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], r2_tx, blockchain.get_onchain_block_number(2))

    # Record 3: X-Ray Report
    r3_blob = b"DEPARTMENT OF RADIODIAGNOSIS - RADIOLOGY REPORT\nDate: 12 Mar 2026 05:00 AM\nRadiologist: Dr. V. Rao, Radiologist\nRegion: Right Tibia-Fibula (AP + Lat) & Skull AP/Lat\nFindings: Complete displaced oblique fracture of mid-shaft of right tibia with comminuted fibular fracture.\nSkull: Linear undisplaced fissure fracture of right parietal bone noted without gross depression."
    r3_content_hash = chain.calculate_content_hash(r3_blob)
    r3_prev = r2_rec_hash
    r3_time = (c1_time + timedelta(hours=2, minutes=45)).isoformat()
    r3_kyc = kyc.get_doctor_kyc("Dr. V. Rao, Radiologist")
    r3_rec_hash = chain.calculate_record_hash(r3_prev, r3_content_hash, "Dr. V. Rao, Radiologist", r3_time)
    r3_tx = blockchain.generate_tx_hash(r3_rec_hash, 3)
    r3_id = db.insert_record(c1_id, "X-Ray Report", "Dr. V. Rao, Radiologist", "Hospital", r3_blob, "xray_report_0042.txt", r3_content_hash, r3_prev, r3_rec_hash, r3_time, None, r3_kyc["nmc_reg"], r3_kyc["kyc_hash"], r3_tx, blockchain.get_onchain_block_number(3))

    # Record 4: Final Medico-Legal Opinion
    r4_blob = b"FINAL MEDICO-LEGAL OPINION & CAUSE OF INJURY\nDate: 12 Mar 2026 09:00 AM\nMedical Board Opinion:\n1. Injury No. 2 (Compound Tib-Fib Fracture) is GRIEVOUS in nature, caused by blunt vehicular impact.\n2. Injury No. 1 (Scalp laceration with fissure fracture) is GRIEVOUS, dangerous to life in the absence of surgical intervention.\nAll injuries are fresh and consistent with high-velocity vehicular collision."
    r4_content_hash = chain.calculate_content_hash(r4_blob)
    r4_prev = r3_rec_hash
    r4_time = (c1_time + timedelta(hours=6, minutes=45)).isoformat()
    r4_rec_hash = chain.calculate_record_hash(r4_prev, r4_content_hash, "Dr. A. Sharma, CMO", r4_time)
    r4_tx = blockchain.generate_tx_hash(r4_rec_hash, 4)
    r4_id = db.insert_record(c1_id, "Final Opinion", "Dr. A. Sharma, CMO", "Hospital", r4_blob, "final_opinion_0042.txt", r4_content_hash, r4_prev, r4_rec_hash, r4_time, None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], r4_tx, blockchain.get_onchain_block_number(4))

    # 2. Case 2: POCSO Case (OVERDUE 47 DAYS)
    c2_time = now - timedelta(days=47)
    c2_id = db.create_case(
        case_no="MLC-2026-0038",
        case_type="POCSO Case",
        patient_alias="Minor Subject (Confidential)",
        hospital="Govt. District Hospital, Civil Lines",
        incident_date=(c2_time - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        injury_summary="Confidential medical examination requested by Special Juvenile Police Unit under POCSO Act §33.",
        duty_doctor="Dr. N. Joshi, Gynaecologist",
        doctor_nmc_reg="NMC-2016-72819",
        entry_duration_seconds=58,
        created_at=c2_time.isoformat()
    )

    c2_r1_blob = b"POCSO CONFIDENTIAL EMERGENCY INTAKE\nCase: MLC-2026-0038\nExamining Doctor: Dr. N. Joshi, Gynaecologist\nVictim Identity Protected under Section 33, POCSO Act 2012.\nPreliminary examination completed in presence of female medical officer and legal support person."
    c2_r1_chash = chain.calculate_content_hash(c2_r1_blob)
    c2_r1_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c2_r1_chash, "Dr. N. Joshi, Gynaecologist", c2_time.isoformat())
    c2_kyc = kyc.get_doctor_kyc("Dr. N. Joshi, Gynaecologist")
    c2_tx = blockchain.generate_tx_hash(c2_r1_rec, 5)
    db.insert_record(c2_id, "MLC Entry", "Dr. N. Joshi, Gynaecologist", "Hospital", c2_r1_blob, "pocso_intake_0038.txt", c2_r1_chash, chain.GENESIS_PREV_HASH, c2_r1_rec, c2_time.isoformat(), None, c2_kyc["nmc_reg"], c2_kyc["kyc_hash"], c2_tx, blockchain.get_onchain_block_number(5))

    c2_r2_time = (c2_time + timedelta(hours=3)).isoformat()
    c2_r2_blob = b"POCSO STATUTORY MEDICAL EXAMINATION REPORT\nDoctor: Dr. N. Joshi, Gynaecologist\nDetailed clinical findings sealed in tamper-evident biological specimen kit. Forwarded to State Forensic Science Laboratory."
    c2_r2_chash = chain.calculate_content_hash(c2_r2_blob)
    c2_r2_rec = chain.calculate_record_hash(c2_r1_rec, c2_r2_chash, "Dr. N. Joshi, Gynaecologist", c2_r2_time)
    c2_r2_tx = blockchain.generate_tx_hash(c2_r2_rec, 6)
    db.insert_record(c2_id, "Medical Examination", "Dr. N. Joshi, Gynaecologist", "Hospital", c2_r2_blob, "pocso_exam_0038.txt", c2_r2_chash, c2_r1_rec, c2_r2_rec, c2_r2_time, None, c2_kyc["nmc_reg"], c2_kyc["kyc_hash"], c2_r2_tx, blockchain.get_onchain_block_number(6))

    # 3. Case 3: Assault Case
    c3_time = now - timedelta(days=5)
    c3_id = db.create_case(
        case_no="MLC-2026-0039",
        case_type="Assault",
        patient_alias="Suresh Patel, 28M",
        hospital="Govt. District Hospital, Civil Lines",
        incident_date=(c3_time - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
        injury_summary="Multiple defense wounds over forearms and incised wound 4cm over left cheek inflicted with sharp object.",
        duty_doctor="Dr. A. Sharma, CMO",
        doctor_nmc_reg="NMC-2018-84920",
        entry_duration_seconds=36,
        created_at=c3_time.isoformat()
    )

    c3_r1_blob = b"MEDICO-LEGAL EMERGENCY INTAKE - PHYSICAL ASSAULT\nPatient: Suresh Patel, 28/M\nBrought by: Sub-Inspector V. Patil, PS Sector-4\nAlleged History: Physical altercation with sharp weapon\nInjuries: Incised wound 4x0.5cm over left zygomatic region, contusions on bilateral forearms."
    c3_r1_chash = chain.calculate_content_hash(c3_r1_blob)
    c3_r1_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c3_r1_chash, "Dr. A. Sharma, CMO", c3_time.isoformat())
    c3_tx = blockchain.generate_tx_hash(c3_r1_rec, 7)
    db.insert_record(c3_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", c3_r1_blob, "mlc_assault_0039.txt", c3_r1_chash, chain.GENESIS_PREV_HASH, c3_r1_rec, c3_time.isoformat(), None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], c3_tx, blockchain.get_onchain_block_number(7))

    # 4. Cases 4-7
    c4_time = now - timedelta(days=12)
    c4_id = db.create_case("MLC-2026-0035", "Road Accident", "Vikram Singh, 45M", "Govt. District Hospital, Civil Lines", (c4_time - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), "Multiple abrasions, fracture clavicle left side.", "Dr. K. Verma, Forensic Specialist", "NMC-2015-61294", 40, c4_time.isoformat())
    c4_blob = b"MLC INTAKE: Vikram Singh, 45M. Fracture left clavicle following two-wheeler skid."
    c4_chash = chain.calculate_content_hash(c4_blob)
    c4_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c4_chash, "Dr. K. Verma, Forensic Specialist", c4_time.isoformat())
    c4_kyc = kyc.get_doctor_kyc("Dr. K. Verma, Forensic Specialist")
    db.insert_record(c4_id, "MLC Entry", "Dr. K. Verma, Forensic Specialist", "Hospital", c4_blob, "mlc_0035.txt", c4_chash, chain.GENESIS_PREV_HASH, c4_rec, c4_time.isoformat(), None, c4_kyc["nmc_reg"], c4_kyc["kyc_hash"], blockchain.generate_tx_hash(c4_rec, 8), blockchain.get_onchain_block_number(8))

    c5_time = now - timedelta(days=8)
    c5_id = db.create_case("MLC-2026-0036", "Assault", "Anita Devi, 32F", "Govt. District Hospital, Civil Lines", (c5_time - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "Blunt injuries to chest wall and facial contusions.", "Dr. A. Sharma, CMO", "NMC-2018-84920", 50, c5_time.isoformat())
    c5_blob = b"MLC INTAKE: Anita Devi, 32F. Domestic altercation, tender lower ribs left."
    c5_chash = chain.calculate_content_hash(c5_blob)
    c5_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c5_chash, "Dr. A. Sharma, CMO", c5_time.isoformat())
    db.insert_record(c5_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", c5_blob, "mlc_0036.txt", c5_chash, chain.GENESIS_PREV_HASH, c5_rec, c5_time.isoformat(), None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], blockchain.generate_tx_hash(c5_rec, 9), blockchain.get_onchain_block_number(9))

    c6_time = now - timedelta(days=4)
    c6_id = db.create_case("MLC-2026-0040", "Road Accident", "Mohd. Irfan, 22M", "Govt. District Hospital, Civil Lines", (c6_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "Pedestrian hit by e-rickshaw, scalp laceration.", "Dr. M. Chawla, Resident", "NMC-2022-90184", 32, c6_time.isoformat())
    c6_blob = b"MLC INTAKE: Mohd. Irfan, 22M. Scalp laceration 3cm, clean edges, sutured under LA."
    c6_chash = chain.calculate_content_hash(c6_blob)
    c6_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c6_chash, "Dr. M. Chawla, Resident", c6_time.isoformat())
    c6_kyc = kyc.get_doctor_kyc("Dr. M. Chawla, Resident")
    db.insert_record(c6_id, "MLC Entry", "Dr. M. Chawla, Resident", "Hospital", c6_blob, "mlc_0040.txt", c6_chash, chain.GENESIS_PREV_HASH, c6_rec, c6_time.isoformat(), None, c6_kyc["nmc_reg"], c6_kyc["kyc_hash"], blockchain.generate_tx_hash(c6_rec, 10), blockchain.get_onchain_block_number(10))

    c7_time = now - timedelta(hours=18)
    c7_id = db.create_case("MLC-2026-0041", "Assault", "Deepak Rawat, 39M", "Govt. District Hospital, Civil Lines", (c7_time - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "Fracture nasal bone with epistaxis following street brawl.", "Dr. A. Sharma, CMO", "NMC-2018-84920", 44, c7_time.isoformat())
    c7_blob = b"MLC INTAKE: Deepak Rawat, 39M. Epistaxis arrested, nasal bridge swelling and deformity."
    c7_chash = chain.calculate_content_hash(c7_blob)
    c7_rec = chain.calculate_record_hash(chain.GENESIS_PREV_HASH, c7_chash, "Dr. A. Sharma, CMO", c7_time.isoformat())
    db.insert_record(c7_id, "MLC Entry", "Dr. A. Sharma, CMO", "Hospital", c7_blob, "mlc_0041.txt", c7_chash, chain.GENESIS_PREV_HASH, c7_rec, c7_time.isoformat(), None, r1_kyc["nmc_reg"], r1_kyc["kyc_hash"], blockchain.generate_tx_hash(c7_rec, 11), blockchain.get_onchain_block_number(11))

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

if __name__ == "__main__":
    seed_database(force=True)
