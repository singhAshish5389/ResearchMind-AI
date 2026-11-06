# ResearchMind AI

**Autonomous Multi-Agent Research and Intelligence Platform**

> A production-oriented portfolio project demonstrating Generative AI engineering: LLMs, multi-agent orchestration (LangGraph), RAG (Qdrant), real web search (Tavily), FastAPI backend, and React frontend.

---

## What It Does

ResearchMind AI takes any research topic and autonomously:

1. **Plans** – Creates 5–10 targeted research questions (Planner Agent + Gemini)
2. **Researches** – Searches the internet for real sources (Researcher Agent + Tavily)
3. **Analyzes** – Identifies themes, trends, opportunities, and contradictions (Analyst Agent)
4. **Fact Checks** – Verifies claims against collected evidence (Fact Checker Agent)
5. **Reports** – Generates a professional, downloadable PDF report with citations (Report Writer Agent)

All agents are coordinated by **LangGraph** with conditional routing, retry logic, and human-in-the-loop plan approval.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI / LLM | Google Gemini API (`google-genai`) |
| Agent Orchestration | LangGraph |
| LLM Framework | LangChain |
| Web Search | Tavily Search API |
| Embeddings | HuggingFace `sentence-transformers` |
| Vector DB | Qdrant |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| PDF Generation | ReportLab |
| Frontend | React + Vite + Tailwind CSS |
| Auth | JWT (python-jose + bcrypt) |
| Observability | LangSmith / Langfuse |
| Evaluation | RAGAS / DeepEval |
| Deployment | Docker + Docker Compose |

---

## Project Structure

```
researchmind-ai/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py         # Pydantic Settings (env vars)
│   │   ├── agents/           # 5 specialized AI agents
│   │   │   ├── planner.py    # ✅ Implemented (Phase 2)
│   │   │   ├── researcher.py # 🔲 Phase 3
│   │   │   ├── analyst.py    # 🔲 Phase 3
│   │   │   ├── fact_checker.py # 🔲 Phase 3
│   │   │   └── report_writer.py # 🔲 Phase 3
│   │   ├── graph/            # LangGraph workflow (Phase 4)
│   │   ├── tools/            # Search tools (Phase 3)
│   │   ├── rag/              # RAG pipeline (Phase 5)
│   │   ├── database/         # SQLAlchemy models (Phase 6)
│   │   ├── api/              # FastAPI routers
│   │   │   └── research.py   # ✅ /api/research/plan
│   │   ├── schemas/          # Pydantic schemas
│   │   │   └── research.py   # ✅ All research schemas
│   │   ├── auth/             # JWT auth (Phase 6)
│   │   ├── evaluation/       # RAGAS/DeepEval (Phase 8)
│   │   └── utils/            # Logging, exceptions
│   ├── tests/
│   │   ├── test_planner.py   # ✅ 15 tests
│   │   └── test_api.py       # ✅ 12 tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/            # ✅ All 13 pages (some stubs)
│   │   ├── components/       # ✅ Sidebar, Navbar, Layout
│   │   ├── services/api.js   # ✅ Axios API client
│   │   ├── App.jsx           # ✅ React Router
│   │   └── index.css         # ✅ Tailwind + custom styles
│   ├── Dockerfile
│   └── vite.config.js
├── docs/
├── .env                      # Your local env (fill in keys)
├── .env.example              # Template with all variables
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Development Progress

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Project Foundation (structure, env, Docker) | ✅ Complete |
| Phase 2 | Planner Agent + Gemini API + REST endpoint | ✅ Complete |
| Phase 3 | Researcher, Analyst, Fact Checker, Report Writer | 🔲 Next |
| Phase 4 | LangGraph multi-agent orchestration | 🔲 Upcoming |
| Phase 5 | RAG pipeline (Qdrant + HuggingFace) | 🔲 Upcoming |
| Phase 6 | PostgreSQL, Auth (JWT), SSE streaming | 🔲 Upcoming |
| Phase 7 | Full React frontend | 🔲 Upcoming |
| Phase 8 | Evaluation, LangSmith, Docker deploy | 🔲 Upcoming |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/researchmind-ai.git
cd researchmind-ai
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in **at minimum** for Phase 1+2:

| Variable | Required For | Where to Get It |
|---|---|---|
| `GEMINI_API_KEY` | AI agent features | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `TAVILY_API_KEY` | Web research (Phase 3+) | [tavily.com](https://tavily.com) |
| `JWT_SECRET_KEY` | Authentication (Phase 6+) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Persistence (Phase 6+) | Local PostgreSQL or Docker |

> **Without API keys:** The backend starts, health endpoint works, and a clear error is shown. Gemini key is required for the `/api/research/plan` endpoint.

### 3. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Start the backend

```bash
# From backend/ directory (with venv activated)
uvicorn app.main:app --reload --port 8000
```

Backend will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

### 5. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: http://localhost:5173

---

## API Endpoints (Phase 1+2)

### Health Check
```
GET /api/health
```
Returns API status and which services are configured.

### Generate Research Plan (requires GEMINI_API_KEY)
```
POST /api/research/plan
Content-Type: application/json

