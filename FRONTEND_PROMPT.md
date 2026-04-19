# FRONTEND_PROMPT.md — Blockchain Evidence Integrity System Frontend

## Context

This is a single-page frontend for a seminar demo project. The backend is a
FastAPI app deployed on Render. The frontend is a single HTML file with vanilla
JS and inline CSS — no framework, no build step, no npm.

The page has three functional sections and one optional data section.
It calls the FastAPI backend via fetch(). The backend URL is hardcoded as a
variable at the top of the script for easy swapping between local and production.

---

## Deliverable

One file: index.html
Deploy to Vercel by dragging and dropping the file. No build config needed.

---

## Backend API Reference

Base URL variable at top of script:
```js
const API_URL = "http://localhost:8000"; // swap to Render URL for production
```

Endpoints used:
- POST /evidence/register — multipart form: file + case_name
- POST /evidence/verify   — multipart form: file + case_id
- POST /evidence/tamper   — multipart form: file (returns corrupted file download)
- GET  /evidence/list     — returns { total, records: [{case_id, original_filename, timestamp}] }

---

## Page Layout

Single scrollable page. Top to bottom:

1. Header — project title
2. Register Section
3. Verify Section
4. Tamper Demo Section
5. Evidence List Section

No navigation, no routing, no sidebar.

---

## Design

- Background: #0d0d0d (near black)
- Card/section background: #1a1a1a
- Text: #f0f0f0
- Accent/button color: #2563eb (blue)
- Success color: #16a34a (green)
- Error/tampered color: #dc2626 (red)
- Warning color: #d97706 (yellow/amber)
- Border radius: 8px on cards
- Font: system-ui, sans-serif
- Max page width: 860px, centered
- Clean spacing — sections clearly separated

Buttons:
- Solid blue background, white text, slightly rounded
- Hover: slightly lighter blue
- Disabled state while loading: grey, cursor not-allowed

Result boxes:
- INTACT: green border + green background tint, show both hashes
- TAMPERED: red border + red background tint, show both hashes with mismatch highlighted
- NOT FOUND: amber border + amber background tint

Keep it minimal. No animations, no gradients, no icons needed.

---

## Section Specifications

### Header
```
Blockchain-Based Digital Evidence Integrity System
CSE 435 – Comprehensive Seminar Demo
```
Small subtitle text. No logo needed.

---

### Section 1 — Register Evidence

Title: "Register Evidence"
Short description: "Upload a file and give it a case name. The system generates
a unique Case ID and records its SHA-256 fingerprint."

Inputs:
- Text field: placeholder "Enter case name (e.g. cyber-fraud)"
- File picker: "Choose file"
- Button: "Register Evidence"

On loading: button shows "Registering..." and is disabled

On success response:
```json
{
  "case_id": "cyber-fraud-A3F8B21C",
  "file_hash": "a3f5...",
  "original_filename": "email.eml",
  "timestamp": "2026-04-19T10:30:00Z",
  "message": "..."
}
```
Show a result box with:
- "Evidence Registered Successfully" heading
- Case ID in large bold text with a Copy button next to it
- Below that: Hash, Filename, Timestamp in smaller text
- Bold note: "Save this Case ID. You will need it to verify this evidence later."

On error: show red error box with the error message from API.

---

### Section 2 — Verify Evidence

Title: "Verify Evidence"
Short description: "Upload the original file and enter its Case ID to check
if it has been tampered with."

Inputs:
- Text field: placeholder "Enter Case ID (e.g. cyber-fraud-A3F8B21C)"
- File picker: "Choose file"
- Button: "Verify Evidence"

On loading: button shows "Verifying..." and is disabled

On INTACT response:
- Green result box
- Large "✓ INTACT" heading
- "This evidence has not been tampered with."
- Show stored hash and submitted hash (they match — display both)

