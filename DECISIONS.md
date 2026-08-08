# RIFT Architectural & Engineering Decisions (DECISIONS.md)

This document outlines the 5 key engineering trade-offs, architecture decisions, and limitations chosen during the design and implementation of RIFT.

---

## 1. Rate Limit & Retries: Rules Engine Fallback
- **Decision**: In a production environment, APIs can fail due to rate-limiting (`429`), network instability, or authorization credentials (`401` / `403` key validation errors).
- **Trade-off**: Instead of relying solely on heavy retry loops that cause request timeouts (especially on serverless Vercel endpoints capped at 10-15 seconds), RIFT integrates a deterministic **Rules Engine** (`rules.py`).
- **Mechanism**: If the Gemini API client throws a connection error or returns a `401`/`403`, the system immediately falls back to regex-based rule routing (mapping categories, priorities, and assignees deterministically). This guarantees a `200 OK` ingestion response under all conditions.

---

## 2. Idempotency: Unique Candidate & Email Constraints
- **Decision**: The grading client frequently replays duplicate ingest batches. RIFT prevents task amplification by enforcing strict idempotency boundaries.
- **Trade-off**: Before writing any record, the ingest worker queries the database for existing `candidate_id` + `source_email_id` matches.
- **Outcome**: If a task with the same `source_email_id` is found under the candidate ID, the system returns the existing task object with a `"note": "existing_duplicate"` status flag, guaranteeing task counts never inflate upon replay.

---

## 3. Database Design: Dual MongoDB & SQL Fallback Pipelines
- **Decision**: To accommodate diverse hosting and deployment requirements (e.g., local developers using SQLite vs. production Vercel using MongoDB Atlas), the data layer supports dual active modes.
- **Trade-off**: Using Motor (async MongoDB driver) when `MONGODB_URL` is active, and defaulting to SQLAlchemy (synchronous SQLite/PostgreSQL) when MongoDB is offline.
- **Validation**: Schema-level contracts are strictly matched between both databases (mapping models, fields, and constraints) to ensure identical API output regardless of the storage backend.

---

## 4. Chat Grounding: Structured Intent Query Parser
- **Decision**: Directly passing user-facing questions to an LLM and asking it to write raw SQL or guess statistics leads to hallucinated numbers and severe security SQL injection vectors.
- **Trade-off**: RIFT uses a multi-tier **Grounded Chat Pipeline**:
  1. The user's query and conversation history are sent to Gemini to output a *Structured Query Plan* (matching a validated JSON schema).
  2. The backend converts the structured plan into a safe, parameterized database query (filtering by assignee, priority, category, or search term).
  3. The resulting database record/count is passed back as the *only* context to Gemini to construct the conversational response.
- **Outcome**: Ground truth is mathematically validated by database queries, preventing AI hallucinations.

---

## 5. Known Limitation: Thread Reconciliation Merging
- **Decision**: When a thread reply arrives, the system is designed to update the original task (`PATCH`) instead of creating a new task record.
- **Limitation**: Currently, thread updates overwrite fields like `priority` and `deal_value_inr` with the newest email's data, but do not append the email body preview in a history array. 
- **Future Improvement**: A nested `emails_history` array should be maintained inside the task document to preserve all past thread replies in order.
