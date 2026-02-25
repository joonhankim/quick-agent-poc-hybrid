#!/bin/bash

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 로그 파일
AGENT_LOG="logs/agent.log"
SERVICE_LOG="logs/service.log"
FRONTEND_LOG="logs/frontend.log"

# PID 파일
AGENT_PID="/tmp/agent.pid"
SERVICE_PID="/tmp/service.pid"
FRONTEND_PID="/tmp/frontend.pid"
SSH_TUNNEL_PID="/tmp/ssh_tunnel.pid"
# 바이트코드 캐싱 방지
export PYTHONDONTWRITEBYTECODE=1

# .env 파일에서 환경변수 로드 (CrewAI 등 외부 라이브러리용)
if [ -f ".env" ]; then
    echo -e "${BLUE}.env 파일에서 환경변수 로드 중...${NC}"
    # .env 파일에서 유효한 bash 변수명(하이픈 제외)만 export
    # 주석, 빈 줄 제외하고 KEY=VALUE 형식의 라인만 처리
    while IFS= read -r line || [ -n "$line" ]; do
        # 주석과 빈 줄 건너뛰기
        if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
            continue
        fi
        # KEY=VALUE 형식 파싱 (하이픈이 있는 키는 제외)
        if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            export "$line"
        fi
    done < .env
    echo -e "${GREEN}✓ 환경변수 로드 완료${NC}"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Quick Agent POC 서버 시작${NC}"
echo -e "${GREEN}========================================${NC}"

# 기존 프로세스 정리
cleanup() {
    echo -e "\n${YELLOW}서버를 종료합니다...${NC}"

    if [ -f "$AGENT_PID" ]; then
        APID=$(cat "$AGENT_PID")
        if ps -p $APID > /dev/null 2>&1; then
            echo -e "${BLUE}Agent API 서버 종료 (PID: $APID)${NC}"
            kill $APID
        fi
        rm -f "$AGENT_PID"
    fi

    if [ -f "$SERVICE_PID" ]; then
        SPID=$(cat "$SERVICE_PID")
        if ps -p $SPID > /dev/null 2>&1; then
            echo -e "${BLUE}Service Backend 서버 종료 (PID: $SPID)${NC}"
            kill $SPID
        fi
        rm -f "$SERVICE_PID"
    fi

    if [ -f "$FRONTEND_PID" ]; then
        FPID=$(cat "$FRONTEND_PID")
        if ps -p $FPID > /dev/null 2>&1; then
            echo -e "${BLUE}Frontend 서버 종료 (PID: $FPID)${NC}"
            kill $FPID
        fi
        rm -f "$FRONTEND_PID"
    fi

    # tail 프로세스 종료
    if [ -n "$TAIL_PID" ] && ps -p $TAIL_PID > /dev/null 2>&1; then
        echo -e "${BLUE}로그 출력 프로세스 종료 (PID: $TAIL_PID)${NC}"
        kill $TAIL_PID
    fi

    echo -e "${GREEN}서버가 종료되었습니다.${NC}"
    exit 0
}

# Ctrl+C 시그널 처리
trap cleanup SIGINT SIGTERM

# 로그 디렉토리 생성
mkdir -p logs

# 1. Agent API 서버 시작 (uvicorn - port 8000)
echo -e "${BLUE}[1/3] Agent API 서버 시작 중...${NC}"
echo -e "${YELLOW}      포트: 8000${NC}"
echo -e "${YELLOW}      로그: $AGENT_LOG${NC}"

# 가상환경 활성화 및 uvicorn 실행
source .venv/bin/activate
# FORCE_COLORS 환경변수 설정하여 파일 리다이렉트 시에도 컬러 유지
FORCE_COLORS=true ENVIRONMENT=local LOG_LEVEL=INFO uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "$AGENT_LOG" 2>&1 &
AGENT_PID_NUM=$!
echo $AGENT_PID_NUM > "$AGENT_PID"

echo -e "${GREEN}✓ Agent API 서버 시작됨 (PID: $AGENT_PID_NUM)${NC}"
sleep 2

# 2. Service Backend 서버 시작 (uvicorn - port 8001)
echo -e "${BLUE}[2/3] Service Backend 서버 시작 중...${NC}"
echo -e "${YELLOW}      포트: 8001${NC}"
echo -e "${YELLOW}      로그: $SERVICE_LOG${NC}"

# 가상환경은 이미 활성화되어 있음
FORCE_COLORS=true ENVIRONMENT=local uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload > "$SERVICE_LOG" 2>&1 &
SERVICE_PID_NUM=$!
echo $SERVICE_PID_NUM > "$SERVICE_PID"

echo -e "${GREEN}✓ Service Backend 서버 시작됨 (PID: $SERVICE_PID_NUM)${NC}"
sleep 2

# 3. Frontend 서버 시작 (Next.js - port 3000)
echo -e "${BLUE}[3/3] Frontend 서버 시작 중...${NC}"
echo -e "${YELLOW}      포트: 3000${NC}"
echo -e "${YELLOW}      로그: $FRONTEND_LOG${NC}"

cd frontend
npm run dev > "../$FRONTEND_LOG" 2>&1 &
FRONTEND_PID_NUM=$!
cd ..
echo $FRONTEND_PID_NUM > "$FRONTEND_PID"

echo -e "${GREEN}✓ Frontend 서버 시작됨 (PID: $FRONTEND_PID_NUM)${NC}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  서버가 성공적으로 시작되었습니다!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Frontend:        ${NC}http://localhost:3000"
echo -e "${BLUE}Agent API:       ${NC}http://localhost:8000"
echo -e "${BLUE}Service Backend: ${NC}http://localhost:8001"
echo -e "${BLUE}Agent API Docs:  ${NC}http://localhost:8000/docs"
echo -e "${BLUE}Service Docs:    ${NC}http://localhost:8001/docs"

# 브라우저 열기 시도 (macOS, Linux 우선 처리)
OPEN_URL="http://localhost:3000"
if command -v open >/dev/null 2>&1; then
    open "$OPEN_URL"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$OPEN_URL" >/dev/null 2>&1 &
elif command -v start >/dev/null 2>&1; then
    start "$OPEN_URL"
else
    echo -e "${YELLOW}브라우저 자동 실행 실패: ${OPEN_URL}${NC}"
fi

# 로그 실시간 출력 (Agent API 로그 우선 출력)
echo -e "${BLUE}=== Agent API 로그 ===${NC}"
tail -f "$AGENT_LOG" &
TAIL_PID=$!

# 프로세스가 종료될 때까지 대기
wait