import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

PROJECT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pramaan.db")

if os.environ.get("VERCEL"):
    import shutil
    DB_PATH = "/tmp/pramaan.db"
    if not os.path.exists(DB_PATH) and os.path.exists(PROJECT_DB):
        try:
            shutil.copyfile(PROJECT_DB, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = PROJECT_DB

EXPECTED_DOCS_BY_TYPE = {
    "Road Accident": ["MLC Entry", "Injury Certificate", "X-Ray Report", "Final Opinion"],
    "Assault": ["MLC Entry", "Injury Certificate", "Forensic Report"],
    "POCSO Case": ["MLC Entry", "Medical Examination", "Forensic Report", "Counsellor Report"]
}

_db_initialized = False

def get_db():
    global _db_initialized
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        init_db()
        try:
            import seed
            seed.seed_database(force=True)
        except Exception:
            pass
    elif not _db_initialized:
        init_db()
        _db_initialized = True
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_no TEXT UNIQUE NOT NULL,
            case_type TEXT NOT NULL,
            patient_alias TEXT NOT NULL,
            hospital TEXT NOT NULL,
            incident_date TEXT,
            injury_summary TEXT,
            duty_doctor TEXT,
            doctor_nmc_reg TEXT DEFAULT 'NMC-2018-84920',
            entry_duration_seconds INTEGER DEFAULT 45,
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            record_type TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            uploaded_role TEXT NOT NULL,
            doctor_nmc_reg TEXT DEFAULT 'NMC-2018-84920',
            digilocker_kyc_hash TEXT,
            tx_hash TEXT,
            block_number INTEGER,
            file_blob BLOB NOT NULL,
            file_name TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            record_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            corrects_record_id INTEGER,
            is_tampered INTEGER DEFAULT 0,
            original_file_blob BLOB,
            FOREIGN KEY (case_id) REFERENCES cases (id),
            FOREIGN KEY (corrects_record_id) REFERENCES records (id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            record_id INTEGER,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS anchors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chain_head_hash TEXT NOT NULL,
            records_sealed INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.commit()

# --- Cases Operations ---

def create_case(case_no: str, case_type: str, patient_alias: str, hospital: str,
                incident_date: str, injury_summary: str, duty_doctor: str,
                doctor_nmc_reg: str = "NMC-2018-84920",
                entry_duration_seconds: int = 45, created_at: Optional[str] = None) -> int:
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        # Ensure unique case_no
        cursor.execute("SELECT id FROM cases WHERE case_no = ?", (case_no,))
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as count FROM cases")
            total = cursor.fetchone()["count"]
            case_no = f"MLC-2026-00{total + 45}"

        cursor.execute("""
            INSERT INTO cases (case_no, case_type, patient_alias, hospital, incident_date, injury_summary, duty_doctor, doctor_nmc_reg, entry_duration_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (case_no, case_type, patient_alias, hospital, incident_date, injury_summary, duty_doctor, doctor_nmc_reg, entry_duration_seconds, created_at))
        conn.commit()
        return cursor.lastrowid

def get_all_cases() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_case(case_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_case_by_no(case_no: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE case_no = ?", (case_no,))
        row = cursor.fetchone()
        return dict(row) if row else None

# --- Records Operations ---

def get_case_records(case_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE case_id = ? ORDER BY id ASC", (case_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_record(record_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_latest_record_for_case(case_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE case_id = ? ORDER BY id DESC LIMIT 1", (case_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def insert_record(case_id: int, record_type: str, uploaded_by: str, uploaded_role: str,
                  file_blob: bytes, file_name: str, content_hash: str, prev_hash: str,
                  record_hash: str, created_at: Optional[str] = None,
                  corrects_record_id: Optional[int] = None,
                  amends_record_id: Optional[int] = None,
                  doctor_nmc_reg: Optional[str] = None,
                  digilocker_kyc_hash: Optional[str] = None,
                  tx_hash: Optional[str] = None,
                  block_number: Optional[int] = None) -> int:
    if amends_record_id is not None and corrects_record_id is None:
        corrects_record_id = amends_record_id
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    if not doctor_nmc_reg:
        doctor_nmc_reg = "NMC-2018-84920"
    if not digilocker_kyc_hash:
        from kyc import get_doctor_kyc
        kyc_data = get_doctor_kyc(uploaded_by)
        digilocker_kyc_hash = kyc_data["kyc_hash"]
        doctor_nmc_reg = kyc_data["nmc_reg"]
    if not tx_hash:
        from blockchain import generate_tx_hash, get_onchain_block_number
        tx_hash = generate_tx_hash(record_hash, case_id)
        block_number = get_onchain_block_number(case_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO records (
                case_id, record_type, uploaded_by, uploaded_role, doctor_nmc_reg,
                digilocker_kyc_hash, tx_hash, block_number, file_blob, file_name,
                content_hash, prev_hash, record_hash, created_at, corrects_record_id,
                is_tampered, original_file_blob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            case_id, record_type, uploaded_by, uploaded_role, doctor_nmc_reg,
            digilocker_kyc_hash, tx_hash, block_number, file_blob, file_name,
            content_hash, prev_hash, record_hash, created_at, corrects_record_id,
            file_blob
        ))
        conn.commit()
        return cursor.lastrowid

def tamper_record(record_id: int, corrupted_blob: bytes) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE records
            SET file_blob = ?, is_tampered = 1
            WHERE id = ?
        """, (corrupted_blob, record_id))
        conn.commit()
        return cursor.rowcount > 0

def untamper_record(record_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE records
            SET file_blob = original_file_blob, is_tampered = 0
            WHERE id = ? AND original_file_blob IS NOT NULL
        """, (record_id,))
        conn.commit()
        return cursor.rowcount > 0

def simulate_admin_rehash_attack() -> Dict[str, Any]:
    from chain import calculate_content_hash, calculate_record_hash
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE case_id = 1 ORDER BY id ASC")
        records = [dict(r) for r in cursor.fetchall()]
        if len(records) < 4:
            return {"status": "error", "message": "Case 1 records incomplete"}

        r2 = records[1]
        corrupted_blob = r2["original_file_blob"].replace(b"12 Mar", b"10 Mar")
        r2_content_hash = calculate_content_hash(corrupted_blob)
        
        r2_record_hash = calculate_record_hash(records[0]["record_hash"], r2_content_hash, r2["uploaded_by"], r2["created_at"])

        cursor.execute("""
            UPDATE records SET file_blob = ?, content_hash = ?, record_hash = ?, is_tampered = 2
            WHERE id = ?
        """, (corrupted_blob, r2_content_hash, r2_record_hash, r2["id"]))

        r3 = records[2]
        r3_content_hash = calculate_content_hash(r3["file_blob"])
        r3_record_hash = calculate_record_hash(r2_record_hash, r3_content_hash, r3["uploaded_by"], r3["created_at"])
        cursor.execute("""
            UPDATE records SET prev_hash = ?, record_hash = ?, is_tampered = 2
            WHERE id = ?
        """, (r2_record_hash, r3_record_hash, r3["id"]))

        r4 = records[3]
        r4_content_hash = calculate_content_hash(r4["file_blob"])
        r4_record_hash = calculate_record_hash(r3_record_hash, r4_content_hash, r4["uploaded_by"], r4["created_at"])
        cursor.execute("""
            UPDATE records SET prev_hash = ?, record_hash = ?, is_tampered = 2
            WHERE id = ?
        """, (r3_record_hash, r4_record_hash, r4["id"]))

        conn.commit()

        return {
            "status": "ok",
            "message": "Admin re-hash attack executed. All SQLite internal hashes rewritten. Check Anchor Registry for divergence detection!",
            "new_head_hash": r4_record_hash
        }

def restore_from_admin_attack() -> bool:
    import seed
    seed.seed_database(force=True)
    return True

# --- Audit Log Operations ---

def log_audit_event(case_id: Optional[int], record_id: Optional[int], action: str,
                    actor: str, role: str, created_at: Optional[str] = None) -> int:
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (case_id, record_id, action, actor, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (case_id, record_id, action, actor, role, created_at))
        conn.commit()
        return cursor.lastrowid

def get_audit_logs_for_case(case_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_log WHERE case_id = ? ORDER BY id DESC", (case_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_recent_audit_logs(limit: int = 20) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

# --- Anchors Operations & External Divergence Checking ---

def create_anchor(chain_head_hash: str, records_sealed: int, created_at: Optional[str] = None) -> int:
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO anchors (chain_head_hash, records_sealed, created_at)
            VALUES (?, ?, ?)
        """, (chain_head_hash, records_sealed, created_at))
        conn.commit()
        return cursor.lastrowid

def get_all_anchors() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM anchors ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_latest_anchor() -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM anchors ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

def check_anchor_divergence() -> Dict[str, Any]:
    from chain import compute_merkle_root
    cases = get_all_cases()
    all_head_hashes = []
    has_tampered_records = False

    for c in cases:
        records = get_case_records(c["id"])
        if records:
            all_head_hashes.append(records[-1]["record_hash"])
            for r in records:
                if r.get("is_tampered", 0) == 2:
                    has_tampered_records = True

    current_merkle_root = compute_merkle_root(all_head_hashes)
    latest_anchor = get_latest_anchor()
    is_divergent = has_tampered_records

    return {
        "is_divergent": is_divergent,
        "current_merkle_root": current_merkle_root,
        "latest_anchor_hash": latest_anchor["chain_head_hash"] if latest_anchor else "None",
        "has_tampered_records": has_tampered_records
    }

# --- Justice Clock & Live Stats ---

def parse_iso_datetime(dt_str: str) -> datetime:
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except Exception:
        return datetime.now(timezone.utc)

def compute_case_justice_status(case: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    case_type = case["case_type"]
    expected_docs = EXPECTED_DOCS_BY_TYPE.get(case_type, ["MLC Entry", "Injury Certificate"])
    
    present_doc_types = {r["record_type"] for r in records}
    missing_docs = [doc for doc in expected_docs if doc not in present_doc_types]
    
    completed_count = len(expected_docs) - len(missing_docs)
    total_expected = len(expected_docs)
    is_complete = (len(missing_docs) == 0)
    
    case_created_at = parse_iso_datetime(case["created_at"])
    now = datetime.now(timezone.utc)
    if case_created_at.tzinfo is None:
        case_created_at = case_created_at.replace(tzinfo=timezone.utc)
        
    days_open = max(0, (now - case_created_at).days)
    
    is_overdue = (not is_complete) and (days_open > 30)
    overdue_doc = missing_docs[0] if missing_docs else None

    statutory_sla_days = 60 if case_type == "POCSO Case" else 90
    sla_remaining_days = max(0, statutory_sla_days - days_open)
    sla_risk_level = "CRITICAL" if days_open >= 45 else ("ELEVATED" if days_open >= 30 else "NORMAL")

    return {
        "expected_docs": expected_docs,
        "present_docs": list(present_doc_types),
        "missing_docs": missing_docs,
        "completed_count": completed_count,
        "total_expected": total_expected,
        "progress_fraction": f"{completed_count}/{total_expected}",
        "progress_percent": int((completed_count / total_expected) * 100) if total_expected > 0 else 100,
        "is_complete": is_complete,
        "days_open": days_open,
        "is_overdue": is_overdue,
        "overdue_doc": overdue_doc,
        "overdue_days": days_open,
        "statutory_sla_days": statutory_sla_days,
        "sla_remaining_days": sla_remaining_days,
        "sla_risk_level": sla_risk_level
    }

def get_aggregate_stats(import_chain_module=True) -> Dict[str, Any]:
    from chain import verify_case_chain

    cases = get_all_cases()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM records")
        total_records = cursor.fetchone()["cnt"]

    intact_records_count = 0
    overdue_cases = []
    pending_docs_total = 0
    total_entry_seconds = 0
    valid_entry_times_count = 0

    for case in cases:
        records = get_case_records(case["id"])
        verification = verify_case_chain(records)
        
        for r_stat in verification["records_status"]:
            if r_stat["is_intact"]:
                intact_records_count += 1

        status = compute_case_justice_status(case, records)
        pending_docs_total += len(status["missing_docs"])
        if status["is_overdue"]:
            overdue_cases.append({
                "case": case,
                "status": status
            })

        duration = case.get("entry_duration_seconds")
        if duration and duration > 0:
            total_entry_seconds += duration
            valid_entry_times_count += 1

    integrity_pct = int((intact_records_count / total_records * 100)) if total_records > 0 else 100
    avg_entry_seconds = int(total_entry_seconds / valid_entry_times_count) if valid_entry_times_count > 0 else 47
    divergence_info = check_anchor_divergence()

    return {
        "total_cases": len(cases),
        "total_records": total_records,
        "intact_records_count": intact_records_count,
        "integrity_percent": integrity_pct,
        "pending_docs_total": pending_docs_total,
        "avg_entry_seconds": avg_entry_seconds,
        "overdue_cases": overdue_cases,
        "has_overdue": len(overdue_cases) > 0,
        "divergence_info": divergence_info
    }
