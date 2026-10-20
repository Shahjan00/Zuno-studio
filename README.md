# ZUNO

ZUNO is an educational AI website builder. Its first milestone establishes a React + TypeScript frontend and a FastAPI backend. Later milestones will add the LangGraph workflow, Gemini integration, PostgreSQL persistence, and isolated website generation and testing.

## Prerequisites

- Python 3.11 or newer
- Node.js 20.19+ or 22.12+
- npm

## Start the backend

From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is available at <http://127.0.0.1:8000/api/health>; interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Start the frontend

In a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Vite prints the local address (normally <http://localhost:5173>). The frontend's `VITE_API_BASE_URL` setting points to the local FastAPI server by default.

## Development phases

The project is built incrementally. See the project brief for the full roadmap; the current skeleton intentionally has no database, LLM integration, or website-generation workflow yet.
