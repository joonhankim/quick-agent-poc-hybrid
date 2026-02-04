# HD현대 법무 지원 Agent (Hybrid Edition)

LangGraph와 CrewAI를 결합한 하이브리드 아키텍처 기반의 법무 지원 AI 시스템입니다.  
엔터프라이즈 환경에서의 안정성(Stability)과 AI의 자율성(Autonomy)을 동시에 추구하며, 보안이 중요한 금융 및 기업 환경에 최적화되어 있습니다.

## 🎯 프로젝트 목적 (Purpose)

본 프로젝트는 다음과 같은 목적을 달성하기 위해 설계되었습니다.

1.  **법무 업무 자동화**: 복잡한 법률 질의에 대해 판례/사규를 검색하고 정밀한 분석 리포트를 제공합니다.
2.  **하이브리드 AI 제어**: LangGraph의 엄격한 상태 관리와 CrewAI의 자율적 문제 해결 능력을 결합하여 환각을 최소화합니다.
3.  **엔터프라이즈 레벨의 신뢰성**: 답변 품질이 낮을 경우 자동으로 재검토하는 FSM(Finite State Machine) 기반의 Self-Healing 메커니즘을 포함합니다.
4.  **보안 및 확장성**: Azure Private 환경 내에서 동작하며, 대화 맥락을 영구 저장(Persistence)하고 복구할 수 있는 아키텍처를 제공합니다.

## 🏗 시스템 아키텍처 (System Architecture)

전체 시스템은 **Next.js 기반의 Frontend**, **FastAPI 기반의 Backend**, 그리고 **LangGraph/CrewAI 기반의 AI Core**로 구성되어 있습니다.

```plaintext
quick-agent-poc/
├── frontend/                 # Frontend Application (Next.js 15, React 19)
│   └── ...                   # Assistant UI & Chat Interface
├── api/                      # Main Backend API (FastAPI)
│   ├── main.py               # App Entrypoint (SSE, Websocket)
│   └── routers/              # Chat Logic Router
├── backend/                  # Support Backend Service (FastAPI)
│   └── api/routers/db        # DB Interaction (History, Metadata)
├── agent/                    # AI Core (Hybrid Architecture)
│   ├── graph/                # LangGraph (Orchestrator + Persistence)
│   ├── crews/                # CrewAI (Legal/Search Expert Team)
│   └── tools/                # Azure AI Search & RAG Tools
└── db/                       # Database Connections (CosmosDB, etc.)
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
    - "죄송합니다"와 같은 불완전한 답변을 사용자에게 그대로 노출하지 않고, 내부적으로 개선을 시도합니다.

4.  **상태 영속성 (Persistence)**:
    - `MemorySaver` 및 `CosmosDB`를 통해 대화의 Context를 스레드별로 안전하게 저장하고 복구합니다.
    - 서버 재시작 시에도 이전 대화 맥락을 유지할 수 있습니다.

## 🛠 기술 스택 (Tech Stack)

| 영역 | 기술 스택 |
| :--- | :--- |
| **Frontend** | Next.js 15, React 19, Assistant UI, TailwindCSS |
| **Backend** | Python 3.13+, FastAPI (Async), UV (Package Manager) |
| **Agent** | LangGraph (Orchestration), CrewAI (Multi-Agent), LangChain |
| **AI / Model** | Azure OpenAI (GPT-4o), Azure AI Search (Vector RAG) |
| **DB / Infra** | Azure CosmosDB (History), Redis (Session), Phoenix (Monitoring) |
