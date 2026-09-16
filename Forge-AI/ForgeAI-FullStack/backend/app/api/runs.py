from fastapi import APIRouter, HTTPException
from app.models.schemas import RunCreate, RunResponse
from app.database.database import project_exists, get_runs, get_run
from app.orchestration.orchestrator import Orchestrator

router = APIRouter(prefix="/runs", tags=["Runs"])
orchestrator = Orchestrator()

@router.post("", response_model=RunResponse)
def run(payload: RunCreate):
    if not project_exists(payload.project_id):
        raise HTTPException(404, "Project not found")
    result = orchestrator.execute(payload.task, payload.code)
    return orchestrator.persist(payload.project_id, payload.task, payload.code, result)

@router.get("", response_model=list[RunResponse])
def history():
    return get_runs()

@router.get("/{run_id}", response_model=RunResponse)
def detail(run_id: int):
    result = get_run(run_id)
    if not result:
        raise HTTPException(404, "Run not found")
    return result
