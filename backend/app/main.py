"""FastAPI application entry point for ZUNO."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.projects import router as projects_router
from app.db import engine

app = FastAPI(
    title="ZUNO API",
    description="API for the ZUNO AI website builder.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(projects_router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Report API and database availability."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "app": "ZUNO", "database": "connected"}
