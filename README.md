# ZUNO

ZUNO is an educational AI website builder. The FastAPI backend runs the LangGraph agent and provides endpoints for submitting prompts and viewing generated website files.

## Start the backend

Set `GOOGLE_API_KEY` in `.env` to your Gemini API key. Install dependencies and run from the repository root:

```sh
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The API docs are at <http://127.0.0.1:8000/docs> and health is at <http://127.0.0.1:8000/api/health>. Available endpoints:

- `POST /api/chat` with `{"prompt":"Build a portfolio website for a photographer"}` runs the graph.
- `GET /api/files` lists generated files; `GET /api/files/{path}` returns a file's text.
- `GET /preview` serves the generated `index.html`; `/preview/...` serves linked CSS, JS, and other assets.

Generated files are saved in `backend/generated_project`. Set `CORS_ORIGINS` in `.env` to the deployed frontend origin when hosting the frontend separately. Chat history is not persisted yet.

For a container or hosting service, use the start command `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT` and configure `GOOGLE_API_KEY` plus `CORS_ORIGINS` in the host's environment settings.

## Start the frontend

In another terminal:

```sh
cd frontend
npm install
npm run dev
```
