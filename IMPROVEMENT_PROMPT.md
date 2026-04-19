# IMPROVEMENT_PROMPT.md — Blockchain-Based Digital Evidence Integrity System

## Project Context

I have a working CLI-based Python prototype for a college seminar project titled
"Ensuring Digital Evidence Integrity in Cybercrime Investigations Using Blockchain."

The project demonstrates a 7-step mechanism:
1. Evidence collection
2. SHA-256 hashing (digital fingerprinting)
3. Immutable ledger storage
4. Off-chain vaulting
5. Re-hashing on verify
6. Integrity confirmation
7. Tamper detection alert

The current prototype is CLI-only, uses SQLite locally, stores files locally,
and has no web interface. The goal is to evolve it into a presentable, deployable
full-stack web application for a seminar demo and defense.

---

## Existing Codebase Structure

```
D:\mini\
├── CONTEXT.md
├── PLAN.md
├── README.md
├── requirements.txt
├── src/
│   ├── hash_evidence.py         # SHA-256 hashing logic
│   ├── store_record.py          # write hash to ledger
│   ├── verify_evidence.py       # re-hash + compare
│   ├── simulate_tampering.py    # tamper demo
│   ├── chain_client.py          # SQLite/Web3 abstraction
│   ├── vault.py                 # local file storage (to be replaced)
│   └── config.py
├── contracts/
│   └── EvidenceLedger.sol
├── scripts/
│   ├── deploy_contract.py
│   └── demo.py
├── tests/
├── evidence_vault/
└── data/
    └── ledger.sqlite
```

Important: Do not rewrite the core hashing, verification, or tamper logic.
Preserve all existing src/ modules and wrap them behind API endpoints.

---

## Target Architecture

```
┌─────────────────────────────────────────┐
│           React + Vite Frontend          │
│              (Vercel)                    │
│   [Register] [Verify] [Tamper Demo]      │
└───────────────────┬─────────────────────┘
                    │ HTTP
┌───────────────────▼─────────────────────┐
│           FastAPI Backend                │
│              (Render)                    │
│  /evidence/register                      │
│  /evidence/verify                        │
│  /evidence/tamper                        │
│  /evidence/list                          │
│  /evidence/{case_id}                     │
│  /health                                 │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│              Supabase                    │
│         (PostgreSQL - hosted)            │
│   records: case_id, file_hash,           │
│   original_filename, timestamp           │
└─────────────────────────────────────────┘
```

Stack:
- Backend: FastAPI (Python 3.11+), deployed on Render
- Frontend: React + Vite, deployed on Vercel (built separately after backend)
- Database: Supabase (hosted PostgreSQL) — replaces local SQLite
- No file storage — only hash and metadata are persisted
- No auth layer — this is a seminar demo

---

## 1. Supabase Database Setup

Create this table in Supabase:

```sql
CREATE TABLE records (
    case_id           TEXT PRIMARY KEY,
    file_hash         TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    timestamp         TIMESTAMPTZ DEFAULT NOW(),
    submitter         TEXT DEFAULT 'demo-user'
);
```

Use supabase-py to interact from FastAPI.

