# HD현대 법무 지원 Agent (Hybrid Edition)

LangGraph와 CrewAI를 결합한 하이브리드 아키텍처 기반의 법무 지원 AI 시스템입니다.
엔터프라이즈 환경에서의 안정성(Stability)과 AI의 자율성(Autonomy)을 동시에 추구하며, 보안이 중요한 금융 및 기업 환경에 최적화되어 있습니다.

## 🎯 프로젝트 목적 (Purpose)

본 프로젝트는 다음과 같은 목적을 달성하기 위해 설계되었습니다.

1.  **법무 업무 자동화**: 복잡한 법률 질의에 대해 판례/사규를 검색하고 정밀한 분석 리포트를 제공합니다.
2.  **하이브리드 AI 제어**: LangGraph의 엄격한 상태 관리와 CrewAI의 자율적 문제 해결 능력을 결합하여 환각을 최소화합니다.
3.  **엔터프라이즈 레벨의 신뢰성**: 답변 품질이 낮을 경우 자동으로 재검토하는 FSM(Finite State Machine) 기반의 Self-Healing 메커니즘을 포함합니다.
4.  **보안 및 확장성**: Azure Private 환경 내에서 동작하며, 대화 맥락을 CosmosDB에 영구 저장(Persistence)하고 복구할 수 있는 아키텍처를 제공합니다.

## 🏗 시스템 아키텍처 (System Architecture)

전체 시스템은 **Next.js 기반의 Frontend**, **FastAPI 기반의 Backend**, 그리고 **LangGraph/CrewAI 기반의 AI Core**로 구성되어 있습니다.

```plaintext
quick-agent-poc/
├── frontend/                 # Frontend Application (Next.js 15, React 19)
│   └── ...                   # Assistant UI & Chat Interface
├── api/                      # Main Backend API (FastAPI)
│   ├── main.py               # App Entrypoint (SSE Streaming)
│   └── routers/              # Chat Logic Router (/agent/chat)
├── backend/                  # Support Backend Service (FastAPI)
│   └── api/routers/db        # DB Interaction (History, Metadata)
├── agent/                    # AI Core (Hybrid Architecture)
│   ├── graph/                # LangGraph (Orchestrator + Persistence)
│   ├── node/                 # Graph Nodes (Router, Chat, Crew, Validation)
│   ├── schema/               # State Definition (AgentState)
│   ├── crews/                # CrewAI (Legal/Research Expert Teams)
│   └── tools/                # Azure AI Search (with In-Memory Cache)
├── db/                       # Database Connections (CosmosDB)
└── config/                   # Configuration (Azure Key Vault, .env)
```

### 🧠 핵심 설계 철학 (Engineering Principles)

1.  **Hybrid Orchestration**:
    - **LangGraph**가 전체 상태(State)와 흐름을 통제하며 루프와 에러를 관리합니다.
    - **CrewAI**가 복잡한 법률 분석 업무를 전문가 팀(검색-분석/작성) 단위로 수행합니다.

2.  **비동기 & 논블로킹 (Async/Await)**:
    - LLM 및 Tool 호출 시 `blocking I/O`를 제거하여 동시 처리 성능을 극대화했습니다.
    - CrewAI(동기)는 `asyncio.to_thread()`로 별도 스레드에서 실행하여 이벤트 루프 차단을 방지합니다.

3.  **FSM 기반 품질 보증 (Self-Healing)**:
    - 답변 품질이 낮거나 오류 발생 시, `Validation Node`가 이를 감지하고 자동으로 재시도(최대 1회)합니다.
    - "죄송합니다"와 같은 불완전한 답변을 사용자에게 그대로 노출하지 않고, 내부적으로 개선을 시도합니다.

4.  **상태 영속성 (Persistence)**:
    - `MemorySaver` 및 `CosmosDB`를 통해 대화의 Context를 스레드별로 안전하게 저장하고 복구합니다.
    - 서버 재시작 시에도 이전 대화 맥락을 유지할 수 있습니다.

