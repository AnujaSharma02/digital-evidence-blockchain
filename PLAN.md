# PLAN.md — Implementation Plan

**Project:** Blockchain-Based Digital Evidence Integrity System
**Scope:** Working prototype demonstrating the 7-step mechanism end-to-end
**Target:** Seminar demo + defense-ready artifact
**Stack:** Python 3.11+, Web3.py, Ganache (local Ethereum), Solidity (minimal), SQLite (fallback), CLI only

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Orchestrator                        │
│                         (demo.py)                            │
└───────────────┬─────────────────────┬───────────────────────┘
                │                     │
        ┌───────▼────────┐    ┌──────▼──────┐
        │   Evidence     │    │   Chain     │
        │   Handler      │    │   Client    │
        │ (hash + store) │    │ (web3 / db) │
        └───────┬────────┘    └──────┬──────┘
                │                     │
       ┌────────▼─────────┐   ┌──────▼──────────┐
       │  Off-chain Store │   │  Ganache / DB   │
       │  ./evidence_vault│   │  EvidenceLedger │
       └──────────────────┘   └─────────────────┘
```

**Design decisions:**
- **Dual backend**: real blockchain (Ganache + Solidity) AND SQLite fallback behind one `ChainClient` interface. Demo works even if Ganache is not available.
- **Off-chain vault**: local directory `./evidence_vault/<case_id>/<filename>` — simulates secure storage.
- **No frontend**: CLI is sufficient for a seminar. Output formatted for screenshots.
- **No auth layer**: explicitly out of scope per CONTEXT.md §Scope.

---

## 2. Repository Layout

```
D:\mini\
├── CONTEXT.md                       # already exists
├── PLAN.md                          # this file
├── README.md                        # quickstart for evaluator
├── requirements.txt                 # pinned deps
├── CSE_435_Seminar.pptx             # presentation (to be added)
│
├── src/
│   ├── __init__.py
│   ├── hash_evidence.py             # Step 2: SHA-256 fingerprinting
│   ├── store_record.py              # Step 3: write hash to chain
│   ├── verify_evidence.py           # Step 5/6/7: re-hash + compare
│   ├── simulate_tampering.py        # tamper demo
│   ├── chain_client.py              # backend abstraction (web3 | sqlite)
│   ├── vault.py                     # off-chain file storage helper
│   └── config.py                    # constants, paths, ganache url
│
├── contracts/
│   └── EvidenceLedger.sol           # minimal smart contract
│
├── scripts/
│   ├── deploy_contract.py           # compiles + deploys to Ganache
│   └── demo.py                      # runs full 7-step flow
│
├── tests/
│   ├── test_hash.py
│   ├── test_store_verify.py
│   └── test_tamper.py
│
├── evidence_vault/                  # off-chain storage (gitignored)
└── data/
    └── ledger.sqlite                # fallback backend (gitignored)
```

---

## 3. Smart Contract (`contracts/EvidenceLedger.sol`)

Minimal Solidity contract. One mapping, two functions, one event.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceLedger {
    struct Record {
        bytes32 fileHash;
        uint256 timestamp;
        address submitter;
        bool exists;
    }

    mapping(string => Record) private records;         // caseId => Record
    event EvidenceStored(string caseId, bytes32 fileHash, uint256 timestamp);

    function storeEvidence(string calldata caseId, bytes32 fileHash) external {
        require(!records[caseId].exists, "Case already recorded");
        records[caseId] = Record(fileHash, block.timestamp, msg.sender, true);
        emit EvidenceStored(caseId, fileHash, block.timestamp);
    }

    function getEvidence(string calldata caseId)
        external view returns (bytes32, uint256, address)
    {
        require(records[caseId].exists, "No record");
        Record memory r = records[caseId];
        return (r.fileHash, r.timestamp, r.submitter);
    }
}
```

**Why this shape:**
- Immutable on write (`require(!exists)`), matches "cannot be altered" claim.
- Event emission gives an auditable log for demos.
- `caseId` as string for human readability in screenshots.

---

## 4. Module Specifications

### 4.1 `src/hash_evidence.py`
- `sha256_file(path: Path) -> str` — streams in 64KB chunks, returns hex digest.
- CLI: `python -m src.hash_evidence <file>` prints hash.
- Rationale for streaming: evidence files can be large (PCAPs, disk images).

### 4.2 `src/chain_client.py`
Abstract interface:
```python
class ChainClient(Protocol):
    def store(self, case_id: str, file_hash: str) -> dict: ...
    def fetch(self, case_id: str) -> dict | None: ...
```
Two implementations:
- `Web3Client` — connects to Ganache at `http://127.0.0.1:7545`, calls contract.
- `SqliteClient` — table `records(case_id PK, file_hash, ts, submitter)`.

`get_client()` returns Web3Client if Ganache reachable, else SqliteClient. Log the backend at startup so the demo is transparent.

### 4.3 `src/store_record.py`
- Inputs: file path, case_id.
- Flow: hash file → copy to vault → call `chain.store()` → print tx/record id.
- Returns dict with `{case_id, hash, timestamp, backend, tx_hash}`.

