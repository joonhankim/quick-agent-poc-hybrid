import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from api.core.logger import APILogger

logger = APILogger()

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # 0.5초 이상 걸리는 요청만 warning으로 로깅 (슬로우 쿼리 감지 효과)
        if process_time > 0.5:
             logger.info(f"Slow Request Detected: path={request.url.path} process_time={process_time:.4f}s")
        else:
             # 너무 시끄러울 수 있으므로 debug 레벨 권장
             # 여기서는 학습 목적으로 info로 찍습니다.
             logger.info(f"Request Processed: path={request.url.path} process_time={process_time:.4f}s")
             
        response.headers["X-Process-Time"] = str(process_time)
        return response