Environment variables:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
```

---

## 2. Case ID Generation — src/case_id.py (NEW)

Rules:
- User provides a readable name e.g. "cyber-fraud" or "email evidence"
- System appends hyphen + 8-character uppercase alphanumeric random key
- Format: {sanitized_case_name}-{8_CHAR_KEY}
- Sanitize: lowercase, spaces to hyphens, strip special chars except hyphens, max 40 chars
- Check uniqueness against Supabase before returning; retry up to 5 times on collision

Examples:
```
"Cyber Fraud Case"  ->  "cyber-fraud-case-A3F8B21C"
"email evidence"    ->  "email-evidence-F92D4AB1"
"CASE 2026!!"       ->  "case-2026-7BC3E1F0"
```

---

## 3. FastAPI Endpoints — main.py (NEW)

### POST /evidence/register
- Accepts: multipart form — file (UploadFile) + case_name (str)
- Flow: read file bytes -> SHA-256 hash -> generate case_id -> insert to Supabase -> return
- Response:
```json
{
  "case_id": "cyber-fraud-A3F8B21C",
  "file_hash": "a3f5...",
  "original_filename": "email_log.eml",
  "timestamp": "2026-04-19T10:30:00Z",
  "message": "Evidence registered. Save your case_id to verify later."
}
```

### POST /evidence/verify
- Accepts: multipart form — file (UploadFile) + case_id (str)
- Flow: hash uploaded file -> fetch stored hash from Supabase -> compare
- Response:
```json
{
  "case_id": "cyber-fraud-A3F8B21C",
  "status": "INTACT",
  "submitted_hash": "a3f5...",
  "stored_hash": "a3f5...",
  "original_filename": "email_log.eml",
  "registered_at": "2026-04-19T10:30:00Z"
}
```
- status: "INTACT" or "TAMPERED"
- 404 if case_id not found

### POST /evidence/tamper
- Accepts: multipart form — file (UploadFile)
- Stateless — does NOT touch the database at all
- Flow: read file -> hash original -> append 8-16 random bytes -> hash corrupted -> return corrupted file
- Response: StreamingResponse (downloadable corrupted file)
- Headers on response:
  - X-Original-Hash: hash before corruption
  - X-Tampered-Hash: hash after corruption
  - X-Original-Filename: original filename
  - Content-Disposition: attachment; filename="tampered_{original_filename}"
- Purpose: user downloads corrupted file, submits to /verify to demo tamper detection

### GET /evidence/{case_id}
- Returns full metadata for one case from Supabase
- 404 if not found

### GET /evidence/list
- Returns all records ordered by timestamp DESC
- Response includes total count and array of {case_id, original_filename, timestamp}

### GET /health
- Returns {status: "ok", backend: "supabase", timestamp: "..."}

---

## 4. Updated Project Structure

```
D:\mini\
├── CONTEXT.md
├── PLAN.md
├── IMPROVEMENT_PROMPT.md        # this file
├── README.md
├── requirements.txt             # updated
├── main.py                      # FastAPI entry point (NEW)
├── .env                         # gitignored
│
├── src/
│   ├── __init__.py
│   ├── hash_evidence.py         # UNCHANGED
│   ├── store_record.py          # UNCHANGED
│   ├── verify_evidence.py       # UNCHANGED
│   ├── simulate_tampering.py    # UNCHANGED
│   ├── chain_client.py          # updated for Supabase
│   ├── vault.py                 # kept for CLI only
│   ├── case_id.py               # NEW
│   ├── db.py                    # NEW — Supabase singleton
│   └── config.py                # updated for Supabase env vars
│
├── contracts/
│   └── EvidenceLedger.sol       # UNCHANGED
│
├── scripts/
│   ├── deploy_contract.py       # UNCHANGED
│   └── demo.py                  # UNCHANGED — CLI stays on SQLite
│
├── tests/
│   ├── test_hash.py             # UNCHANGED
│   ├── test_case_id.py          # NEW
│   ├── test_endpoints.py        # NEW
│   └── test_tamper.py           # UNCHANGED
│
└── evidence_vault/              # kept for CLI only
```

---

## 5. Updated Dependencies

Add to requirements.txt:
```
fastapi==0.111.0
uvicorn==0.30.1
python-multipart==0.0.9
supabase==2.4.6
python-dotenv==1.0.1
```

Keep all existing deps unchanged.

---

## 6. CORS

```python
origins = [
    "http://localhost:5173",
    os.getenv("FRONTEND_URL", ""),
]
```

Add FRONTEND_URL as env var on Render after frontend is deployed.

---

## 7. CLI Demo Stays Intact

scripts/demo.py and all CLI commands must continue working on SQLite.
Two independent paths after this improvement:
- CLI path: SQLite + local vault (unchanged)
- API path: Supabase + FastAPI (new)

---

## 8. Frontend Spec (build after backend is deployed on Render)

Single-page React + Vite. Three sections, no routing.

### Register Section
- Inputs: case name text field + file upload
- Button: "Register Evidence"
- On success: show case_id in highlighted box with copy button, hash, filename, timestamp
- Message: "Save this Case ID. You will need it to verify this evidence later."

### Verify Section
- Inputs: case_id text field + file upload
- Button: "Verify Evidence"
- INTACT: green banner, both hashes shown (matching)
- TAMPERED: red alert banner, both hashes shown (mismatch highlighted)
- NOT FOUND: yellow warning

### Tamper Demo Section
- Input: file upload only
- Button: "Corrupt This File"
- On result: show original hash and tampered hash side by side, auto-download corrupted file
- Instruction: "Download the corrupted file, then submit it to Verify
  with a registered case_id to see tamper detection in action."

### Evidence List (bottom)
- Loads on mount via GET /evidence/list
- Table: Case ID | Filename | Registered At
- Refreshes after each register

Design: minimal, color-coded (green/red/yellow), single page, no login.
Env var: VITE_API_URL = Render backend URL

---

## 9. Deployment

Backend on Render:
- Build: pip install -r requirements.txt
- Start: uvicorn main:app --host 0.0.0.0 --port $PORT
- Env vars: SUPABASE_URL, SUPABASE_KEY, FRONTEND_URL

Frontend on Vercel:
- Preset: Vite
- Env var: VITE_API_URL = Render backend URL

---

## 10. Seminar Demo Flow (4 minutes)

1. Open frontend — show the three-section UI (30s)
2. Register — upload a sample file, type case name "demo-case", register.
   Show generated case_id and hash. (45s)
3. Open Supabase dashboard — show the record inserted in real time.
   This is the "immutable ledger" visual proof. (30s)
4. Verify intact — same file + case_id -> green INTACT banner. (30s)
5. Tamper — upload same file to Tamper section, corrupt it.
   Show before/after hashes. Download corrupted file. (30s)
6. Verify tampered — corrupted file + same case_id -> red TAMPERED banner. (30s)
7. Defense Q&A — refer to CONTEXT.md Phase 3. (60s)

---

## 11. Out of Scope — Do Not Build

- User authentication or login
- Role-based access control
- Any file storage (Cloudinary, IPFS, S3) — hash and metadata only
- Multi-node blockchain deployment
- ZKP implementation
- Multiple evidence files per case_id
- Case deletion or update endpoints
- Multi-page frontend

Mention all as future scope during defense.

---

## 12. Pre-Start Checklist

Before writing any code:
- [ ] Supabase project created, table created with schema above, credentials in hand
- [ ] Render account ready
- [ ] Vercel account ready
- [ ] Confirm existing CLI demo (scripts/demo.py) still runs locally before touching anything
- [ ] Confirmed: CLI stays on SQLite, API uses Supabase — two separate paths