### 4.4 `src/verify_evidence.py`
- Inputs: file path, case_id.
- Flow: re-hash current file at vault → fetch on-chain record → compare.
- Returns `INTACT` or `TAMPERED` with the two hashes for visual diff.
- Exit code 0 if intact, 2 if tampered (useful for CI demo).

### 4.5 `src/simulate_tampering.py`
- Appends a single byte to a vaulted file, runs verify, prints the alert banner.
- Shows the "before hash" vs "after hash" clearly — this is the screenshot slide.

### 4.6 `src/vault.py`
- `store_file(case_id, src_path) -> vault_path`
- `read_file(case_id) -> bytes`
- Simple, no encryption (out of scope); add a TODO for AES-GCM as future work.

### 4.7 `scripts/demo.py`
Runs all 7 steps in order with labeled output:
```
[Step 1] Collected: ./samples/email.eml
[Step 2] SHA-256:  a3f5...
[Step 3] On-chain: tx 0xabc... (Ganache)
[Step 4] Vaulted:  ./evidence_vault/CASE-001/email.eml
[Step 5] Verify... re-hashed
[Step 6] ✓ INTACT
--- simulating tampering ---
[Step 7] ✗ TAMPERING DETECTED
```

---

## 5. Build Order (execution sequence)

| # | Task | Deliverable | Est. |
|---|---|---|---|
| 1 | `requirements.txt`, venv, `.gitignore` | clean env | 15m |
| 2 | `config.py`, `vault.py`, `hash_evidence.py` + tests | hashing works | 30m |
| 3 | `SqliteClient` (fallback first — always works) + tests | store/fetch works offline | 45m |
| 4 | `EvidenceLedger.sol` + `scripts/deploy_contract.py` | deployed contract address | 60m |
| 5 | `Web3Client` + integration test against Ganache | real chain path works | 60m |
| 6 | `store_record.py`, `verify_evidence.py`, `simulate_tampering.py` | 7-step primitives | 45m |
| 7 | `scripts/demo.py` end-to-end | screenshottable demo | 30m |
| 8 | `README.md` with run instructions | evaluator can reproduce | 20m |
| 9 | Polish output (colors, banners), capture screenshots | presentation assets | 30m |

Total: ~5.5 hours of focused work. Fallback-first ordering means you have a working demo after step 3 even if Ganache fails.

---

## 6. Dependencies (`requirements.txt`)

```
web3==6.20.0
py-solc-x==2.0.3
eth-account==0.11.0
pytest==8.3.3
```
Everything else (`hashlib`, `sqlite3`, `pathlib`) is stdlib.

Ganache: install standalone GUI OR `ganache-cli` via npm. Document both in README.

---

## 7. Testing Strategy

- **Unit**: hash determinism, hash sensitivity (1-byte change → different hash), sqlite round-trip.
- **Integration**: deploy contract to Ganache in `conftest.py`, run store → verify on real chain.
- **Tamper**: byte-modify a vaulted file, assert verify returns TAMPERED.
- **Idempotency**: storing same case_id twice must revert/error.

Target: ~15 tests, all passing in under 10s (Ganache test spawns a fresh chain per session).

---

## 8. Demo Script for Viva / Seminar

1. Show `CONTEXT.md` — conceptual grounding (30s).
2. Run `python scripts/demo.py` — live 7 steps (90s).
3. Open Ganache UI, show the tx in the block list (30s).
4. Run `python -m src.simulate_tampering CASE-001` — show red alert (30s).
5. Answer defense questions from CONTEXT.md §Phase 3.

Total demo: ~3 min, fits inside a seminar Q&A slot.

---

## 9. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Ganache unavailable on eval machine | Med | SQLite fallback always works; demo script picks automatically |
| solc version mismatch | Med | `py-solc-x` pulls specific version (`0.8.20`) on first run |
| Hash collision concern from evaluator | Low | Prepared answer: SHA-256 collision resistance is ~2^128, infeasible |
| "Why not just git?" question | Low | Prepared answer: git is centralized, history is rewritable by maintainer |
| Out-of-scope creep (auth, IPFS) | High | Keep scope to what CONTEXT.md §In-Scope lists; log extras as future work |

---

## 10. Explicitly Out of Scope (do not build)

Per CONTEXT.md §Out-of-Scope — do not start these, even if time permits:
- User authentication / role-based access
- IPFS or S3 integration
- Web frontend or dashboard
- Multi-node consortium deployment
- Jurisdiction-specific legal compliance layer
- ZKP implementation (mention only as future scope)

Any of these can become a follow-up project; conflating them with this prototype will blow the timeline.

---

## 11. Open Questions Before Starting

1. Is the PPT already built, or does this plan need to include slide production? (CONTEXT says complete.)
2. Is a real Ganache demo required, or is the SQLite fallback acceptable to the evaluator?
3. Is the prototype mandatory, optional, or bonus?

Answers to these shape whether section 4.2's Web3Client is priority P0 or P1.
