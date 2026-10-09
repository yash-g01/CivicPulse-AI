### Sprint Master Schedule (48-Hour Execution Track)

| Time Window | Milestone | Core Deliverables & Targets | Risk / Fallback Gate |
| --- | --- | --- | --- |
| **Hours 00 – 04** | **Phase 1: Bedrock Multimodal Core** | AWS CLI config, Bedrock Converse API scripts for triage & audit. | Validate model invocation directly via terminal; zero UI.|
| **Hours 04 – 08** | **Phase 2: Authority Routing & DynamoDB** | Single-table schema (`CivicPulseTable`), OSM geocoding, authority cache.| Verify sub-50ms cache hits for PMC/BBMP/BMC.|
| **Hours 08 – 14** | **Phase 3: FastAPI Backend Services** | API router (`/reports`, `/tickets`, `/submit-otp`, `/simulate-resolution`).| Test multipart file uploads and S3 presigned URL generation.|
| **Hours 14 – 20** | **Phase 4: Playwright Worker & Mock Fallback** | Headed browser runner, OTP polling state machine, `/mock-pmc-portal`.| Toggle `PORTAL_MODE=mock` if live PMC gateway latency > 5s.|
| **Hours 20 – 30** | **Phase 5: Beacon-Grade UI Assembly** | v0/Lovable layout generation, Vite/Tailwind scaffolding, Web Share dispatch.| Confirm dual-pane telemetry stream and OTP modal open on state change.|
| **Hours 30 – 38** | **Phase 6: Ghost-Resolution Auditor Loop** | Forensic comparison panel, Bedrock visual diff, status transition triggers.| Verify fraud banner turns rose and reopens ticket with audit notes.|
| **Hours 38 – 44** | **Phase 7: End-to-End Dry Run & Polish** | Full user flow test: Snap $\rightarrow$ Route $\rightarrow$ File $\rightarrow$ OTP $\rightarrow$ Audit.| Eliminate unhandled promise rejections and console errors. |
| **Hours 44 – 48** | **Phase 8: Pitch Video & Submission** | Screen recording (30s problem / 90s demo / 60s AWS architecture), Devpost submission.| Ensure live URL or demo recording link renders without permission blocks. |

---

### Step-by-Step Technical Execution Plan

```
                    ┌────────────────────────────────────────────────────────┐
                    │               CIVICPULSE BUILD PIPELINE                │
                    └────────────────────────────────────────────────────────┘
                                                 │
       ┌───────────────────┬─────────────────────┼─────────────────────┬───────────────────┐
       ▼                   ▼                     ▼                     ▼                   ▼
 [1. Bedrock Core]   [2. Geo Routing]     [3. Playwright]       [4. Beacon UI]      [5. Ghost Audit]
  • Triage engine     • Nominatim OSM      • Headed worker       • Split deck        • Visual diff
  • Audit engine      • DynamoDB Cache     • OTP polling loop    • Thought stream    • SLA escalation
  • CLI smoke tests   • S3 Presigned URLs  • Mock failover       • Native WebShare   • Ticket reopen

```

#### Milestone 1: Environment Setup & Bedrock CLI Core (Hours 00 – 04)

1. **Repository Setup:**
* Initialize a monorepo structure with `/backend` (Python 3.11+) and `/frontend` (Vite + React + TypeScript).


* Set up virtual environment and install core backend dependencies:
```bash
pip install fastapi uvicorn boto3 pydantic pydantic-settings python-multipart pillow httpx playwright
playwright install chromium

```




2. **Bedrock Multimodal Scripts:**
* Create `backend/app/config.py` loading `AWS_REGION` (default `us-east-1`), `BEDROCK_MODEL_ID` (`anthropic.claude-3-5-sonnet-20241022-v2:0`), `DYNAMODB_TABLE`, and `S3_BUCKET`.


* Create `backend/app/services/triage_service.py` to parse waste categories, score severity (1–5), extract landmark context, and generate formal complaint text using the Bedrock Converse API.


* Create `backend/app/services/audit_service.py` to accept two image byte streams ("Before" vs. "After") and output raw JSON containing `is_same_scene`, `debris_cleared`, and `fraud_detected`.




3. **Verification Criterion:** Run CLI smoke tests passing local sample images directly to Bedrock to confirm JSON parsing without markdown fences:


```bash
python -m app.services.triage_service --test-image tests/sample_dump.jpg

```



