from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.projects import router as projects_router
from app.api.runs import router as runs_router
from app.api.health import router as health_router

app = FastAPI(
    title="ForgeAI",
    version="1.0.0",
    description="Multi-Agent Software Engineering Workspace",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(runs_router, prefix="/api")

@app.get("/")
def root():
    return {"name": "ForgeAI", "status": "running", "docs": "/docs"}
