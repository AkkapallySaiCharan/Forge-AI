from fastapi import APIRouter, HTTPException
from app.models.schemas import ProjectCreate, ProjectResponse
from app.database.database import create_project, get_projects, remove_project

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse)
def create(payload: ProjectCreate):
    return create_project(payload.name, payload.description, payload.repository_url)

@router.get("", response_model=list[ProjectResponse])
def list_all():
    return get_projects()

@router.delete("/{project_id}")
def delete(project_id: int):
    if not remove_project(project_id):
        raise HTTPException(404, "Project not found")
    return {"message": "Project deleted"}