#### Milestone 2: Authority Routing, Geo Resolution & DynamoDB Store (Hours 04 – 08)

1. **DynamoDB Single-Table Schema:**
* Create `CivicPulseTable` in AWS Console or via AWS CLI:


* Primary Key: `PK` (String), Sort Key: `SK` (String).


* Global Secondary Index: `GSI1_PK` (Partition Key), `GSI1_SK` (Sort Key).




* Implement `backend/app/core/dynamodb.py` with methods: `save_ticket()`, `get_ticket()`, `update_ticket_status()`, `get_authority_cache()`, and `save_authority_cache()`.




2. **Geo Routing Service:**
* Implement `backend/app/services/geo_router.py` using OpenStreetMap Nominatim for reverse geocoding `(lat, lng)` into administrative districts.


* Build the hybrid resolver: check DynamoDB `AUTHORITY#<city>` cache first; fall back to the built-in dictionary (PMC, PCMC, BMC, BBMP); fall back to web search if unindexed.




3. **S3 Evidence Helpers:**
* Implement `backend/app/core/s3.py` for uploading raw uploads and returning presigned GET URLs with a 7-day TTL for official statutory notifications.




4. **Verification Criterion:** Run a script with coordinates `18.5204, 73.8567` (Pune) and confirm that `geo_router.py` returns `complaint.pmc.gov.in` and `feedback@punecorporation.org` in under 50ms.



#### Milestone 3: FastAPI Routing Engine (Hours 08 – 14)

1. **API Endpoints (`backend/app/api/routes.py`):**
* `POST /api/v1/reports`: Accepts `image`, `lat`, `lng`, and `user_phone`. Executes Bedrock triage and geo-routing concurrently, saves evidence to S3, writes state `QUEUED_FOR_FILING` to DynamoDB, and launches the background Playwright worker.


* `GET /api/v1/tickets/{ticket_id}`: Returns ticket metadata, current filing status, municipal token, and audit results.


* `POST /api/v1/tickets/{ticket_id}/submit-otp`: Accepts citizen OTP string, sets `user_provided_otp`, and updates status to `RELAYING_OTP` to unblock the filing worker.


* `POST /api/v1/tickets/{ticket_id}/simulate-resolution`: Accepts `after_image`, loads initial complaint photo from S3, triggers Bedrock audit, and transitions status to `CONFIRMED_CLEAN` or `REOPENED_AUDIT_FAILED`.




2. **Local Mock Portal:**
* Create a static HTML endpoint `GET /mock-pmc-portal` mimicking the PMC grievance form (mobile field, OTP request button, category dropdown, image upload, submit button returning `PMC-SW-2026-XXXX`).




3. **Verification Criterion:** Test the API lifecycle with cURL: submit a mock report, verify the DynamoDB record, and confirm background task initialization.



#### Milestone 4: Playwright Worker & Human-in-the-Loop Relay (Hours 14 – 20)

1. **Autonomous Worker (`backend/app/services/filing_agent.py`):**
* Configure Playwright Chromium to run with `headless=False` for video capture.


* Read environment variable `PORTAL_MODE=live|mock`.


* Direct the browser to `complaint.pmc.gov.in` (or `/mock-pmc-portal`).


* Input citizen phone number and trigger the SMS OTP button.




2. **DynamoDB Polling State Machine:**
* Update DynamoDB state to `AWAITING_OTP` and flag `otp_requested: true`.


* Implement an asynchronous polling loop: check DynamoDB every 2 seconds for up to 120 seconds awaiting `user_provided_otp`.


* Once populated, type the OTP into the form, select "Solid Waste" / "Garbage", inject the Bedrock complaint description, upload the evidence image, and submit.


* Scrape the generated reference ID (e.g., `PMC-SW-2026-89102`) and set status to `SUBMITTED`.




3. **Verification Criterion:** Run the worker script, send an OTP via `POST /api/v1/tickets/{id}/submit-otp`, and watch Playwright complete the form in headed mode.



#### Milestone 5: Beacon-Grade Frontend Assembly (Hours 20 – 30)

1. **Frontend Scaffolding:**
* Run the master UI prompt in v0 or Lovable, download the package, and set up in `/frontend`.


* Ensure core dependencies: `lucide-react`, `clsx`, `tailwind-merge`, and `@radix-ui/react-dialog`.


