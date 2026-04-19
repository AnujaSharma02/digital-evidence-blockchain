# CONTEXT.md — CSE 435 Comprehensive Seminar Project

## Project Identity

- **Course:** CSE 435 – Comprehensive Seminar
- **Title:** Ensuring Digital Evidence Integrity in Cybercrime Investigations Using Blockchain
- **Subtitle:** A Secure and Tamper-Proof Approach for Digital Chain of Custody
- **Student:** Anuja Sharma | Roll No: R422HYA34 | Section: 422HY
- **Deliverable:** 5-slide academic seminar presentation (complete) + optional prototype system

---

## Detailed Summary

### Problem Statement

Cybercrime cases are increasing rapidly worldwide. Digital evidence — logs, emails, files, images, network data — forms the backbone of any cybercrime investigation. However, this evidence is inherently fragile: it is easy to modify, copy, or delete without leaving a visible trace. Traditional evidence management systems are centralized, meaning a single compromised administrator or a single point of failure can corrupt the entire evidence chain. Courts demand proof that evidence has not been tampered with from the moment of collection to the moment of presentation. Current systems cannot reliably provide this guarantee.

### Core Idea

The project proposes using **blockchain technology** to create a tamper-proof, immutable chain of custody for digital evidence. Instead of storing evidence in a central server that can be altered, every piece of evidence is cryptographically fingerprinted (SHA-256 hash) and that fingerprint — along with a timestamp and case ID — is written to a blockchain. The actual evidence file is stored off-chain in secure storage. At any point, anyone with access can re-hash the evidence file and compare it against the on-chain record. If hashes match, the evidence is intact. If they don't, a tampering alert is triggered.

### The 7-Step Working Mechanism

1. **Evidence Collection** — Logs, files, images, and network data are gathered from the crime scene or digital environment.
2. **Digital Fingerprinting (Hash Generation)** — A SHA-256 cryptographic hash is generated for each individual piece of evidence. This hash is unique to that file's exact byte content.
3. **Blockchain Storage (Immutable Record)** — The hash, timestamp, and case ID are written as a transaction to the blockchain. Once written, this record cannot be altered or deleted.
4. **Secure Backup (Off-Chain Storage)** — The original evidence files are stored securely off-chain (e.g., encrypted cloud storage or a forensics lab server). The blockchain does not store the files themselves, only their fingerprints.
5. **Verification (Integrity Check)** — Whenever evidence needs to be verified (before court, during transfer, during review), it is re-hashed and the new hash is compared against the blockchain record.
6. **Verified — Evidence Intact** — If hashes match, the evidence is confirmed unaltered since the moment of collection.
7. **Tampering Detected — Alert** — If hashes do not match, a tampering alert is raised, flagging the evidence as compromised and inadmissible.

### Industry Relevance

This system applies directly to:
- Law enforcement agencies managing cybercrime case files
- Cybercrime investigation units handling digital artifacts
- Digital forensics labs processing and transferring evidence
- Courts and judicial systems verifying admissibility

### Key Benefits

- **Tamper-proof evidence** — blockchain immutability makes post-collection alteration detectable
- **Strong chain of custody** — every access and transfer event can be logged on-chain
- **Improved court admissibility** — cryptographic proof replaces manual paperwork
- **Prevents insider manipulation** — no single administrator can alter records silently
- **Stakeholder trust** — all parties (investigators, lawyers, judges) can independently verify integrity

### Real-World Use Cases

- Cyber fraud investigations (financial transaction logs, phishing emails)
- Data breach forensics (server logs, access records)
- Online harassment and cyberstalking cases (screenshot evidence, message logs)
- Corporate incident response (internal audit trails, malware artifacts)

### Conclusion

Traditional centralized evidence management systems are insufficient for the demands of modern cybercrime investigations. Blockchain — specifically a **consortium blockchain** (a permissioned chain shared among law enforcement agencies, forensics labs, and courts rather than a fully public chain) — provides the immutability, transparency, and distributed trust needed to make digital evidence legally defensible.

### Future Scope

- **Integration with AI-based forensic tools** — AI can assist in automated evidence classification, anomaly detection, and pattern recognition within the evidence corpus
- **Automated evidence tracking** — smart contracts can automate custody transfer logging without manual intervention
- **Privacy-preserving techniques using Zero-Knowledge Proofs (ZKP)** — ZKP allows a party to prove they have valid evidence without revealing the actual content, protecting sensitive data while maintaining verifiability

---

## Project Scope

### What This Project Covers (In Scope)

