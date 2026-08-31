import os
import sys
import io
import time
import zipfile
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, Request, Form, UploadFile, File, Response, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import qrcode

from backend.database import db, seed
from backend.services import kyc, sarvam
from backend.core import blockchain
from backend.core.chain import (
    calculate_content_hash,
    calculate_record_hash,
    verify_case_chain,
    verify_record_integrity,
    compute_merkle_root,
    generate_merkle_proof,
    verify_merkle_proof
)

app = FastAPI(
    title="PRAMAAN Medico-Legal Evidence Platform",
    description="Section 63 BSA 2023 Compliant Electronic Evidence Infrastructure"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Robust multi-path template discovery
def _get_template_dirs():
    candidates = [
        os.path.join(PROJECT_ROOT, "frontend", "templates"),
        os.path.join(PROJECT_ROOT, "templates"),
        os.path.join(BASE_DIR, "templates"),
        os.path.join(os.getcwd(), "frontend", "templates"),
        os.path.join(os.getcwd(), "templates"),
        "/var/task/frontend/templates",
        "/var/task/templates",
        "/var/task/api/frontend/templates",
        "/var/task/api/templates",
    ]
    found = [c for c in candidates if os.path.exists(c) and os.path.isdir(c)]
    return found if found else [os.path.join(PROJECT_ROOT, "frontend", "templates")]

TEMPLATES_DIRS = _get_template_dirs()
templates = Jinja2Templates(directory=TEMPLATES_DIRS)

# Resolve STATIC_DIR safely
def _get_static_dir():
    candidates = [
        os.path.join(PROJECT_ROOT, "frontend", "static"),
        os.path.join(PROJECT_ROOT, "static"),
        os.path.join(os.getcwd(), "frontend", "static"),
        os.path.join(os.getcwd(), "static"),
        "/var/task/frontend/static",
        "/var/task/static",
        "/var/task/api/frontend/static",
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return c
    fallback = os.path.join(PROJECT_ROOT, "frontend", "static")
    try:
        os.makedirs(fallback, exist_ok=True)
    except Exception:
        pass
    return fallback

STATIC_DIR = _get_static_dir()
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def on_startup():
    try:
        db.init_db()
        cases = db.get_all_cases()
        if not cases:
            print("Empty database detected. Seeding 7 realistic cases...")
            seed.seed_database(force=True)
    except Exception as e:
        print(f"Startup initialization notice: {e}")

# Global Exception Diagnostic Handler for Serverless
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    err_tb = traceback.format_exc()
    print(f"PRAMAAN Server Error on {request.url.path}: {err_tb}")
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
        <html>
        <head><title>PRAMAAN Server Status</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css">
        </head>
        <body class="bg-gray-950 text-white p-8 font-mono">
          <div class="max-w-2xl mx-auto bg-gray-900 p-6 rounded-2xl border border-yellow-500 shadow-2xl">
            <h1 class="text-xl font-bold text-yellow-400 mb-2">⚖️ PRAMAAN Server Diagnostic Notice</h1>
            <p class="text-xs text-gray-300 mb-4">Request to <code class="text-yellow-300">{request.url.path}</code> encountered an error:</p>
            <pre class="bg-black p-4 rounded-xl text-[11px] text-red-400 overflow-x-auto leading-relaxed">{err_tb}</pre>
            <div class="mt-4 flex gap-3">
              <a href="/api/system/health" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg">Check Health API</a>
              <a href="/" class="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-gray-900 font-bold text-xs rounded-lg">Return to Home</a>
            </div>
          </div>
        </body>
        </html>""",
        status_code=500
    )

# Vercel Internal Rewrite Path Normalizer Middleware
@app.middleware("http")
async def vercel_internal_rewrite_middleware(request: Request, call_next):
    matched_path = request.headers.get("x-matched-path")
    original_uri = request.headers.get("x-forwarded-uri")
    path = request.scope.get("path", "")

    if matched_path and not matched_path.startswith("/api/index"):
        request.scope["path"] = matched_path
    elif original_uri and not original_uri.startswith("/api/index"):
        request.scope["path"] = original_uri.split("?")[0]
    elif path.startswith("/api/index.py"):
        new_path = path[len("/api/index.py"):]
        request.scope["path"] = new_path if new_path.startswith("/") else ("/" + new_path)
    elif path.startswith("/api/index"):
        new_path = path[len("/api/index"):]
        request.scope["path"] = new_path if new_path.startswith("/") else ("/" + new_path)

    return await call_next(request)

# Helper to get current role from cookies
def get_current_role(request: Request) -> str:
    role = request.cookies.get("pramaan_role", "Hospital")
    if role not in ["Hospital", "Police", "Court"]:
        return "Hospital"
    return role

# --- ROUTE 1: LANDING PAGE (/) ---
@app.get("/", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
async def landing_page(request: Request):
    stats = db.get_aggregate_stats()
    demo_case = db.get_case_by_no("MLC-2026-0042")
    demo_record = None
    if demo_case:
        case_recs = db.get_case_records(demo_case["id"])
        for r in case_recs:
            if r["record_type"] == "Injury Certificate":
                demo_record = r
                break
        if not demo_record and case_recs:
            demo_record = case_recs[0]
            
    if not demo_record:
        all_cases = db.get_all_cases()
        if all_cases:
            first_case_recs = db.get_case_records(all_cases[0]["id"])
            if first_case_recs:
                demo_record = first_case_recs[0]

    if not demo_record:
        demo_record = {
            "id": 1,
            "record_type": "Injury Certificate",
            "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "record_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
    current_role = get_current_role(request)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "stats": stats,
        "demo_record": demo_record,
        "current_role": current_role,
        "is_standalone_verifier": True
    })

# --- ROUTE 2: DASHBOARD (/dashboard) ---
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    current_role = get_current_role(request)
    stats = db.get_aggregate_stats()
    cases = db.get_all_cases()

    case_rows = []
    for c in cases:
        records = db.get_case_records(c["id"])
        verification = verify_case_chain(records)
        justice = db.compute_case_justice_status(c, records)
        case_rows.append({
            "case": c,
            "records": records,
            "verification": verification,
            "justice": justice
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_role": current_role,
        "active_page": "dashboard",
        "stats": stats,
        "cases": cases,
        "case_rows": case_rows,
        "is_standalone_verifier": False
    })

# --- ROUTE 3: NEW MLC ENTRY FORM (/cases/new) ---
@app.get("/cases/new", response_class=HTMLResponse)
async def new_case_form(request: Request):
    current_role = get_current_role(request)
    if current_role != "Hospital":
        return RedirectResponse(url="/dashboard")

    cases = db.get_all_cases()
    next_case_no = f"MLC-2026-00{len(cases) + 43}"
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return templates.TemplateResponse("new_case.html", {
        "request": request,
        "current_role": current_role,
        "active_page": "new_case",
        "next_case_no": next_case_no,
        "today_date": today_date,
        "is_standalone_verifier": False
    })

@app.post("/cases/new")
async def create_new_case(
    request: Request,
    case_no: str = Form(...),
    case_type: str = Form(...),
    patient_alias: str = Form(...),
    incident_date: str = Form(...),
    injury_summary: str = Form(...),
    duty_doctor: str = Form(...),
    form_started_at: Optional[str] = Form(None),
    evidence_file: Optional[UploadFile] = File(None)
):
    current_role = get_current_role(request)
    if current_role != "Hospital":
        raise HTTPException(status_code=403, detail="Only Hospital staff may initiate cases.")

    entry_duration = 45
    if form_started_at:
        try:
            start_ms = float(form_started_at)
            elapsed_sec = int((time.time() * 1000 - start_ms) / 1000)
            if 1 <= elapsed_sec <= 600:
                entry_duration = elapsed_sec
        except Exception:
            pass

    now_iso = datetime.now(timezone.utc).isoformat()
    hospital_name = "Govt. District Hospital, Civil Lines"

    case_id = db.create_case(
        case_no=case_no,
        case_type=case_type,
        patient_alias=patient_alias,
        hospital=hospital_name,
        incident_date=incident_date,
        injury_summary=injury_summary,
        duty_doctor=duty_doctor,
        entry_duration_seconds=entry_duration,
        created_at=now_iso
    )

    if evidence_file and evidence_file.filename:
        file_bytes = await evidence_file.read()
        file_name = evidence_file.filename
    else:
        file_bytes = seed.generate_file_content(
            "MLC Entry", case_no, patient_alias,
            f"Emergency intake recorded. Incident Date: {incident_date}.\nObservations: {injury_summary}\nAttending: {duty_doctor}"
        )
        file_name = f"MLC_Entry_{case_no.replace('MLC-', '')}.txt"

    content_hash = calculate_content_hash(file_bytes)
    record_hash = calculate_record_hash("GENESIS", content_hash, duty_doctor, now_iso)
    doc_kyc = kyc.get_doctor_kyc(duty_doctor)
    tx_hash = blockchain.generate_tx_hash(record_hash, case_id)
    block_num = blockchain.get_onchain_block_number(case_id)

    record_id = db.insert_record(
        case_id=case_id,
        record_type="MLC Entry",
        uploaded_by=duty_doctor,
        uploaded_role="Hospital",
        file_blob=file_bytes,
        file_name=file_name,
        content_hash=content_hash,
        prev_hash="GENESIS",
        record_hash=record_hash,
        created_at=now_iso,
        amends_record_id=None,
        doctor_nmc_reg=doc_kyc.get("nmc_reg", "NMC-2018-84920"),
        digilocker_kyc_hash=doc_kyc.get("kyc_hash", "0xabc"),
        tx_hash=tx_hash,
        block_number=block_num
    )

    db.log_audit_event(case_id, record_id, "Case Created & Genesis Sealed", duty_doctor, "Hospital", now_iso)
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)

# --- ROUTE 4: CASE TIMELINE (/cases/{id}) ---
@app.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_timeline(case_id: int, request: Request):
    current_role = get_current_role(request)
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    records = db.get_case_records(case_id)
    verification = verify_case_chain(records)
    justice = db.compute_case_justice_status(case, records)
    audit_logs = db.get_audit_logs_for_case(case_id)

    if case["case_type"] == "POCSO Case" and current_role == "Hospital":
        db.log_audit_event(case_id, None, "Identity & Case Inspected", "Hospital Staff", "Hospital")
    else:
        db.log_audit_event(case_id, None, "Case Inspected", f"{current_role} User", current_role)

    return templates.TemplateResponse("timeline.html", {
        "request": request,
        "case": case,
        "records": records,
        "verification": verification,
        "justice": justice,
        "audit_logs": audit_logs,
        "current_role": current_role,
        "active_page": "dashboard",
        "is_standalone_verifier": False
    })

# --- ROUTE: ADD RECORD (/records/add) ---
@app.post("/records/add")
async def add_record_to_chain(
    request: Request,
    case_id: int = Form(...),
    record_type: str = Form(...),
    uploaded_by: str = Form(...),
    notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    current_role = get_current_role(request)
    if current_role != "Hospital":
        raise HTTPException(status_code=403, detail="Read-only role.")

    case = db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    latest_record = db.get_latest_record_for_case(case_id)
    prev_hash = latest_record["record_hash"] if latest_record else "GENESIS"

    if file and file.filename:
        file_bytes = await file.read()
        file_name = file.filename
    else:
        content_text = notes if notes else f"{record_type} official medical report."
        file_bytes = seed.generate_file_content(record_type, case["case_no"], case["patient_alias"], content_text)
        file_name = f"{record_type.replace(' ', '_')}_{case['case_no'].replace('MLC-', '')}.txt"

    now_iso = datetime.now(timezone.utc).isoformat()
    content_hash = calculate_content_hash(file_bytes)
    record_hash = calculate_record_hash(prev_hash, content_hash, uploaded_by, now_iso)
    doc_kyc = kyc.get_doctor_kyc(uploaded_by)
    tx_hash = blockchain.generate_tx_hash(record_hash, case_id)
    block_num = blockchain.get_onchain_block_number(case_id)

    record_id = db.insert_record(
        case_id=case_id,
        record_type=record_type,
        uploaded_by=uploaded_by,
        uploaded_role="Hospital",
        file_blob=file_bytes,
        file_name=file_name,
        content_hash=content_hash,
        prev_hash=prev_hash,
        record_hash=record_hash,
        created_at=now_iso,
        amends_record_id=None,
        doctor_nmc_reg=doc_kyc.get("nmc_reg", "NMC-2018-84920"),
        digilocker_kyc_hash=doc_kyc.get("kyc_hash", "0xabc"),
        tx_hash=tx_hash,
        block_number=block_num
    )

    db.log_audit_event(case_id, record_id, "Record Appended & Sealed", uploaded_by, "Hospital", now_iso)
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)

# --- ROUTE: ADD CORRECTION / AMENDMENT (/records/{id}/correct) ---
@app.post("/records/{record_id}/correct")
async def add_correction_record(
    record_id: int,
    request: Request,
    case_id: int = Form(...),
    record_type: str = Form(...),
    uploaded_by: str = Form(...),
    notes: str = Form(...)
):
    current_role = get_current_role(request)
    if current_role != "Hospital":
        raise HTTPException(status_code=403, detail="Read-only role.")

    target_record = db.get_record(record_id)
    if not target_record:
        raise HTTPException(status_code=404, detail="Target record not found")

    case = db.get_case(case_id)
    latest_record = db.get_latest_record_for_case(case_id)
    prev_hash = latest_record["record_hash"] if latest_record else "GENESIS"

    file_bytes = seed.generate_file_content(
        record_type, case["case_no"], case["patient_alias"],
        f"OFFICIAL AMENDMENT TO RECORD #{target_record['id']} ({target_record['record_type']}):\n{notes}"
    )
    file_name = f"Amendment_Rec_{target_record['id']}_{case['case_no'].replace('MLC-', '')}.txt"

    now_iso = datetime.now(timezone.utc).isoformat()
    content_hash = calculate_content_hash(file_bytes)
    record_hash = calculate_record_hash(prev_hash, content_hash, uploaded_by, now_iso)
    doc_kyc = kyc.get_doctor_kyc(uploaded_by)
    tx_hash = blockchain.generate_tx_hash(record_hash, case_id)
    block_num = blockchain.get_onchain_block_number(case_id)

    new_record_id = db.insert_record(
        case_id=case_id,
        record_type=record_type,
        uploaded_by=uploaded_by,
        uploaded_role="Hospital",
        file_blob=file_bytes,
        file_name=file_name,
        content_hash=content_hash,
        prev_hash=prev_hash,
        record_hash=record_hash,
        created_at=now_iso,
        amends_record_id=target_record["id"],
        doctor_nmc_reg=doc_kyc.get("nmc_reg", "NMC-2018-84920"),
        digilocker_kyc_hash=doc_kyc.get("kyc_hash", "0xabc"),
        tx_hash=tx_hash,
        block_number=block_num
    )

    db.log_audit_event(case_id, new_record_id, f"Amendment Sealed for Record #{target_record['id']}", uploaded_by, "Hospital", now_iso)
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)

# --- ROUTE: INTEGRITY RECEIPT (/records/{id}) ---
@app.get("/records/{record_id}", response_class=HTMLResponse)
async def integrity_receipt(record_id: int, request: Request):
    current_role = get_current_role(request)
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    case = db.get_case(record["case_id"])
    file_content_text = record["file_blob"].decode("utf-8", errors="replace")

    db.log_audit_event(case["id"], record_id, "Receipt Inspected", f"{current_role} User", current_role)

    return templates.TemplateResponse("receipt.html", {
        "request": request,
        "record": record,
        "case": case,
        "file_content_text": file_content_text,
        "request_host": request.headers.get("host", "localhost:8000"),
        "current_role": current_role,
        "is_standalone_verifier": False
    })

@app.get("/records/{record_id}/download")
async def download_record_blob(record_id: int, request: Request):
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    current_role = get_current_role(request)
    db.log_audit_event(record["case_id"], record_id, "Raw Blob Downloaded", f"{current_role} User", current_role)

    return Response(
        content=record["file_blob"],
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{record["file_name"]}"'}
    )

# --- ROUTE: COURTROOM EVIDENCE DOSSIER EXPORT (/cases/{id}/export-bundle) ---
@app.get("/cases/{case_id}/export-bundle")
async def export_court_dossier_bundle(case_id: int, request: Request):
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    records = db.get_case_records(case_id)
    verification = verify_case_chain(records)
    audit_logs = db.get_audit_logs_for_case(case_id)
    current_role = get_current_role(request)
    now_iso = datetime.now(timezone.utc).isoformat()
    now_formatted = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M:%S UTC")

    db.log_audit_event(case_id, None, "Statutory Court Evidence Dossier Exported (.zip)", f"{current_role} User", current_role, now_iso)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        readme_content = f"""================================================================================
PRAMAAN MEDICO-LEGAL EVIDENCE DOSSIER — SECTION 63 BSA 2023 CERTIFIED
================================================================================
Master Case Reference: {case['case_no']}
Case Classification  : {case['case_type']}
Hospital Node        : {case['hospital']}
Incident Date        : {case['incident_date']}
Attending Examiner   : {case['duty_doctor']} ({case.get('doctor_nmc_reg', 'NMC-2018-84920')})
Export Timestamp     : {now_formatted}
Cryptographic Status : {'INTACT (VALIDATED 100%)' if verification['is_intact'] else 'CHAIN COMPROMISED / BROKEN'}
Merkle Root Hash     : {verification.get('merkle_root', 'N/A')}

LEGAL STATUTORY ADMISSIBILITY NOTICE:
This electronic evidence dossier has been generated under Section 63 of the
Bharatiya Sakshya Adhiniyam (BSA), 2023 and Section 193(3) of the Bharatiya
Nagarik Suraksha Sanhita (BNSS), 2023.

CONTENTS OF THIS DOSSIER:
1. /Section_63_BSA_Certificate.html - Formal Certificate of Electronic Integrity
2. /Evidence_Chain_Manifest.txt     - Cryptographic hashes, byte digests, on-chain Tx
3. /Cryptographic_Audit_Trail.json  - Immutable timestamped custody access trail
4. /raw_evidence_records/           - Unmodified byte-for-byte evidence documents

VERIFICATION INSTRUCTIONS FOR MAGISTRATES & PROSECUTORS:
1. Verify SHA-256 digests in Evidence_Chain_Manifest.txt against raw files.
2. Verify Polygon PoS On-Chain Smart Contract: 0x91F5C7A87A656a297E59b2d8cD6d3F3e4F2bc842
3. Scan QR code embedded in Section_63_BSA_Certificate.html for real-time validation.
================================================================================
"""
        zip_file.writestr("README_COURT_INSTRUCTIONS.txt", readme_content)

        manifest_lines = [
            f"PRAMAAN EVIDENCE CHAIN MANIFEST — CASE {case['case_no']}",
            f"Generated: {now_formatted}",
            f"Chain Intact: {verification['is_intact']}",
            f"Total Records Sealed: {len(records)}",
            f"Case Merkle Root: {verification.get('merkle_root')}",
            "-" * 80,
            f"{'ID':<4} | {'RECORD TYPE':<24} | {'SEALED BY':<22} | {'SHA-256 CONTENT HASH':<64}",
            "-" * 80,
        ]
        for idx, rec in enumerate(records):
            manifest_lines.append(
                f"#{rec['id']:<3} | {rec['record_type']:<24} | {rec['uploaded_by']:<22} | {rec['content_hash']}"
            )
            manifest_lines.append(f"     Prev Hash  : {rec['prev_hash']}")
            manifest_lines.append(f"     Record Hash: {rec['record_hash']}")
            manifest_lines.append(f"     On-Chain Tx: {rec.get('tx_hash', 'N/A')} (Block #{rec.get('block_number', 'N/A')})")
            manifest_lines.append(f"     Doctor KYC : {rec.get('doctor_nmc_reg', 'NMC-2018-84920')} | DigiLocker Hash: {rec.get('digilocker_kyc_hash', 'N/A')}")
            manifest_lines.append("-" * 80)

        zip_file.writestr("Evidence_Chain_Manifest.txt", "\n".join(manifest_lines))

        audit_payload = {
            "case_no": case["case_no"],
            "case_type": case["case_type"],
            "patient_alias": case["patient_alias"],
            "hospital": case["hospital"],
            "exported_at": now_iso,
            "chain_verification": verification,
            "records_summary": [
                {
                    "id": r["id"],
                    "type": r["record_type"],
                    "uploaded_by": r["uploaded_by"],
                    "doctor_nmc_reg": r.get("doctor_nmc_reg"),
                    "content_hash": r["content_hash"],
                    "prev_hash": r["prev_hash"],
                    "record_hash": r["record_hash"],
                    "tx_hash": r.get("tx_hash"),
                    "block_number": r.get("block_number"),
                    "created_at": r["created_at"]
                }
                for r in records
            ],
            "audit_events": audit_logs
        }
        zip_file.writestr("Cryptographic_Audit_Trail.json", json.dumps(audit_payload, indent=2))

        cert_template = templates.get_template("certificate.html")
        cert_html = cert_template.render({
            "request": request,
            "record": records[0] if records else {"id": 1, "record_type": "MLC Entry", "record_hash": "GENESIS", "created_at": now_iso},
            "case": case,
            "request_host": request.headers.get("host", "localhost:8000"),
            "current_role": current_role,
            "is_standalone_verifier": True
        })
        zip_file.writestr("Section_63_BSA_Certificate.html", cert_html)

        for idx, rec in enumerate(records):
            file_name = rec.get("file_name") or f"Record_{rec['id']}_{rec['record_type'].replace(' ', '_')}.txt"
            raw_blob = rec.get("file_blob") or b""
            if isinstance(raw_blob, str):
                raw_blob = raw_blob.encode("utf-8")
            zip_file.writestr(f"raw_evidence_records/{idx+1}_{file_name}", raw_blob)

    safe_case_no = case["case_no"].replace(" ", "_")
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="PRAMAAN_Dossier_{safe_case_no}.zip"'}
    )

# --- ROUTE 5: THE VERIFIER (/verify/{record_id}) ---
@app.get("/verify/{record_id}", response_class=HTMLResponse)
async def verifier_page(record_id: int, request: Request):
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    case = db.get_case(record["case_id"])
    all_case_records = db.get_case_records(case["id"])

    record_index = 1
    previous_hash = "GENESIS"
    for idx, r in enumerate(all_case_records):
        if r["id"] == record["id"]:
            record_index = idx + 1
            break
        previous_hash = r["record_hash"]

    record_status = verify_record_integrity(record, previous_hash)
    chain_verification = verify_case_chain(all_case_records)

    diff_info = None
    if not record_status["content_intact"] and record.get("original_file_blob"):
        orig_text = record["original_file_blob"].decode("utf-8", errors="replace")
        curr_text = record["file_blob"].decode("utf-8", errors="replace")
        if "12 Mar" in orig_text and "10 Mar" in curr_text:
            diff_info = {
                "original_excerpt": "Injury Date: 12 Mar",
                "corrupted_excerpt": "Injury Date: 10 Mar"
            }
        else:
            diff_info = {
                "original_excerpt": orig_text[:120],
                "corrupted_excerpt": curr_text[:120]
            }

    current_role = get_current_role(request)
    db.log_audit_event(case["id"], record_id, "Independent Verification Executed", "Independent Verifier", "Public")

    return templates.TemplateResponse("verify.html", {
        "request": request,
        "record": record,
        "case": case,
        "record_index": record_index,
        "total_records": len(all_case_records),
        "record_status": record_status,
        "chain_verification": chain_verification,
        "diff_info": diff_info,
        "current_role": current_role,
        "is_standalone_verifier": True
    })

# --- ROUTE: QR CODE GENERATOR (/qr/{record_id}) ---
@app.get("/qr/{record_id}")
async def generate_qr_code(record_id: int, request: Request):
    host = request.headers.get("host", "localhost:8000")
    scheme = "http"
    verify_url = f"{scheme}://{host}/verify/{record_id}"

    qr = qrcode.QRCode(
        version=1,
        box_size=7,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1B2A4A", back_color="#FFFFFF")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")

# --- ROUTE: TAMPER / UNTAMPER DEMO ENDPOINTS ---
@app.post("/dev/tamper/{record_id}")
async def tamper_record_endpoint(record_id: int):
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    blob = record["file_blob"]
    if b"12 Mar" in blob:
        corrupted_blob = blob.replace(b"12 Mar", b"10 Mar")
    else:
        corrupted_blob = blob + b"\n[TAMPER_CORRUPTED_BYTES]"

    db.tamper_record(record_id, corrupted_blob)
    return {"status": "ok", "record_id": record_id, "is_tampered": True}

@app.post("/dev/untamper/{record_id}")
async def untamper_record_endpoint(record_id: int):
    db.untamper_record(record_id)
    return {"status": "ok", "record_id": record_id, "is_tampered": False}

# --- ROUTE: A4 CERTIFICATE (/certificate/{record_id}) ---
@app.get("/certificate/{record_id}", response_class=HTMLResponse)
async def printable_certificate(record_id: int, request: Request):
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    case = db.get_case(record["case_id"])
    current_role = get_current_role(request)
    request_host = request.headers.get("host", "localhost:8000")

    db.log_audit_event(case["id"], record_id, "A4 Integrity Certificate Generated", f"{current_role} User", current_role)

    return templates.TemplateResponse("certificate.html", {
        "request": request,
        "record": record,
        "case": case,
        "request_host": request_host,
        "current_role": current_role,
        "is_standalone_verifier": True
    })

# --- ROUTE: ANCHOR REGISTRY (/anchor) ---
@app.get("/anchor", response_class=HTMLResponse)
async def anchor_page(request: Request):
    anchors = db.get_all_anchors()
    latest_anchor = db.get_latest_anchor()
    current_role = get_current_role(request)
    divergence_info = db.check_anchor_divergence()

    return templates.TemplateResponse("anchor.html", {
        "request": request,
        "anchors": anchors,
        "latest_anchor": latest_anchor,
        "divergence_info": divergence_info,
        "current_role": current_role,
        "active_page": "anchor",
        "is_standalone_verifier": False
    })

@app.post("/anchor/seal")
async def seal_today_anchor():
    stats = db.get_aggregate_stats()
    now_iso = datetime.now(timezone.utc).isoformat()
    chain_head_hash = calculate_record_hash("DAILY_ANCHOR_PREV", f"DAILY_ROOT_SNAP_{stats['total_records']}", "REGISTRY_PUBLIC_NODE", now_iso)
    db.create_anchor(chain_head_hash, stats["total_records"], now_iso)
    return RedirectResponse(url="/anchor", status_code=303)

# --- ROUTE: NATIONAL GOVERNMENT INTEGRATIONS (/integrations) ---
@app.get("/integrations", response_class=HTMLResponse)
async def integrations_page(request: Request):
    current_role = get_current_role(request)
    return templates.TemplateResponse("integrations.html", {
        "request": request,
        "current_role": current_role,
        "active_page": "integrations",
        "is_standalone_verifier": False
    })

# --- ROUTE: IOT COLD-CHAIN & VISCERA TELEMETRY (/telemetry) ---
@app.get("/telemetry", response_class=HTMLResponse)
async def telemetry_page(request: Request):
    current_role = get_current_role(request)
    return templates.TemplateResponse("telemetry.html", {
        "request": request,
        "current_role": current_role,
        "active_page": "telemetry",
        "is_standalone_verifier": False
    })

@app.post("/dev/admin-attack")
async def execute_admin_attack_endpoint():
    res = db.simulate_admin_rehash_attack()
    return res

@app.post("/dev/admin-restore")
async def execute_admin_restore_endpoint():
    db.restore_from_admin_attack()
    return {"status": "ok", "message": "Restored clean database state"}

# --- SARVAM AI TRANSLATION API ---
class TranslationRequest(BaseModel):
    text: str
    target_lang: str = "hi"
    source_lang: str = "en"

@app.post("/api/translate")
async def translate_endpoint(data: TranslationRequest):
    res = sarvam.translate_text(data.text, data.target_lang, data.source_lang)
    return res

# --- BLOCKCHAIN ON-CHAIN PROOF API ---
@app.get("/api/blockchain/proof/{record_id}")
async def get_blockchain_proof_endpoint(record_id: int):
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    proof = blockchain.get_blockchain_proof(
        record["id"], record["record_hash"], record["content_hash"],
        record["uploaded_by"], record.get("doctor_nmc_reg", "NMC-2018-84920")
    )
    return proof

# --- DIGILOCKER DOCTOR e-KYC API ---
@app.get("/api/kyc/doctor/{doctor_name}")
async def get_doctor_kyc_endpoint(doctor_name: str):
    return kyc.get_doctor_kyc(doctor_name)

# --- SARVAM AI VOICE DICTATION & STRUCTURING API ---
class VoiceDictationRequest(BaseModel):
    transcript: str
    language_code: str = "hi-IN"

@app.post("/api/sarvam/voice-dictate")
async def sarvam_voice_dictate_endpoint(data: VoiceDictationRequest):
    return sarvam.structure_medical_dictation(data.transcript, data.language_code)

class SarvamKeyRequest(BaseModel):
    api_key: str

@app.post("/api/sarvam/set-key")
async def set_sarvam_key_endpoint(data: SarvamKeyRequest):
    os.environ["SARVAM_API_KEY"] = data.api_key.strip()
    return {"status": "ok", "message": "Sarvam AI API Key configured successfully for live requests!"}

# --- MULTI-ROLE RBAC API (/api/set-role) ---
class RoleChangeRequest(BaseModel):
    role: str

@app.post("/api/set-role")
async def set_role_endpoint(data: RoleChangeRequest, response: Response):
    valid_roles = ["Hospital", "Police", "Court"]
    new_role = data.role if data.role in valid_roles else "Hospital"
    resp = JSONResponse({
        "status": "ok",
        "role": new_role,
        "message": f"Switched active workspace persona to {new_role}"
    })
    resp.set_cookie(key="pramaan_role", value=new_role, max_age=86400 * 30, httponly=False, samesite="lax")
    return resp

# --- IOT COLD-CHAIN & VISCERA BREACH SIMULATOR API ---
class TelemetryBreachRequest(BaseModel):
    sensor_id: str = "M-04"
    temperature: float = 6.2
    reason: str = "Hospital Morgue Compressor Power Interruption"
    case_id: Optional[int] = 1

@app.post("/api/telemetry/simulate-breach")
async def simulate_telemetry_breach_endpoint(data: TelemetryBreachRequest):
    now_iso = datetime.now(timezone.utc).isoformat()
    action_text = f"CRITICAL: IoT Viscera Cold-Chain Breach ({data.temperature}°C > +4.0°C) Alert Triggered [{data.sensor_id}]"
    db.log_audit_event(
        case_id=data.case_id or 1,
        record_id=None,
        action=action_text,
        actor=f"IoT Sentinel Node #{data.sensor_id}",
        role="IoT_Grid",
        created_at=now_iso
    )
    breach_hash = calculate_record_hash("IOT_TELEMETRY_ALERT", f"{data.sensor_id}_{data.temperature}_{data.reason}", "IOT_SENTINEL", now_iso)
    return {
        "status": "alert_logged",
        "sensor_id": data.sensor_id,
        "temperature": data.temperature,
        "is_breached": data.temperature > 4.0,
        "breach_hash": breach_hash,
        "logged_at": now_iso,
        "message": "Thermal breach securely sealed to Case Audit Ledger under Section 63 BSA 2023."
    }

# --- MERKLE AUDIT PROOF API (/api/anchor/merkle-proof/{record_id}) ---
@app.get("/api/anchor/merkle-proof/{record_id}")
async def get_merkle_proof_endpoint(record_id: int):
    record = db.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    case_records = db.get_case_records(record["case_id"])
    hashes = [r["record_hash"] for r in case_records]
    proof_data = generate_merkle_proof(hashes, record["record_hash"])

    return {
        "record_id": record["id"],
        "record_type": record["record_type"],
        "case_id": record["case_id"],
        "record_hash": record["record_hash"],
        "proof": proof_data
    }

# --- SYSTEM HEALTH CHECK API ---
@app.get("/api/system/health")
async def system_health_endpoint():
    stats = db.get_aggregate_stats()
    return {
        "status": "online",
        "platform": "PRAMAAN Medico-Legal Evidence Platform",
        "compliance": "Section 63 BSA 2023 / Section 173 BNSS 2023",
        "smart_contract": blockchain.SMART_CONTRACT_ADDRESS,
        "total_cases": stats["total_cases"],
        "records_sealed": stats["total_records"],
        "integrity_percent": stats["integrity_percent"]
    }
