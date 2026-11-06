# ResearchMind AI – API Documentation

Base URL: `http://localhost:8000/api`

Full interactive documentation: http://localhost:8000/docs

---

## Authentication (Phase 6)

Most endpoints require a Bearer JWT token.

```
Authorization: Bearer <access_token>
```

Tokens are obtained from `POST /api/auth/login`.

---

## Health

### GET /health
Returns API and service status. No authentication required.

**Response 200:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "services": {
    "gemini": "configured",
    "tavily": "unconfigured",
    "database": "url_set",
    "qdrant": "url_set",
    "langsmith": "disabled"
  }
}
```

---

## Authentication

### POST /auth/register
Register a new user account.

**Request:**
```json
{ "email": "user@example.com", "password": "secure123", "full_name": "Ada Lovelace" }
```

**Response 201:**
```json
{ "user_id": "uuid", "email": "user@example.com", "full_name": "Ada Lovelace" }
```

### POST /auth/login
Login and receive a JWT access token.

**Request:**
```json
{ "email": "user@example.com", "password": "secure123" }
```

**Response 200:**
```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 1800 }
```

### GET /auth/me
Get the currently authenticated user's profile.

---

## Research

### POST /research/plan ✅ (Implemented Phase 2)
Generate a research plan using the Planner Agent.

**Request:**
```json
{
  "topic": "Analyze the future of Generative AI engineering jobs in India.",
  "depth": "standard",
  "mode": "web",
  "language": "English",
  "max_questions": null
}
```

**Depth options:** `quick` | `standard` | `comprehensive`  
**Mode options:** `web` | `documents` | `hybrid`

**Response 201:**
```json
{
  "research_id": "uuid",
  "plan": {
    "plan_id": "uuid",
    "topic": "...",
    "scope_and_objectives": "...",
    "information_categories": ["Skills", "Market", "Salary"],
    "research_questions": [
      {
        "id": "uuid",
        "question": "What GenAI skills are most in-demand?",
        "category": "Skills",
        "priority": 1,
        "search_queries": ["GenAI skills demand India 2024"],
        "rationale": "..."
      }
    ],
    "estimated_duration_minutes": 8,
    "depth": "standard",
    "mode": "web",
    "language": "English"
  },
  "message": "Research plan created. Please review and approve to begin research."
}
```

**Errors:**
- `503` – `GEMINI_API_KEY` not configured
- `502` – Gemini API call failed
- `422` – Invalid request body

---

### POST /research/{id}/approve-plan (Phase 4)
Approve the research plan and start the LangGraph workflow.

### GET /research/{id}/status (Phase 6)
Get real-time workflow status with SSE streaming.

### GET /research/{id}/sources (Phase 6)
Get all sources collected for a research job.

### GET /research/{id}/report (Phase 6)
Get the final report for a completed research job.

---

## Documents (Phase 5)

### POST /documents
Upload a document for RAG research. Multipart form data.

**Form fields:**
- `file` – The file (PDF, DOCX, TXT, MD)
- `description` – Optional description

**Response 201:**
```json
{ "document_id": "uuid", "filename": "report.pdf", "page_count": 45, "chunk_count": 132 }
```

### GET /documents
List all documents owned by the current user.

### DELETE /documents/{id}
Delete a document and remove its vectors from Qdrant.

---

## Reports (Phase 6)

### GET /reports/{id}/export
Download the report as a PDF.

**Response:** `application/pdf` binary stream.

---

## Analytics (Phase 8)

### GET /analytics/overview
High-level stats: total jobs, completion rate, avg duration.

### GET /analytics/usage
API usage breakdown by service and time period.

---

## Error Response Format

All errors follow this structure:

```json
{
  "success": false,
  "error_code": "GEMINI_API_KEY_MISSING",
  "message": "Human-readable error message",
  "details": { "hint": "Add GEMINI_API_KEY to .env" },
  "request_id": "uuid"
}
```

All responses include:
- `X-Request-ID` header for log correlation
- `X-Process-Time-Ms` header for performance monitoring
