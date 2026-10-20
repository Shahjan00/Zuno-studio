"""Project persistence endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter(prefix="/api/projects", tags=["projects"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession) -> Project:
    """Create a project metadata record."""
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Project]:
    """Return the most recently created project records."""
    statement = select(Project).order_by(Project.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())
