# LaunchBoard 🚀
> **Your next opportunity starts here.**

An AI-powered fresher job & internship aggregator engineered for the Indian tech ecosystem. Aggregates genuine entry-level opportunities across India from permitted public sources, classifies them using Large Language Models, eliminates duplicates with deterministic fingerprinting and fuzzy matching, and delivers a modern, searchable user experience.

Built for the **Gen AI & Engineering Role Hiring Assignment at Beep**.

---

## 🌟 Verified Platform Metrics (LaunchBoard V2)

| Metric | Measured Value | Verification Source |
|---|---|---|
| **Total Active Jobs** | **880** | Live PostgreSQL DB (`SELECT COUNT(*) FROM jobs WHERE status = 'active'`) |
| **Unique Hiring Companies** | **249** | Live PostgreSQL DB (`SELECT COUNT(DISTINCT company) FROM jobs`) |
| **Unique India-Eligible Jobs** | **179** | 159 India on-site/hybrid/remote + 20 international remote explicitly open to Indian applicants |
| **Internship Opportunities** | **129** | Filterable via `employment_type = 'Internship'` |
| **Fresher / Entry-Level Roles** | **34** | Filterable via `experience_level IN ('Fresher', 'Entry-level')` |
| **Remote Opportunities** | **660** | Filterable via `is_remote = true` |
| **Registered Collectors** | **11** | Arbeitnow, Himalayas, Remotive, Jobicy, RemoteOK, WeWorkRemotely, RSS/Atom, Greenhouse, Lever |
| **AI Classification Quality** | **98.0% Role, 94.0% City** | Ground-truth evaluated across 50 real database records (`evaluation/50_job_evaluation_dataset_verified.csv`) |
| **Commercial AI Cost / 1k Jobs** | **$0.1335** | Gemini Flash-Lite: 235k input / 14.1k output tokens measured ($0.00 actual billed on Google AI Studio Free Tier) |
| **Backend Test Coverage** | **69 / 69 Passed (100%)** | `pytest backend/tests -v` in 5.7s |
| **Frontend Production Build** | **Clean (0 errors, 0 lint warnings)** | Next.js 14 App Router (6/6 static & dynamic routes compiled) |

---

## 1. Project Overview & Vision

College students and fresh graduates in India struggle with an opaque, fragmented job market where listings are scattered across dozens of individual company career pages, community boards, and aggregators riddled with expired or fake opportunities.

**LaunchBoard** solves this by:
- Ingesting listings exclusively from **permitted public APIs, authorized feeds, and official company ATS endpoints**.
- Preserving original source provenance and direct application links — **zero fabricated listings or dummy application URLs**.
- Using **Google Gemini** to infer nuanced technical role categories, extract and normalize Indian cities, and isolate specific technologies.
- Distinguishing between **Fresher**, **Internship**, **Entry-level**, and **Experienced** roles so experienced jobs are never misclassified as fresher.
- Applying a multi-stage **Deduplication Engine** that identifies cross-posted jobs across multiple sources.
- Measuring real LLM token consumption and calculating accurate dollar costs per 1,000 posts.
- Providing an **Evaluation Suite** with a 50-job ground-truth verification dataset for measurable classification accuracy.
- Automating daily ingestion at **00:30 UTC (6:00 AM IST)** via **GitHub Actions**.

---

## 2. Technology Stack & Design Rationale

| Layer | Technology | Selection Rationale |
|-------|------------|---------------------|
| **Frontend** | Next.js 14 (App Router), TypeScript | Server-side rendering (SSR), fast client transitions, strict typing, search-engine visibility. |
| **Styling & UI** | Tailwind CSS, shadcn/ui, Lucide Icons | Clean modern SaaS design, accessible Radix UI primitives, zero runtime CSS overhead, native light/dark mode. |
| **Backend** | Python 3.13, FastAPI | High-concurrency async I/O (`asyncio`), native OpenAPI documentation, rapid JSON serialization. |
| **Validation** | Pydantic v2 | Strict data contracts, schema validation, zero-overhead coercion, JSON schema generation for AI output. |
| **ORM & Database**| SQLAlchemy 2.0 (asyncio), PostgreSQL | ACID compliance, relational integrity, JSONB support, composite indexing. Compatible with Neon and Supabase. |
| **Migrations** | Alembic | Trackable database schema versioning across development, staging, and production environments. |
| **AI Classifier**| Google Gemini 2.0 Flash / 1.5 Flash | High reasoning accuracy on technical job specs, sub-second latency, ultra-competitive pricing (\$0.10 / 1M input tokens). |
| **Deduplication**| RapidFuzz, SHA-256 | High-throughput C++-backed fuzzy token similarity; deterministic cryptographic fingerprinting. |
| **Automation** | GitHub Actions | Reliable serverless daily scheduled workflows (`cron`) with manual dispatch support. |
| **Package Mgmt**| Astral `uv` | 10–100x faster dependency resolution and virtual environment management in Python. |

