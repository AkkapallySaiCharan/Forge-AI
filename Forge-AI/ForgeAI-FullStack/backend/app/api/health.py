from fastapi import APIRouter
from app.database.database import database_status
from app.services.llm_service import LLMService

router = APIRouter(tags=["Health"])

@router.get("/health")
def health():
    return {"status": "healthy", "database": database_status(), "ai": LLMService().status()}