On TAMPERED response:
- Red result box
- Large "✗ TAMPERED" heading
- "Warning: This evidence has been modified."
- Show stored hash and submitted hash side by side
- Both hashes visible so evaluator can see they differ

On 404 (not found):
- Amber result box
- "Case ID not found" with the case_id that was searched

On other error: red error box with message.

---

### Section 3 — Tamper Demo

Title: "Tamper Demo"
Short description: "Upload any file to corrupt it. Download the corrupted
version, then submit it to Verify to see tamper detection in action."

Input:
- File picker: "Choose file to corrupt"
- Button: "Corrupt This File"

On loading: button shows "Corrupting..." and is disabled

On success:
- The corrupted file auto-downloads (use a hidden anchor trick with blob URL)
- Show a result box with:
  - "File Corrupted — Download Started"
  - Original Hash (from X-Original-Hash response header)
  - Tampered Hash (from X-Tampered-Hash response header)
  - Instruction text: "Now go to the Verify section, enter a registered Case ID,
    and upload the downloaded corrupted file to see the TAMPERED result."

Note: the tamper endpoint returns the corrupted file as a blob download.
Read the response as blob, create an object URL, trigger download via
a temporary <a> element. Read headers BEFORE consuming the body as blob.

```js
const originalHash = response.headers.get("X-Original-Hash");
const tamperedHash = response.headers.get("X-Tampered-Hash");
const originalFilename = response.headers.get("X-Original-Filename");
const blob = await response.blob();
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = "tampered_" + originalFilename;
a.click();
URL.revokeObjectURL(url);
```

On error: red error box with message.

---

### Section 4 — Evidence List

Title: "Registered Evidence"
Button: "Refresh List" — clicking this calls GET /evidence/list and updates the table

On load: table is empty with text "Click Refresh to load registered evidence."
After refresh: show a simple table:

| Case ID | Filename | Registered At |
|---|---|---|
| cyber-fraud-A3F8B21C | email.eml | 19 Apr 2026, 10:30 AM |

- Format timestamp to readable local date string
- If no records: show "No evidence registered yet."
- Show total count above the table: "Total records: 12"
- Table styling: subtle borders, alternating row shading (#1a1a1a and #222)

---

## JavaScript Structure

Keep all JS in a single <script> tag at the bottom of the body.

Structure:
```
const API_URL = "http://localhost:8000";

// Utility: show result box
function showResult(containerId, type, html) { ... }
// type: "success" | "error" | "tampered" | "warning"

// Utility: format timestamp
function formatDate(ts) { ... }

// Register handler
document.getElementById("register-form")
  .addEventListener("submit", async (e) => { ... });

// Verify handler
document.getElementById("verify-form")
  .addEventListener("submit", async (e) => { ... });

// Tamper handler
document.getElementById("tamper-form")
  .addEventListener("submit", async (e) => { ... });

// Evidence list refresh
document.getElementById("refresh-list")
  .addEventListener("click", async () => { ... });
```

---

## Error Handling

All fetch calls wrapped in try/catch.
- Network error (API unreachable): "Could not connect to the server. Make sure the backend is running."
- Non-200 response: parse the JSON error body and show the detail field
- Always re-enable the button and reset its text after success or error

---

## Deployment Note

At the top of the script, one variable controls the backend URL:
```js
const API_URL = "http://localhost:8000";
```

For production, change this to the Render backend URL before deploying to Vercel.
Add a comment above it:
```js
// Change this to your Render backend URL for production
// e.g. const API_URL = "https://your-app.onrender.com";
const API_URL = "http://localhost:8000";
```

To deploy on Vercel: drag and drop index.html into vercel.com/new. Done.

---

## What NOT to Include

- No npm, no package.json, no node_modules
- No React, Vue, or any framework
- No external CSS libraries (no Bootstrap, no Tailwind CDN)
- No authentication or login UI
- No multiple pages or routing
- No animations or transitions
- No dark/light mode toggle
