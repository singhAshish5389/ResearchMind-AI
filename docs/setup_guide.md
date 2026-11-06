# ResearchMind AI – Setup Guide

## System Requirements

- Python 3.11 or higher
- Node.js 18 or higher
- Git
- (Optional) Docker Desktop for containerized setup

## Step-by-Step Setup

### Step 1 – Clone the repository

```bash
git clone https://github.com/yourusername/researchmind-ai.git
cd researchmind-ai
```

### Step 2 – Create and configure .env

```bash
cp .env.example .env
```

Edit `.env` with your actual values. See the table below.

### Step 3 – Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Start the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

### Step 4 – Frontend

```bash
cd frontend
npm install
npm run dev
```

### Step 5 – Run tests

```bash
cd backend
pytest -v
```

---

## API Keys

| Variable | Service | Required | How to Get |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini | Phase 2+ | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) – Free tier available |
| `TAVILY_API_KEY` | Tavily | Phase 3+ | [tavily.com](https://tavily.com) – Free tier: 1000 searches/month |
| `JWT_SECRET_KEY` | Auth | Phase 6+ | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `LANGCHAIN_API_KEY` | LangSmith | Optional | [smith.langchain.com](https://smith.langchain.com) – Free account |
| `HF_TOKEN` | HuggingFace | Optional | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) – Only for gated models |

---

## Local Services (Without Docker)

### PostgreSQL

Install from: https://www.postgresql.org/download/

```bash
# Create the database
psql -U postgres
CREATE DATABASE researchmind;
\q
```

Set `DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/researchmind`

### Qdrant

Download from: https://qdrant.tech/documentation/guides/installation/

```bash
# Run locally
qdrant
```

Or with Docker:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

Set `QDRANT_URL=http://localhost:6333` (no API key needed for local)

---

## Docker Setup (Recommended)

```bash
# Start all services including PostgreSQL and Qdrant
docker compose up --build

# Stop
docker compose down

# Remove all data volumes
docker compose down -v
```

---

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.11+)
- Ensure venv is activated
- Run `pip install -r requirements.txt` again

### Gemini API errors
- Verify `GEMINI_API_KEY` is set in `.env`
- Check model name in `GEMINI_MODEL` (default: `gemini-2.0-flash`)
- Check quota at [aistudio.google.com](https://aistudio.google.com)

### Frontend won't start
- Run `npm install` in the `frontend/` directory
- Check Node version: `node --version` (needs 18+)

### CORS errors
- Ensure `FRONTEND_URL=http://localhost:5173` in `.env`
- Restart the backend after changing `.env`