{
  "topic": "Analyze the future of Generative AI engineering jobs in India.",
  "depth": "standard",
  "mode": "web",
  "language": "English"
}
```

**Response:**
```json
{
  "research_id": "uuid",
  "plan": {
    "plan_id": "uuid",
    "topic": "...",
    "scope_and_objectives": "...",
    "information_categories": ["Skills", "Salaries", "..."],
    "research_questions": [
      {
        "id": "uuid",
        "question": "...",
        "category": "...",
        "priority": 1,
        "search_queries": ["query 1", "query 2"],
        "rationale": "..."
      }
    ],
    "estimated_duration_minutes": 8,
    "depth": "standard",
    "mode": "web"
  },
  "message": "Research plan created. Please review and approve to begin research."
}
```

Full API documentation is available at `/docs` (Swagger UI).

---

## Running Tests

```bash
# From backend/ directory (with venv activated)
pytest

# With verbose output
pytest -v

# Run only planner tests
pytest tests/test_planner.py -v

# Run only API tests
pytest tests/test_api.py -v
```

Tests run **without consuming API credits** — Gemini is mocked in all non-integration tests.

---

## Docker (Full Stack)

> Requires Docker Desktop installed.

```bash
# Copy .env with your actual keys first
cp .env.example .env
# ... fill in .env ...

# Start all services
docker compose up --build

# Start in background
docker compose up -d

# Stop everything
docker compose down
```

Services started by Docker:
- **Backend** → http://localhost:8000
- **Frontend** → http://localhost:5173
- **PostgreSQL** → localhost:5432
- **Qdrant** → http://localhost:6333

---

## Architecture

```
User Request
    │
    ▼
FastAPI Backend (Python 3.11)
    │
    ├── POST /api/research/plan
    │       │
    │       ▼
    │   Planner Agent ──► Gemini API
    │       │
    │       ▼
    │   ResearchPlan (Pydantic validated)
    │
    └── POST /api/research/{id}/approve-plan  [Phase 4]
            │
            ▼
        LangGraph StateGraph
            │
            ├── Researcher Agent ──► Tavily Search API
            ├── Analyst Agent ──────► Gemini API
            ├── Fact Checker Agent ─► Gemini API
            └── Report Writer Agent ► Gemini + ReportLab
                        │
                        ▼
                 PostgreSQL (persistence)
                 Qdrant (RAG vectors)
                 PDF Report
```

---

## Environment Variables Reference

See [`.env.example`](.env.example) for the complete list with explanations.

**Minimum required for Phase 1+2:**
- `GEMINI_API_KEY` – For the Planner Agent

**Required for full stack (Phase 3+):**
- `TAVILY_API_KEY` – Web research
- `JWT_SECRET_KEY` – User authentication
- `DATABASE_URL` – Research history persistence
- `QDRANT_URL` – Document RAG (local Qdrant needs no API key)

**Optional:**
- `LANGCHAIN_API_KEY` + `LANGCHAIN_TRACING_V2=true` – LangSmith tracing
- `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` – Langfuse tracing
- `HF_TOKEN` – Only for private HuggingFace models

---

## Security Notes

- Passwords are hashed with bcrypt (never stored in plaintext)
- JWT tokens expire after 30 minutes (configurable)
- CORS is configured to allow only the frontend URL
- Web pages and uploaded documents are treated as untrusted data
- API keys are loaded from environment variables, never hardcoded
- Secret values are never printed in logs

---

## Portfolio Highlights

This project demonstrates:

- **Multi-agent AI systems** with LangGraph StateGraph, conditional routing, and retry logic
- **Production FastAPI** with Pydantic validation, structured logging, and centralized error handling
- **Real RAG pipeline** with HuggingFace embeddings, Qdrant vector store, and metadata filtering
- **Fact verification** that distinguishes claim support levels (VERIFIED / PARTIALLY_SUPPORTED / UNSUPPORTED)
- **Streaming UX** with Server-Sent Events for live agent progress
- **JWT authentication** with bcrypt password hashing
- **Alembic database migrations** with SQLAlchemy ORM
- **Docker Compose** for reproducible full-stack deployment
- **Clean architecture** with separated concerns across agents, API, services, and database layers

---

## License

MIT — Free to use for portfolio and educational purposes.
