# HD현대 법무 지원 Agent (Hybrid Edition)
 
 LangGraph와 CrewAI를 결합한 하이브리드 아키텍처 기반의 법무 지원 AI 시스템입니다. 엔터프라이즈 환경에서의 안정성(Stability)과 AI의 자율성(Autonomy)을 동시에 추구합니다.

## ️ 시스템 아키텍처

```
quick-agent-poc-hybrid/
├── api/                      # Backend API (FastAPI)
│   ├── main.py              # App Entrypoint + Middleware
│   ├── routers/             # SSE Chat Router
│   └── core/                # Logger, Singleton utils
├── agent/                   # AI Core (Hybrid Architecture)
│   ├── graph/core_graph.py  # LangGraph (Orchestrator + Persistence)
│   ├── node/core_node.py    # Async Nodes + Validation Logic
│   ├── crews/               # CrewAI (Legal Expert Team)
│   └── tools/               # Azure AI Search Tools
└── middleware/              # Performance & CORS Middlewares
```

### 🧠 핵심 설계 철학 (Engineering Principles)

1.  **Hybrid Orchestration**: 
    - **LangGraph**가 전체 상태(State)와 흐름을 통제하며 루프와 에러를 관리합니다.
    - **CrewAI**가 복잡한 법률 분석 업무를 전문가 팀(검색-분석-작성) 단위로 수행합니다.

2.  **비동기 & 논블로킹 (Async/Await)**: 
    - LLM 및 Tool 호출 시 `blocking I/O`를 제거하여 동시 처리 성능을 극대화했습니다.
    - Python의 `asyncio`를 활용하여 고성능 API 서버를 구현했습니다.

3.  **FSM 기반 품질 보증 (Self-Healing)**: 
    - 답변 품질이 낮거나 오류 발생 시, `Validation Node`가 이를 감지하고 자동으로 재시도(Retry) 사이클을 돕니다.
    - "죄송합니다"와 같은 불완전한 답변을 사용자에게 그대로 노출하지 않습니다.

4.  **상태 영속성 (Persistence)**: 
    - `MemorySaver` 체크포인팅을 통해 대화의 Context를 스레드별로 안전하게 저장하고 복구합니다.
    - 서버 장애나 재시작 시에도 대화 맥락 유지 가능 (DB 확장 용이).

## �️ 기술 스택

- **Core**: Python 3.13+, LangChain 0.3+, FastAPI
- **Agent Engines**: LangGraph (Flow Control), CrewAI (Multi-Agent)
- **AI Models**: GPT-4o (Reasoning), Azure AI Search (RAG)
- **Infrastructure**: Azure OpenAI, CosmosDB (History)
- **Package Manager**: `uv` (Fast Python Package Installer)

## 🚀 실행 방법

### 1. 환경 설정
`uv`를 사용하여 의존성을 빠르게 설치합니다.
```bash
# 의존성 설치
uv sync

# .env 설정
cp .env.example .env
# (API Key 입력 필요)
```

### 2. 서버 실행
통합 스크립트로 백엔드와 프론트엔드(선택)를 동시에 실행합니다.
```bash
./start.sh
```
또는 백엔드만 개별 실행:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