---

## 3. Architecture & Data Flow

```
+-----------------------------------------------------------------------------------+
|                            Permitted Data Sources                                 |
|  Arbeitnow · Himalayas · Remotive · Jobicy · RemoteOK · WWR · RSS · ATS Feeds     |
|         (Official ATS: InMobi, Rubrik, CRED, Zeta, GitLab, Automattic, Linear)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        Data Collection Pipeline (FastAPI)                         |
|    HTML Sanitization · Date Parsing · India City Heuristics · RawJob Validation   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              Deduplication Engine                                 |
|     1. Suffix-stripped Company Normalization                                      |
|     2. Regional & Remote Title Normalization                                      |
|     3. Canonical Indian City Normalization (e.g. Bangalore -> Bengaluru)           |
|     4. Deterministic SHA-256 Fingerprinting                                      |
|     5. URL Canonicalization & Tracking Param Stripping                            |
|     6. RapidFuzz Token-Set Similarity Check (>= 85.0%)                            |
+-----------------------------------------------------------------------------------+
                                         |
                       +-----------------+-----------------+
                       | New Listing                       | Re-seen Listing
                       v                                   v
+------------------------------------------+    +-----------------------------------+
|        GenAI Classification Engine       |    |      Update last_verified_at      |
|    Gemini API · Structured JSON Output   |    |    Preserve secondary source ref  |
|     Pydantic Validation · Cost Record    |    +-----------------------------------+
+------------------------------------------+
                       |
                       v
+-----------------------------------------------------------------------------------+
|                        PostgreSQL Database (6 Normalized Tables)                  |
|    jobs · job_sources · classifications · collection_runs · usage · source_status |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                               Next.js Frontend                                    |
|   Live Stats · Search · Faceted Filters · Responsive Cards · Job Details · Admin  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Database Schema

LaunchBoard utilizes 6 normalized tables with foreign keys and composite indexes:

1. **`jobs`**: Canonical job records.
   - `id`: UUID (Primary Key)
   - `title`: String(500), Indexed
   - `company`: String(300), Indexed
   - `description`: Text (Original job description)
   - `location`: String(300)
   - `city`: String(200), Indexed (Normalized Indian city or "Remote")
   - `employment_type`: String(50) (Internship, Full-time, Part-time, Contract)
   - `experience_level`: String(50) (Fresher, Internship, Entry-level, Experienced, Unknown)
   - `application_url`: String(2000) (Original application URL)
   - `source_name`: String(200)
   - `source_url`: String(2000)
   - `posted_at`: Timestamp (Original employer posting date, if available)
   - `collected_at`: Timestamp (Ingestion timestamp)
   - `last_verified_at`: Timestamp (Most recent verification)
   - `status`: String(20) (active, expired, removed)
   - `role_category`: String(100), Indexed
   - `skills`: JSON (Array of extracted skill strings)
   - `is_remote`: Boolean, Indexed
   - `fingerprint`: String(64), Unique, Indexed (SHA-256 dedup hash)
   - `classification_confidence`: Float (0.0 to 1.0)
   - `classification_status`: String(20) (classified, review, uncertain, failed)
   - Composite indexes: `(company, title, location)` and `(status, role_category)`

2. **`job_sources`**: Provenance tracking for cross-posted jobs.
   - `id`: UUID (PK), `job_id`: FK -> `jobs.id` (CASCADE)
   - `source_name`, `source_url`, `source_job_id`, `application_url`, `discovered_at`, `last_seen_at`, `is_primary`
   - Unique constraint: `(source_name, source_job_id)`

3. **`classifications`**: AI audit trail.
   - `id`: UUID (PK), `job_id`: FK -> `jobs.id` (CASCADE)
   - `model_name`, `role_category`, `city`, `skills`, `experience_level`, `employment_type`, `is_remote`, `confidence`, `raw_response`, `input_tokens`, `output_tokens`, `processing_time_ms`, `classified_at`

4. **`collection_runs`**: Ingestion execution telemetry.
   - `id`: UUID (PK), `started_at`, `completed_at`, `status`, `trigger_type` (scheduled/manual)
   - `total_fetched`, `total_new`, `total_updated`, `total_duplicates`, `total_classified`, `total_failed`, `total_errors`
   - `error_details` (JSON), `source_results` (JSON breakdown per source)

5. **`classification_usage`**: LLM cost and token accounting.
   - `id`: UUID (PK), `collection_run_id`: FK -> `collection_runs.id` (SET NULL)
   - `model_name`, `total_input_tokens`, `total_output_tokens`, `total_requests`, `total_cost_usd`, `pricing_config` (JSON)

6. **`source_status`**: Scraper health & circuit-breaker metrics.
   - `id`: UUID (PK), `source_name`: String(200) Unique
   - `is_enabled`, `last_success_at`, `last_failure_at`, `last_error_message`, `total_jobs_collected`, `total_runs`, `total_failures`, `consecutive_failures`

---

## 5. Data Collection Strategy & Source Compliance

LaunchBoard strictly adheres to web scraping ethics, robots.txt, and platform terms of service:
- **No CAPTCHA or Authentication Bypassing**: No scraping behind paywalls or logins.
- **Rate-Limiting & Backoff**: Configured delays between requests to prevent service degradation.
- **Source Graceful Degradation**: If an external provider experiences downtime, the error is recorded in `source_status` without halting other collectors or corrupting existing active jobs.
- **Distinguishing Discovery vs Posting**:
  - `posted_at`: Original employer timestamp.
  - `collected_at`: When LaunchBoard first ingested the job.
  - `last_verified_at`: When the listing was confirmed active in a subsequent collection run.
  - Old jobs newly discovered are **never** presented as newly posted.

### India Opportunities & Honest Target Reconciliation
- **Active Physical / Hybrid / Remote India Listings**: **159 jobs** across major hubs (Bengaluru, Pune, Hyderabad, Mumbai, Gurugram, Noida, Chennai, Kolkata).
- **International Remote Listings Open to India**: **20 jobs** with explicit eligibility tags ("India", "APAC", "Worldwide", "Anywhere", "Remote - Global").
- **Total Unique Deduplicated India-Eligible Opportunities**: **179 jobs** (159 + 20).
- **Platform-wide Totals**: **880 active jobs**, **129 internships**, **34 fresher/entry-level roles**, **660 remote roles**.
- **Domestic Platform Constraints**: Portals like Naukri, Internshala, and Wellfound implement aggressive anti-bot protections (Cloudflare Turnstile, perimeter WAFs) and strictly forbid automated access. In accordance with assignment instructions and web ethics, LaunchBoard **never bypasses security gates and never fabricates mock or dummy listings**. Instead, domestic expansion is achieved legally through verified company ATS endpoints (e.g. Greenhouse & Lever for InMobi, Rubrik, CRED, Zeta).

---

## 6. GenAI Classification Engine & Backlog Processor

Located in `backend/app/services/classifier.py` with prompt templates in `prompts/job_classification.txt`.

### 15 Supported Role Categories:
1. Software Development
2. Frontend Development
3. Backend Development
4. Full Stack Development
5. AI/ML Engineering
6. Data Science
7. Data Analytics
8. DevOps / Cloud
9. Cybersecurity
10. Mobile Development
11. QA / Testing
12. UI/UX Design
13. Product Management
14. Business Development
15. Other

### Schema-Enforced JSON Output:
```json
{
  "role_category": "Backend Development",
  "city": "Bengaluru",
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
  "experience_level": "Fresher",
  "employment_type": "Full-time",
  "is_remote": false,
  "confidence": 0.94
}
```

### Classification Rules & Prompt Engineering:
- **Role Inferred from Responsibilities**: A "Software Engineer" writing Python microservices is classified as `Backend Development`, not generic `Software Development`.
- **Specialized Security Classification**: Roles containing "Security Engineer", "Application Security", or "AppSec" are classified strictly as `Cybersecurity` rather than generic backend.
- **Multilingual Remote Recognition**: Detects international remote indicators (German "Homeoffice", "100% Remote", "Telearbeit", French "Télétravail") as `is_remote: true`, `city: 'Remote'`.
- **City Extraction & Normalization**: "Bangalore" -> `Bengaluru`, "Gurgaon" -> `Gurugram`, "Bombay" -> `Mumbai`.
- **Non-Indian Offices**: Foreign physical offices (London, Singapore, Tokyo, New York) without India presence are mapped to `is_remote: false`, `city: 'Unknown'`.
- **Strict Anti-Hallucination**: The model is prohibited from guessing or inventing Indian cities for unlocated jobs.
- **Experience Level Separation**: Never assumes an internship is automatically a fresher role, and never classifies an experienced role as fresher without explicit evidence in the job description.

### Rate-Limiting & Backlog Architecture
- **Gemini Free-Tier 15 RPM Pacing**: Google AI Studio free tier limits requests to 15 Requests Per Minute. LaunchBoard enforces a **4.2-second sleep** between calls (14.28 RPM maximum), completely eliminating `429 ResourceExhausted` errors.
- **Tenacity Exponential Backoff**: Uses `stop_after_attempt(4)` and `wait_exponential(min=4, max=25)` to gracefully handle temporary burst limits.
- **Dedicated Backlog Processor**: `backend/app/services/classification_backlog.py` processes pending and unclassified jobs in atomic batches with per-job database commits, enabling seamless interruption and resume.
- **CLI & API Triggering**:
  ```bash
  # Run backlog processing via CLI:
  b:\launchboard\backend\.venv\Scripts\python.exe backend/scripts/process_backlog.py --batch-size 50 --delay 4.2
  ```
  Or trigger in background via Admin API: `POST /api/admin/classify/backlog?batch_size=50`

---

## 7. Accuracy Evaluation Report (50-Job Ground Truth)

As required by the Beep assignment, LaunchBoard includes a dedicated evaluation dataset and ground-truth validation suite:
- **`evaluation/50_job_evaluation_dataset.csv`**: Unlabeled evaluation dataset with blank human-verification columns for independent manual review.
- **`evaluation/50_job_evaluation_dataset_verified.csv`**: Full ground-truth human-verified evaluation dataset across 50 real database records covering competitive Indian technical listings and international remote opportunities.

### Actual Measured Evaluation Results:
```
============================================================
  LaunchBoard AI Classification Evaluation Report (50 Jobs)
