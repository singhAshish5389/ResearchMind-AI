# ResearchMind AI – Architecture

## System Overview

ResearchMind AI is a multi-agent autonomous research platform. Users submit a research topic; a team of five specialized AI agents conducts research, verifies facts, and produces a professional report.

## Agent Architecture

```
User Request
     │
     ▼
┌─────────────────┐
│  Planner Agent  │  ◄── Gemini API
│                 │      Generates 5-10 research questions
│  ResearchPlan   │      Returns structured JSON (Pydantic validated)
└────────┬────────┘
         │ Human approval
         ▼
┌─────────────────┐
│ Researcher Agent│  ◄── Tavily Search API
│                 │      Searches per question
│ ResearchSources │      Deduplicates and ranks results
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analyst Agent  │  ◄── Gemini API
│                 │      Identifies themes, trends, risks
│ ResearchAnalysis│      Evidence-linked findings
└────────┬────────┘
         │
         ▼
┌────────────────────┐
│ Fact Checker Agent │  ◄── Gemini API
│                    │      Compares claims to evidence
│  VerifiedClaims    │      VERIFIED / PARTIALLY_SUPPORTED /
└────────┬───────────┘      UNSUPPORTED / CONTRADICTED
         │
    ┌────┴────────────┐
    │  Quality check  │
    │                 │
    │ Insufficient?   │──► Back to Researcher (bounded retries)
    └────┬────────────┘
         │
         ▼
┌──────────────────────┐
│ Report Writer Agent  │  ◄── Gemini API + ReportLab
│                      │      Structured JSON report
│  ResearchReport      │      PDF download
└──────────────────────┘
```

## LangGraph State Machine

```
START → planner_node
          │
          ▼
     plan_approval (human-in-the-loop)
          │
          ▼
     researcher_node ──────────────────────┐
          │                                │
          ▼                                │
     analyst_node                          │
          │                                │
          ▼                                │
     fact_checker_node                     │
          │                                │
          ▼                              retry ≤ 3
     quality_check_node                    │
          │                                │
          ├── NEEDS_MORE_EVIDENCE ─────────┘
          │
          ▼
     report_writer_node
          │
          ▼
     save_report_node
          │
         END
```

## Data Flow

1. **User** submits `ResearchRequest` (topic, depth, mode)
2. **FastAPI** validates with Pydantic, creates research record in PostgreSQL
3. **LangGraph** executes the workflow asynchronously
4. **Progress** is streamed to the frontend via Server-Sent Events
5. **Sources** are stored in PostgreSQL with full metadata
6. **Vectors** from uploaded documents are stored in Qdrant
7. **Report** is generated as JSON (stored in PostgreSQL) and PDF (stored on disk)

## RAG Pipeline

```
Document Upload
      │
      ▼
Text Extraction (pypdf / python-docx)
      │
      ▼
Chunking (configurable size + overlap)
      │
      ▼
Embeddings (HuggingFace sentence-transformers)
      │
      ▼
Qdrant Vector Storage (with metadata)
      │
      ▼
Semantic Search (top-k retrieval)
      │
      ▼
Relevant Context → LLM Generation
```

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| LLM | Google Gemini | Native Python SDK, JSON mode, competitive performance |
| Agent framework | LangGraph | State machine model, native checkpointing, human-in-the-loop |
| Vector DB | Qdrant | Open source, self-hostable, fast, good Python client |
| Embeddings | HuggingFace | Free, local, no API key required |
| Web search | Tavily | Designed for AI agents, structured results, real URLs |
| Database | PostgreSQL | ACID, relational, good for structured research data |
| API | FastAPI | Async, Pydantic-native, auto Swagger docs |
| Auth | JWT + bcrypt | Standard, stateless, secure |
