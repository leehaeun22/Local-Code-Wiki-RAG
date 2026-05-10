# Local-Code-Wiki-RAG

Local-Code-Wiki-RAG is a developer onboarding platform that analyzes GitHub repositories, generates code documentation, and helps new or mid-project developers understand a codebase through a RAG-based chatbot.

## Project Purpose

This project aims to reduce onboarding time by turning repository source code into searchable documentation and contextual chat answers. It will support code analysis, document generation, semantic search, and AI-assisted project Q&A.

## Tech Stack

### Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Query
- Zustand

### Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic
- PostgreSQL
- Celery
- Redis

### AI

- OpenAI or Gemini API
- ChromaDB
- tree-sitter
- RAG pipeline
- Translation support
- Future Ollama local mode support

## Main Features

- GitHub repository registration
- Repository cloning and file scanning
- Source code analysis
- Automatic code documentation generation
- File tree and document viewer
- RAG-based chatbot for codebase Q&A
- Translation support

## Planned Features

- Frontend layout
- Project registration page
- Project detail page
- File tree page
- Document viewer page
- Chatbot UI
- Backend project API
- GitHub repository clone API
- File scan API
- Code chunking
- Embedding storage
- RAG search
- Chatbot answer generation
- Automatic documentation generation
- Translation workflow
- GitHub webhook integration
- Deployment setup

## Getting Started

Backend:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8888
```

Frontend:

```powershell
cd frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8888"
npm run dev
```

Swagger:

```text
http://127.0.0.1:8888/docs
```

## Docker Compose

Start local infrastructure services:

```bash
docker compose up -d
```

Services:

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- ChromaDB: `localhost:8001`

Copy the environment example before running backend services:

```bash
cp .env.example backend/.env
```