- Conceptual design of a blockchain-based digital evidence management system
- SHA-256 hashing as the core integrity mechanism
- On-chain storage of evidence metadata (hash + timestamp + case ID)
- Off-chain storage of actual evidence files
- A 7-step workflow from collection to tampering detection
- Consortium blockchain model for legal and law enforcement use
- Industry applicability and real-world use case mapping

### What This Project Does Not Cover (Out of Scope)

- Full smart contract implementation (Solidity / Hyperledger Chaincode)
- A live blockchain network deployment
- Evidence file storage infrastructure design (S3, IPFS, etc.)
- Legal framework compliance per jurisdiction
- Authentication and access control system for investigators
- Frontend UI for investigators to interact with the system

### If Extended to a Prototype (Optional Scope)

If a working prototype is required, the minimal viable scope would be:

1. A Python script that accepts an evidence file and generates its SHA-256 hash
2. A local/testnet blockchain interaction (e.g., Ethereum testnet via Web3.py, or a simulated chain) to store the hash + timestamp + case ID
3. A verification script that re-hashes a file and compares against the stored on-chain record
4. A tampering simulation: modify the file and show the alert trigger

This prototype can be built without a real blockchain deployment using a local Ethereum node (Ganache) or even a simple SQLite-based simulation for demonstration purposes.

---

## Approach

### Phase 1 — Conceptual Clarity (Already Done via Presentation)

The presentation covers this well. The 7-step mechanism is clear and technically sound. No gaps in the conceptual model.

Key concepts to be solid on before any implementation:
- How SHA-256 hashing works and why it is collision-resistant
- Difference between on-chain and off-chain storage and why evidence files should be off-chain
- What a consortium blockchain is vs. public (Ethereum) vs. private (Hyperledger Fabric)
- Why ZKP is relevant for future privacy and what it means in simple terms

### Phase 2 — If Building a Prototype

**Recommended stack:**
- Python for all scripting (hashlib for SHA-256, web3.py for blockchain interaction)
- Ganache (local Ethereum testnet) for blockchain simulation without real network costs
- SQLite as a fallback if blockchain setup is out of scope for the assignment
- A simple CLI interface — no frontend needed for a seminar prototype

**Execution order:**
1. Write `hash_evidence.py` — takes a file path, returns SHA-256 hash
2. Write `store_record.py` — takes hash + case_id + timestamp, writes to chain/db
3. Write `verify_evidence.py` — takes a file path + case_id, re-hashes, compares, returns INTACT or TAMPERED
4. Write `simulate_tampering.py` — modifies a file slightly, runs verify, shows alert
5. Demo script that runs the full 7-step flow end to end

### Phase 3 — Presentation / Defense Preparation

Likely questions from evaluators:
- *Why blockchain and not a simple database with audit logs?* — Answer: database logs can be altered by the DBA; blockchain entries are immutable by design
- *Why consortium blockchain specifically?* — Answer: public chains are slow/expensive and expose case data; private chains sacrifice decentralization; consortium gives trusted multi-party verification without full exposure
- *What happens if the blockchain node itself is compromised?* — Answer: consortium chains have multiple nodes; majority consensus means no single node can alter history
- *How is off-chain storage secured?* — Answer: encryption + access control; the blockchain only guarantees integrity of what was stored, not the storage medium itself
- *What is ZKP and how does it apply here?* — Answer: ZKP lets a party prove "I have the original file" without showing the file, useful when evidence is sensitive (e.g., CSAM, trade secrets)

---

## Key Technical Terms Reference

| Term | Meaning in This Project |
|---|---|
| SHA-256 | Cryptographic hash function producing a 256-bit fingerprint of any file |
| Chain of Custody | Documented trail showing who handled evidence, when, and how |
| Consortium Blockchain | Permissioned blockchain operated by a fixed group of known organizations |
| On-chain | Data written directly into the blockchain ledger (hashes, metadata) |
| Off-chain | Data stored outside the blockchain but referenced by it (actual evidence files) |
| Immutability | Property of blockchain where written records cannot be altered or deleted |
| ZKP (Zero-Knowledge Proof) | Cryptographic method to prove knowledge of data without revealing the data |
| Smart Contract | Self-executing code on a blockchain that automates actions when conditions are met |
| Tamper Detection | Detecting that a file has changed by comparing current hash to stored hash |

---

## Files in This Project

| File | Purpose |
|---|---|
| `CONTEXT.md` | This file — full project summary, scope, and approach |
| `CSE_435_Seminar.pptx` | The 5-slide seminar presentation (complete) |
| `hash_evidence.py` | (If prototype) SHA-256 hashing script |
| `store_record.py` | (If prototype) Blockchain/DB record storage |
| `verify_evidence.py` | (If prototype) Integrity verification script |
| `simulate_tampering.py` | (If prototype) Tamper simulation and alert demo |