============================================================

📊 Total Records Evaluated: 50
🤖 Model: gemini-flash-lite-latest

🏷️  Role Classification Accuracy:
   49 / 50 = 98.0%

📍 City Extraction & Normalization Accuracy:
   47 / 50 = 94.0%

✅ Combined Exact-Match Accuracy:
   46 / 50 = 92.0%

🔍 Error Analysis & Engineering Mitigations:
   1. Role Error (1):
      - Job: Linear "Software Engineer, Security" was classified as "Backend Development".
      - Mitigation: Refined prompt to explicitly mandate that any security-focused software engineering title maps to "Cybersecurity".
   2. City Errors (3):
      - Job: Linear physical office jobs in London & Singapore were classified as "Remote" due to generic hybrid company perks in the text.
      - Mitigation: Added negative prompt rule: non-Indian physical offices without remote designation must map to city "Unknown" and is_remote: false.
      - Job: German Arbeitnow listing with "Homeoffice" was classified as city "Unknown".
      - Mitigation: Added multilingual remote terminology recognition ("Homeoffice", "Telearbeit", "Télétravail").
============================================================
```

---

## 8. LLM Cost Tracking & Measured Economics

LaunchBoard tracks exact input and output token consumption per classification call via `cost_tracker.py` and persists usage in the `classification_usage` table:

### Real Measured Usage on Production Database:
| Metric | Measured Value |
|---|---|
| **AI Model** | `gemini-flash-lite-latest` |
| **Total Measured API Calls** | **164** |
| **Input Tokens Measured** | **235,436** (avg. 1,435.6 tokens / job) |
| **Output Tokens Measured** | **14,145** (avg. 86.3 tokens / job) |
| **Total Tokens Consumed** | **249,581** |
| **Actual Billed Cost** | **$0.00** (Google AI Studio Free Tier) |
| **Estimated Commercial Cost** | **$0.0219** for 164 jobs ($0.0001335 per job) |
| **Projected Cost / 1,000 Posts** | **$0.1335** (~$0.129–$0.134 / 1k jobs) |

### Commercial Pricing Benchmark:
| Provider & Model | Input Price / 1M | Output Price / 1M | Cost / 1k Jobs |
|---|---|---|---|
| **Gemini Flash-Lite (Current)** | **$0.075** | **$0.300** | **$0.1335** |
| Gemini 2.0 Flash | $0.100 | $0.400 | $0.1780 |
| GPT-4o Mini | $0.150 | $0.600 | $0.2670 |

---

## 9. API Reference

### Public Endpoints

#### `GET /api/jobs`
Query parameters:
- `q`: Search query (searches title, company, description)
- `role_category`: Filter by role (e.g. `Backend Development`, `AI/ML Engineering`)
- `city`: Filter by city (e.g. `Bengaluru`, `Remote`)
- `employment_type`: Filter by type (`Internship`, `Full-time`, `Contract`)
- `experience_level`: Filter by level (`Fresher`, `Internship`, `Entry-level`, `Experienced`)
- `is_remote`: Boolean filter (`true` / `false`)
- `sort_by`: `collected_at`, `posted_at`, `company`, `title` (Default: `collected_at`)
- `sort_order`: `desc` or `asc` (Default: `desc`)
- `page`: Page index (Default: 1)
- `page_size`: Page size (Default: 20, max: 100)

#### `GET /api/jobs/{job_id}`
Returns full job details including original description, classifications, skills list, and source verification metadata.

#### `GET /api/roles`
Returns distinct active roles and live job counts: `[{"role_category": "Backend Development", "count": 128}, ...]`.

#### `GET /api/cities`
Returns distinct active cities and counts: `[{"city": "Bengaluru", "count": 67}, ...]`.

#### `GET /api/stats`
Returns live platform metrics:
```json
{
  "total_active_jobs": 880,
  "total_unique_jobs": 880,
  "total_companies": 249,
  "total_cities": 35,
  "total_remote_jobs": 660,
  "jobs_by_role": { ... },
  "jobs_by_city": { ... },
  "last_successful_refresh": "2026-11-18T10:15:00Z",
  "total_sources": 11
}
```

### Administrative Endpoints (`X-Admin-API-Key` required)

#### `POST /api/admin/refresh`
Triggers an asynchronous collection run across all 11 collectors. Returns HTTP 409 Conflict if a run is already active.

#### `GET /api/admin/refresh/status`
Returns real-time status, counts, and per-source telemetry of the latest ingestion pipeline run.

#### `POST /api/admin/classify/backlog`
Executes rate-paced backlog classification across pending unclassified jobs with atomic per-job checkpointing. Query parameter: `batch_size` (default 50).

#### `GET /api/admin/dashboard`
Returns comprehensive administrative metrics (totals, source circuit-breaker statuses, token cost report, and run history).

#### `GET /api/admin/evaluation/export`
Exports up to 50 classified jobs as a CSV for manual ground truth labeling.

---

## 10. Automated Ingestion Scheduler & Hosting Architecture

### Built-in 30-Minute Scheduler
LaunchBoard includes an in-process `CollectionScheduler` defined in `backend/app/services/scheduler.py` initialized during the FastAPI lifespan event. It automatically executes a complete ingestion cycle every 30 minutes with graceful shutdown handling.

### Hosting Compatibility & Deployment Rules:
- **Persistent Server Environments (Fully Compatible)**:
  - Docker Containers, Linux VMs, Railway, Render, DigitalOcean.
  - The in-process event loop runs indefinitely in the background; the 30-minute timer triggers reliably.
- **Serverless Environments (Requires External Trigger)**:
  - Vercel Serverless Functions, AWS Lambda, Google Cloud Run (min instances = 0).
  - Serverless platforms freeze execution threads when incoming HTTP requests complete. In-process timers will sleep between invocations.
  - **Serverless Solution**: Use GitHub Actions ([`.github/workflows/daily-refresh.yml`](file:///.github/workflows/daily-refresh.yml)) or a managed cron trigger (e.g. Vercel Cron, Cloud Scheduler) to invoke `POST /api/admin/refresh` with the `X-Admin-API-Key` header.

---

## 11. Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL or SQLite (for tests)
- uv (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Step 1: Clone & Configure
```bash
git clone https://github.com/your-username/launchboard.git
cd launchboard
```

### Step 2: Start Backend
```bash
cd backend
uv venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation: `http://localhost:8000/docs`

