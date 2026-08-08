# RIFT — Engineering Decisions

This document outlines the key engineering trade-offs, architecture decisions, and known limitations made during the design and implementation of RIFT.

---

## 1. Rate Limiting & Reliability: Rules Engine Fallback

**Decision**: External extraction APIs can fail due to rate-limiting (`429`), network instability, or credential errors (`401` / `403`).

**Trade-off**: Rather than relying on retry loops — which cause request timeouts on serverless endpoints capped at 10–15 seconds — RIFT integrates a deterministic **Rules Engine** (`rules.py`) as the primary fallback layer.

**Mechanism**: If the extraction API returns an error or auth failure, the system immediately falls back to regex-based rule routing, deterministically mapping categories, priorities, and assignees. This guarantees a `200 OK` ingestion response under all network conditions.

---

## 2. Idempotency: Scoped Email & Candidate Constraints

**Decision**: Ingestion clients frequently replay duplicate batches. RIFT prevents task amplification through strict idempotency boundaries.

**Trade-off**: Before writing any record, the ingest worker checks for an existing `candidate_id` + `source_email_id` match in the database.

**Outcome**: If a task with the same `source_email_id` already exists under the candidate, the system returns the existing task object with a `"note": "existing_duplicate"` flag — task counts never inflate on replay.

---

## 3. Database Design: Dual MongoDB & SQL Fallback

**Decision**: To accommodate diverse deployment requirements (local developers using SQLite vs. production using MongoDB Atlas), the data layer supports two active modes simultaneously.

**Trade-off**: Motor (async MongoDB driver) is used when `MONGODB_URL` is configured; SQLAlchemy (SQLite/PostgreSQL) is used as fallback when MongoDB is unavailable.

**Validation**: Schema contracts are strictly matched between both backends — the same field names, types, and constraints — so API output is identical regardless of which storage layer is active.

---

## 4. Chat Grounding: Structured Intent Query Execution

**Decision**: Passing natural-language questions directly to a language model and asking it to generate statistics or SQL leads to fabricated numbers and SQL injection risks.

**Trade-off**: RIFT uses a two-stage **Grounded Chat Pipeline**:
1. The user's query and conversation history are sent to the extraction layer, which outputs a *Structured Query Plan* in a validated JSON schema (intent + filters — no free text).
2. The backend converts the structured plan into a safe, parameterised database query.
3. The computed database result is passed back as the *only* context for constructing the conversational response — no values are generated from model memory.

**Outcome**: All numbers in responses are mathematically exact, sourced directly from live database queries.

---

## 5. Known Limitation: Thread Reconciliation Field Merging

**Decision**: When a thread reply arrives, the system updates the original task (`PATCH`) rather than creating a new record.

**Limitation**: Thread updates overwrite scalar fields (`priority`, `deal_value_inr`) with the newest email's values, but do not append email body content to a history array.

**Future Improvement**: A nested `emails_history` array should be maintained inside the task document to preserve all thread replies in insertion order, alongside a field-level change delta log.
