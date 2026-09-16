from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = ""
    repository_url: str | None = None

class ProjectResponse(ProjectCreate):
    id: int
    created_at: datetime

class RunCreate(BaseModel):
    project_id: int
    task: str = Field(min_length=5, max_length=5000)
    code: str = ""

class RunResponse(BaseModel):
    id: int
    project_id: int
    task: str
    status: str
    result: dict[str, Any]
    created_at: datetime