### Step 3: Start Frontend
```bash
cd ../frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

### Step 4: Run Tests
```bash
cd ..
backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```
*Result: 69/69 unit and integration tests passing.*

---

## 12. Deployment Instructions

### Option A: Docker Compose (All-in-One)
```bash
docker-compose up --build -d
```
Starts:
- PostgreSQL on `localhost:5432`
- FastAPI backend on `http://localhost:8000`
- Next.js frontend on `http://localhost:3000`

### Option B: Cloud Deployment (Vercel + Render + Neon)
1. **Database**: Create a serverless PostgreSQL database on [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com).
2. **Backend (Render)**:
   - Connect repository to [Render](https://render.com).
   - Blueprint `render.yaml` automatically sets up the Python service.
   - Set environment variables: `DATABASE_URL`, `GEMINI_API_KEY`, `ADMIN_API_KEY`.
3. **Frontend (Vercel)**:
   - Import `frontend/` directory to [Vercel](https://vercel.com).
   - Set environment variable: `NEXT_PUBLIC_API_URL=https://your-backend.onrender.com`.

---

## 13. Known Limitations & Ethical Scraping Compliance

### Limitations:
- **Domestic Portal Anti-Bot Gating**: Large Indian domestic portals (Naukri, Internshala, Wellfound) strictly prohibit automated scraping and enforce CAPTCHA / Cloudflare Turnstile barriers. In strict accordance with assignment ethics, LaunchBoard does not deploy circumvention scripts or generate fake dummy listings. Expansion relies on verified public ATS boards (Greenhouse, Lever) of Indian engineering employers.
- **Free-Tier API Rate Limits**: Google AI Studio free tier limits classification throughput to 15 RPM. The built-in backlog processor throttles calls with a 4.2-second pause to prevent quota errors.
- **Multiple Office Mentions**: When a job posting lists several regional hubs in freeform text, the primary mentioned hub is assigned as canonical.

---

## 14. 5-Minute Video Walkthrough Outline

For reviewers evaluating the Beep Gen AI & Engineering submission, here is the structured 5-minute demonstration outline:

| Time | Section | Key Demonstration Points |
|---|---|---|
| **0:00 – 1:00** | **Problem & Live Product Tour** | • Open `http://localhost:3000`<br>• Highlight hero statistics: 880 active jobs, 179 India-eligible, 249 hiring companies.<br>• Demonstrate live text search, role filtering (`AI/ML`, `Backend`), and freshness sorting.<br>• Inspect a job card showing original posting date, verified Indian city, and direct employer application URL. |
| **1:00 – 2:00** | **Multi-Source Ingestion & Compliance** | • Walk through `backend/app/collectors/`<br>• Explain the 11 registered sources: Arbeitnow, Himalayas, Remotive, Jobicy, RemoteOK, WWR, RSS, Greenhouse, Lever.<br>• Highlight ATS coverage of domestic hubs (InMobi, Rubrik, CRED, Zeta).<br>• Show source provenance in PostgreSQL: zero dummy data, original application URLs preserved. |
| **2:00 – 3:00** | **Deduplication & Gemini AI Pipeline** | • Explain the 6-stage deduplication engine (company suffix stripping, city canonicalization, SHA-256 fingerprint, RapidFuzz token matching).<br>• Open `backend/app/services/classifier.py` and `prompts/job_classification.txt`.<br>• Explain prompt rules: 15 technical roles, cybersecurity isolation, multilingual remote keywords, anti-hallucination city policy. |
| **3:00 – 4:00** | **Evaluation Suite & Token Economics** | • Walk through `evaluation/50_job_evaluation_dataset_verified.csv`.<br>• Show measured accuracy: 98.0% Role, 94.0% City.<br>• Discuss the 3 edge cases and prompt mitigations.<br>• Open `backend/app/services/cost_tracker.py`: 235k input / 14k output tokens measured, $0.1335 per 1k jobs commercial equivalent ($0.00 actual on free tier). |
| **4:00 – 5:00** | **Admin Dashboard & Background Operations** | • Log in to `/admin` with `X-Admin-API-Key`.<br>• Demonstrate live ingestion telemetry, source health circuit-breakers, and token cost charts.<br>• Trigger `/api/admin/classify/backlog` and show rate-limit-aware 4.2s pacing in action.<br>• Explain scheduler hosting architecture: persistent lifespan loop vs serverless GitHub Actions cron. |
