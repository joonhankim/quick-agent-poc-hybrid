from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.api.routers.db import router as db_router

from api.core.logger import APILogger
from middleware.cors import add_cors_middleware
from db import verify_cosmosdb_connection

logger = APILogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("B/E FastAPI 서버 시작")    # CosmosDB 연결 확인
    verify_cosmosdb_connection()

    yield
    # Shutdown
    logger.info("B/E FastAPI 서버 종료")


def create_app():
    app = FastAPI(
        title="B/E POC API",
        description="B/E POC API",
        version="0.1.0",
        lifespan=lifespan
    )
    # CORS 설정 - Frontend와 통신 허용
    add_cors_middleware(app)

    # 라우터 등록
    app.include_router(db_router, prefix="/db", tags=["get_history"])
    return app

app = create_app()
