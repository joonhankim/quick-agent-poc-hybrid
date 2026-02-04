from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routers.chat import router as chat_router
from api.routers.healthcheck import router as healthcheck_router 
from api.routers.db import router as db_router

from api.core.logger import APILogger
from middleware.cors import add_cors_middleware
from middleware.performance import PerformanceMiddleware
from db import verify_cosmosdb_connection

logger = APILogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Agent FastAPI 서버 시작")    # CosmosDB 연결 확인
    verify_cosmosdb_connection()

    yield
    # Shutdown
    logger.info("Agent FastAPI 서버 종료")


def create_app():
    app = FastAPI(
        title="Quick Agent POC API",
        description="Azure OpenAI 기반 채팅 API",
        version="0.1.0",
        lifespan=lifespan
    )
    # [Middleware] 성능 로깅 미들웨어 추가 (가장 먼저 실행되도록 상단 배치 권장)
    app.add_middleware(PerformanceMiddleware)
    
    # CORS 설정 - Frontend와 통신 허용
    add_cors_middleware(app)

    # 라우터 등록
    app.include_router(chat_router, prefix="/agent", tags=["chat"])
    app.include_router(healthcheck_router, prefix="/agent", tags=["healthcheck"])
    app.include_router(db_router, prefix="/db", tags=["get_history"])
    return app

app = create_app()