5.  **Latency 최적화**:
    - CrewAI 에이전트를 3개에서 2개로 통합하여 LLM 호출 횟수를 절감합니다.
    - Azure AI Search 결과 및 Crew 실행 결과에 인메모리 TTL 캐시(1시간)를 적용합니다.
    - 동일한 법률 질문 재요청 시 Crew 전체 실행을 건너뛰고 즉시 캐시된 결과를 반환합니다.

## 🔄 그래프 플로우 (Graph Flow)

LangGraph 기반의 5개 노드로 구성된 FSM 흐름입니다.

```plaintext
START → start_node → router_node ─┬─ "general" → general_chat_node → END
                                   │
                                   └─ "legal" → crew_collaboration_node → validation_node ─┬─ "passed" → END
                                                        ↑                                   │
                                                        └─── "retry" (max 1회) ─────────────┘
                                                                                            │
                                                                                     "failed" → END
```

| 노드 | 역할 |
| :--- | :--- |
| **start_node** | 상태 초기화 |
| **router_node** | 의도 분류 (키워드 Fast Path + LLM Slow Path) |
| **general_chat_node** | 일반 대화 처리 (RAG 없이 LLM 직접 응답) |
| **crew_collaboration_node** | CrewAI 법률 전문가 팀 실행 (`asyncio.to_thread`) |
| **validation_node** | 답변 품질 검증 및 재시도 판단 (최대 1회) |

## 👥 CrewAI 에이전트 구성

### Legal RAG Crew (법무지원)

| 에이전트 | 역할 | 도구 |
| :--- | :--- | :--- |
| **Search Specialist** | 법률 문서 검색 (키워드 추출 → Azure AI Search) | AzureSearchTool |
| **Legal Expert** | 법률 분석 + 사용자 친화적 답변 작성 (통합) | 없음 (텍스트 처리) |

- **프로세스**: Sequential (검색 → 분석/작성)
- **캐싱**: Crew 결과 전체를 `user_query` 기준으로 1시간 TTL 캐시

### Research Crew (일반 리서치)

| 에이전트 | 역할 |
| :--- | :--- |
| **Researcher** | 전문 리서치 분석 |
| **Editor** | 시니어 콘텐츠 에디팅 |

## ⚡ Latency 최적화

법률 질문 경로의 응답 속도를 개선하기 위해 다음 최적화가 적용되어 있습니다.

| 최적화 | 내용 | 효과 |
| :--- | :--- | :--- |
| **에이전트 통합** | legal_analyst + legal_writer → legal_expert (3→2 에이전트) | LLM 호출 1회 절감 |
| **재시도 축소** | max_retries 3 → 1 | 최악의 경우 latency 1/3 |
| **Search 캐시** | Azure AI Search 결과 인메모리 TTL 캐시 (1시간) | 동일 검색어 API 호출 생략 |
| **Crew 결과 캐시** | user_query 기준 Crew 전체 결과 캐시 (1시간) | 동일 질문 즉시 응답 |

## 🔌 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
| :--- | :--- | :--- |
| `/agent/chat` | POST | 법률/일반 질문 처리 (SSE 스트리밍 응답) |
| `/agent/health` | GET | 헬스 체크 |
| `/db/room_list` | GET | 대화방 목록 조회 |
| `/db/room_history` | GET | 대화 히스토리 조회 |

- **SSE 스트리밍**: Vercel AI SDK 프로토콜 호환 (`text/event-stream`)
- **대화 히스토리**: CosmosDB에서 최근 10턴을 로드하여 멀티턴 대화 지원

## 🛠 기술 스택 (Tech Stack)

| 영역 | 기술 스택 |
| :--- | :--- |
| **Frontend** | Next.js 15, React 19, Assistant UI, TailwindCSS, Zustand |
| **Backend** | Python 3.13+, FastAPI (Async), UV (Package Manager) |
| **Agent** | LangGraph (Orchestration), CrewAI (Multi-Agent), LangChain, LiteLLM |
| **AI / Model** | Azure OpenAI (GPT-5.1 Primary, GPT-4o Fallback), Azure AI Search (Semantic RAG) |
| **DB / Infra** | Azure CosmosDB (History/Persistence), Azure Key Vault (Secrets) |