2. **Dual-Pane Operations Deck:**
* **Left Pane (Operational Stage):**
* Camera capture / file dropzone with GPS coordinate detection.


* Discovered Authority card displaying portal link, nodal email, and statutory draft.


* Primary action buttons: "Launch Native Mail / Share" (triggering `navigator.share` with the actual image) and "Dispatch Filing Worker".
* Live step-indicator accordion tracking filing progress.




* **Right Pane (Agent Intelligence Console):**
* Terminal trace log simulating real-time Bedrock thoughts and Playwright steps.


* KPI telemetry strip across the top (Active Hotspots, Auto-Filing Rate, Fake Resolutions Intercepted, DynamoDB Cache Latency).






3. **Interactive Modals & Demo Toolbar:**
* Wire the `PortalOtpRelayModal`: pop up automatically when ticket status changes to `AWAITING_OTP`.


* Build the "Demo Control Toolbar" at the top header to manually force states (`Simulate Intake`, `Trigger OTP Modal`, `Trigger Ghost Audit`) during presentation recording.




4. **Verification Criterion:** Run the UI on `localhost:5173` and verify seamless WebSocket or polling connection to FastAPI endpoints.



#### Milestone 6: Ghost-Resolution Auditor Panel (Hours 30 – 38)

1. **Forensic Diff Viewer (`GhostResolutionAuditor.tsx`):**
* Side-by-side photo comparison view: "Original Citizen Report" vs. "Worker Resolution Claim".


* Bedrock Forensic Metrics card: Landmark Consistency %, Debris Clearance %, Scene Authenticity.


* High-contrast conditional banners:
* Green banner (`bg-emerald-500/10 text-emerald-400`): Cleanup Verified.


* Pulsing red banner (`bg-rose-500/10 text-rose-400`): Ghost Resolution Detected.






2. **Automated Escalation Action Block:**
* Automatically generate SLA breach dossier addressed to the municipal commissioner when fraud is detected.


* Transition ticket state to `REOPENED_AUDIT_FAILED` in DynamoDB.




3. **Verification Criterion:** Trigger the simulated resolution endpoint using a mismatched image; verify that the UI turns rose, displays Bedrock forensic reasoning, and marks the ticket reopened.



#### Milestone 7: Dry Run, Production Readiness & Video Pitch (Hours 38 – 48)

1. **Pre-Demo Dry Run Checklist:**
* Confirm that sample images are pre-cached in `/tests` for fast drag-and-drop.
* Verify that DynamoDB authority cache is pre-seeded for Pune (`ULB#pune`).


* Ensure `PORTAL_MODE` is tested in both `live` and `mock` environments.




2. **Video Recording Structure (3-Minute Judging Pitch):**
* **0:00 – 0:30 (Problem Hook):** Open on a real street waste dump. Articulate the breakdown: tedious municipal forms and fake worker photo closures.


* **0:30 – 1:30 (Live Intake & Filing):** Capture image in PWA, show Bedrock triage, show auto-discovered authority, demonstrate Playwright navigating the portal, type the OTP into the modal, and retrieve the live reference token.


* **1:30 – 2:15 (The X-Factor Demo):** Upload fake "clean" photo, trigger Bedrock Ghost Auditor, show the screen turn rose, and highlight landmark consistency matching alongside uncollected debris detection.


* **2:15 – 3:00 (AWS Architecture Walkthrough):** Show Bedrock Converse API metrics, DynamoDB single-table items, and S3 evidence buckets in the AWS Console.





---

### Failure Modes & Safety Fallbacks

| Scenario | Immediate Fallback Strategy |
| --- | --- |
| **`complaint.pmc.gov.in` gateway times out** | Flip `PORTAL_MODE=mock` in `.env` to route Playwright to `localhost:8000/mock-pmc-portal` without changing frontend behavior.

 |
| **SMS OTP not received on phone** | The mock portal auto-fills OTP `592014`, or the demo toolbar allows manual injection.

 |
| **AWS Bedrock rate limit or throttling** | Implement an exponential backoff decorator around `bedrock.converse()` with a local mock JSON fallback response.

 |
| **Nominatim reverse geocode rate-limited** | The built-in dictionary in `geo_router.py` automatically resolves Pune, Mumbai, and Bengaluru coordinates locally.

 |
| **Mobile browser blocks image attachment in `mailto:**` | Use the Web Share API Level 2 trigger (`navigator.share`) to hand off both the image file and pre-filled text to the native email client.

 |