# Rift Sales Inbox Task Router & Grounded Chat Assistant

An production-grade enterprise sales inbox routing service and grounded AI chat copilot built for the **FDE Challenge**.

It automatically ingests raw B2B email payloads, extracts structured deal entities via **Gemini 2.5 Flash**, applies deterministic business routing rules (PSU overrides, deal thresholds, spam filtering), persists deduplicated task records to **MongoDB / SQLite / PostgreSQL**, and answers natural language queries with **100% grounded, zero-hallucination SQL/NoSQL query execution**.

---

## System Architecture

![Sales Inbox Architecture Flowchart](./architecture_flowchart.svg)

---

## Core Capabilities

1. **Section 5 Task API (`/tasks`, `/users`)**:
   - Complete Task CRUD operations (`POST`, `GET`, `PATCH`, `DELETE`).
   - Strict enum validation (`category`, `priority`, `assignee_id`).
   - Scoped filtering by `candidate_id`, `assignee_id`, `category`, `priority`, and date ranges.

2. **Section 7 Ingest API (`/ingest`, `/api/ingest-single`)**:
   - Fast async batch email routing pipeline.
   - Extracts deal value (INR), company name, due date, category, and priority using **Gemini 2.5 Flash**.
   - Thread reconciliation: updates existing tasks on email thread replies (`is_reply=true`).
   - Rule 4 filtering: automatically skips out-of-office auto-replies, spam, and newsletters.

3. **Deterministic Business Rules Engine (Section 4)**:
   - **Rule 1 (PSU / Government Priority Override)**: PSU / PSU-adjacent / Government emails are assigned to **u_aarti** regardless of deal size.
   - **Rule 2 (Deal Size Routing)**: Commercial RFPs $\ge ₹10,000,000$ assigned to **u_aarti** (Enterprise); $< ₹10,000,000$ assigned to **u_rohit** (SMB).
   - **Rule 3 (Category Specialization)**: Marketing requests -> **u_meera**, Partnerships -> **u_karan**, Billing/Refunds -> **u_divya**, Unclear -> **u_triage**.
   - **Rule 4 (Noise Filter)**: Auto-replies, newsletters, and promotional spam do not generate tasks.
   - **Rule 5 (Currency Extraction)**: Standardizes Lakhs ($₹1\text{L} = 100,000$), Crores ($₹1\text{Cr} = 10,000,000$), USD ($\$1 = ₹83$), and numeric representations.

4. **Section 8 Grounded Copilot Chat API (`/api/chat`)**:
   - 2-Stage anti-hallucination execution.
   - **Stage 1 (Query Planner)**: Converts user query into DB queries to fetch computed metrics and supporting task lists (`supporting_data`).
   - **Stage 2 (Phraser)**: Formats response strictly using computed ground-truth data.

5. **Flexible Multi-Database Architecture**:
   - Supports **MongoDB** (`MONGODB_URL`), **SQLite** (`DATABASE_URL=sqlite:///./sales_inbox.db`), and **PostgreSQL / Supabase**.

6. **Vercel Cloud Deployment Ready**:
   - Pre-configured `vercel.json` for 1-click cloud deployment of both React Vite frontend and FastAPI backend serverless functions.

---

## Directory Structure

```
d:\CLAUDE\
├── rift_logo.png                    # Brand logo image
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── config.py                # Environment configuration & normalization
│   │   ├── db/
│   │   │   ├── database.py          # SQLAlchemy engine & session factory
│   │   │   ├── models.py            # TaskModel, ProcessedEmailModel, ThreadMapModel
│   │   │   └── mongo.py             # Motor async MongoDB helper
│   │   ├── routers/
│   │   │   ├── tasks.py             # Section 5 Task API endpoints
│   │   │   ├── ingest.py            # Section 7 Ingestion & single email router
│   │   │   ├── chat.py              # Section 8 Grounded chat assistant endpoint
│   │   │   ├── stats.py             # Dashboard statistics & joined task logs
│   │   │   └── users.py             # Team roster & user endpoints
│   │   └── services/
│   │       ├── gemini_service.py    # Gemini 2.5 Flash LLM extraction service
│   │       ├── rules.py             # Deterministic business routing engine & currency regex
│   │       ├── chat_executor.py     # 2-Stage grounded chat executor
│   │       └── sample_generator.py # Synthetic sample batch generator
│   ├── tests/                       # Pytest automated test suite
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── rift_logo.png            # Static brand logo image
│   ├── src/
│   │   ├── App.jsx                  # Main 3-pane dashboard container
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          # Navigation sidebar & candidate ID switcher
│   │   │   ├── JsonInput.jsx        # Raw email batch payload reader
│   │   │   ├── TaskDashboard.jsx    # Triage Queue & task table
│   │   │   ├── SingleEmailReader.jsx# Real email reader interface
│   │   │   ├── SkippedLog.jsx       # Rule 4 noise audit log
│   │   │   └── ChatPanel.jsx        # Copilot Analysis sidebar & JSON grounding
│   │   └── index.css                # Styling directives
│   ├── index.html                   # HTML entrypoint
│   └── package.json
├── architecture_flowchart.svg       # Flowchart architecture diagram
├── vercel.json                      # Vercel deployment configuration
├── DECISIONS.md                     # Engineering trade-offs & architecture rationale
└── EVALS.md                         # Benchmark suite precision & recall report
```

---

## Getting Started

### Environment Setup (`.env`)

Create a `.env` file in the root directory:

```env
# Gemini 2.5 Flash API Key
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# MongoDB Connection URL (Optional - paste your MongoDB string here)
MONGODB_URL=

# SQL Database URL (Defaults to local SQLite)
DATABASE_URL=sqlite:///./sales_inbox.db

# Server Port
PORT=8000
```

---

### Running Locally

#### 1. Backend Server (FastAPI)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/`

#### 2. Frontend UI (React + Vite)

```bash
cd frontend
npm install
npm run dev
```
- Dashboard Interface: `http://localhost:3000`

---

### Deployment to Vercel

The workspace includes a root `vercel.json` configured for Vercel deployment:

```bash
npm i -g vercel
vercel
```

---

## API Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/ingest` | Synchronous batch email ingestion and routing pipeline |
| `POST` | `/tasks` | Create task manually |
| `GET` | `/tasks` | Query tasks filtered by `candidate_id`, `category`, `priority`, `assignee_id` |
| `PATCH` | `/tasks/{id}` | Update task details |
| `DELETE` | `/tasks/{id}` | Delete task |
| `POST` | `/api/chat` | Grounded natural language query copilot |
| `POST` | `/api/ingest-single` | Process a single real email |
| `POST` | `/api/clear-database` | Wipe database clean |
| `GET` | `/users` | Get team roster and assignees |
| `GET` | `/docs` | Interactive Swagger API documentation |

---

## Test Suite Execution

Run the backend pytest suite:

```bash
cd backend
python -m pytest tests/
```
Output:
```
============================= 12 passed in 4.23s ==============================
```
