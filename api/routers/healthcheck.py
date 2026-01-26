from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """기본 헬스체크"""
    return {
        "status": "healthy", 
        "service": "quick-agent-poc",
        "version": "0.1.0",
        "message": "Quick Agent POC API is running!"
        }