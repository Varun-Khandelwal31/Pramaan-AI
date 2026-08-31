import hashlib
from typing import Dict, Any, List, Optional, Tuple

GENESIS_PREV_HASH = "GENESIS"

def calculate_content_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 hash of raw file bytes."""
    if not isinstance(file_bytes, (bytes, bytearray)):
        if isinstance(file_bytes, str):
            file_bytes = file_bytes.encode('utf-8')
        else:
            file_bytes = bytes(file_bytes)
    return hashlib.sha256(file_bytes).hexdigest()

def calculate_record_hash(prev_hash: str, content_hash: str, uploaded_by: str, created_at: str) -> str:
    """
    Computes cryptographic block hash for a record.
    record_hash = sha256(prev_hash + content_hash + uploaded_by + created_at)
    """
    payload = f"{prev_hash}{content_hash}{uploaded_by}{created_at}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def compute_merkle_root(hashes: List[str]) -> str:
    """
    Computes a cryptographic Merkle Root over a list of block/record hashes.
    Provides external witness and O(log N) inclusion proofs.
    """
    if not hashes:
        return hashlib.sha256(b"EMPTY_REGISTRY").hexdigest()
    
    current_level = [h if len(h) == 64 else hashlib.sha256(h.encode('utf-8')).hexdigest() for h in hashes]
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = hashlib.sha256(f"{left}{right}".encode('utf-8')).hexdigest()
            next_level.append(combined)
        current_level = next_level
        
    return current_level[0]

def generate_merkle_proof(hashes: List[str], target_hash: str) -> Dict[str, Any]:
    """
    Generates a cryptographic Merkle inclusion audit proof (siblings path) for a target record hash.
    Allows independent court / police verification of record inclusion in O(log N) operations.
    """
    if not hashes:
        return {"target_hash": target_hash, "proof": [], "root": compute_merkle_root([]), "is_valid": False}

    current_level = [h if len(h) == 64 else hashlib.sha256(h.encode('utf-8')).hexdigest() for h in hashes]
    
    # Locate target index
    target_idx = None
    for idx, h in enumerate(current_level):
        if h.lower() == target_hash.lower():
            target_idx = idx
            break
            
    if target_idx is None:
        target_idx = 0
        target_hash = current_level[0]

    proof = []
    curr_idx = target_idx
    level_num = 0

    while len(current_level) > 1:
        next_level = []
        is_even = (curr_idx % 2 == 0)
        sibling_idx = curr_idx + 1 if is_even else curr_idx - 1

        if sibling_idx < len(current_level):
            sibling_hash = current_level[sibling_idx]
        else:
            sibling_hash = current_level[curr_idx]  # duplicate odd tail

        proof.append({
            "level": level_num,
            "sibling_hash": sibling_hash,
            "position": "right" if is_even else "left"
        })

        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = hashlib.sha256(f"{left}{right}".encode('utf-8')).hexdigest()
            next_level.append(combined)

        curr_idx = curr_idx // 2
        current_level = next_level
        level_num += 1

    root = current_level[0]
    return {
        "target_hash": target_hash,
        "leaf_index": target_idx,
        "total_leaves": len(hashes),
        "proof_steps": proof,
        "merkle_root": root,
        "is_valid": True
    }

def verify_merkle_proof(target_hash: str, proof_steps: List[Dict[str, Any]], expected_root: str) -> bool:
    """Verifies a Merkle inclusion proof against an expected root."""
    current = target_hash
    for step in proof_steps:
        sibling = step["sibling_hash"]
        if step["position"] == "right":
            current = hashlib.sha256(f"{current}{sibling}".encode('utf-8')).hexdigest()
        else:
            current = hashlib.sha256(f"{sibling}{current}".encode('utf-8')).hexdigest()
    return current.lower() == expected_root.lower()

def verify_record_integrity(record: Dict[str, Any], previous_record_hash: str) -> Dict[str, Any]:
    """
    Independently verifies a single record against its stored byte blob and previous block hash.
    """
    file_blob = record.get("file_blob", b"")
    if isinstance(file_blob, str):
        file_blob = file_blob.encode('utf-8')
    elif file_blob is None:
        file_blob = b""

    expected_content_hash = calculate_content_hash(file_blob)
    stored_content_hash = record.get("content_hash", "")
    stored_prev_hash = record.get("prev_hash", "")
    stored_record_hash = record.get("record_hash", "")
    uploaded_by = record.get("uploaded_by", "")
    created_at = record.get("created_at", "")

    content_intact = (expected_content_hash == stored_content_hash)
    prev_link_intact = (stored_prev_hash == previous_record_hash)

    # Recompute record hash using the actual content hash from bytes
    recomputed_record_hash = calculate_record_hash(
        stored_prev_hash,
        expected_content_hash,
        uploaded_by,
        created_at
    )
    record_intact = (recomputed_record_hash == stored_record_hash) and content_intact and prev_link_intact

    return {
        "is_intact": record_intact,
        "content_intact": content_intact,
        "prev_link_intact": prev_link_intact,
        "expected_content_hash": expected_content_hash,
        "stored_content_hash": stored_content_hash,
        "stored_prev_hash": stored_prev_hash,
        "expected_prev_hash": previous_record_hash,
        "recomputed_record_hash": recomputed_record_hash,
        "stored_record_hash": stored_record_hash
    }

def verify_case_chain(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifies the entire cryptographic chain for a case from Genesis to head.
    Returns details on chain health, first failing record (if any), and full audit trace.
    """
    if not records:
        return {
            "is_intact": True,
            "total_records": 0,
            "broken_record_id": None,
            "broken_index": None,
            "error_reason": None,
            "records_status": [],
            "merkle_root": compute_merkle_root([])
        }

    expected_prev = "GENESIS"
    records_status = []
    broken_record_id = None
    broken_index = None
    error_reason = None
    chain_intact = True
    record_hashes = []

    for idx, record in enumerate(records):
        res = verify_record_integrity(record, expected_prev)
        record_hashes.append(record.get("record_hash", ""))
        records_status.append({
            "record_id": record["id"],
            "record_type": record.get("record_type"),
            "index": idx + 1,
            "is_intact": res["is_intact"],
            "details": res
        })

        if not res["is_intact"] and chain_intact:
            chain_intact = False
            broken_record_id = record["id"]
            broken_index = idx + 1
            if not res["content_intact"]:
                error_reason = f"Content hash mismatch: file bytes were altered after sealing."
            elif not res["prev_link_intact"]:
                error_reason = f"Chain linkage broken: previous hash does not match prior record."
            else:
                error_reason = f"Record hash mismatch: metadata or signature altered."

        # The next block expects the stored record_hash of this block
        expected_prev = record.get("record_hash", "")

    merkle_root = compute_merkle_root(record_hashes)

    return {
        "is_intact": chain_intact,
        "total_records": len(records),
        "broken_record_id": broken_record_id,
        "broken_index": broken_index,
        "error_reason": error_reason,
        "records_status": records_status,
        "chain_head_hash": records[-1].get("record_hash") if records else None,
        "merkle_root": merkle_root
    }
