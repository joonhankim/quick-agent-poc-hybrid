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

## 📚 법률 데이터 현황 (Legal Data)

Azure AI Search 인덱스(`law-unified-index`)에 적재된 데이터는 **[법제처 Open API](https://open.law.go.kr)**를 통해 수집한 대한민국 공공 법률 데이터입니다.

| 구분 | 건수 | 출처 | 수집 API |
| :--- | ---: | :--- | :--- |
| **법령** | 500건 | 법제처 | 법령 API (`법령검색/목록`) |
| **판례** | 5,000건 | 법제처 | 판례 API (`판례검색/목록`) |
| **합계** | **5,500건** | | |

### 법령 데이터 (500건)

대한민국 현행 법률, 시행령, 시행규칙 등 다양한 법규를 포함합니다.

**하위 유형별 분포:**

| 유형 | 건수 | 비율 |
| :--- | ---: | ---: |
| 법률 | 151건 | 30.2% |
| 시행령 | 130건 | 26.0% |
| 시행규칙 | 82건 | 16.4% |
| 규칙 (기타) | 71건 | 14.2% |
| 규정 | 44건 | 8.8% |
| 직제 | 9건 | 1.8% |
| 기타 | 13건 | 2.6% |

**포함된 주요 법령 (예시):**
건축법, 개인정보 보호법 시행령, 근로기준법, 고등교육법, 경비업법 시행령, 가축분뇨의 관리 및 이용에 관한 법률, 개발이익 환수에 관한 법률 등

### 판례 데이터 (5,000건)

법제처 Open API를 통해 수집한 판결 요지(판시사항) 중심의 판례 데이터입니다.

**판결 연도별 분포:**

| 연도 | 건수 | 비율 |
| :--- | ---: | ---: |
| 2024년 | 2,587건 | 51.7% |
| 2025년 | 2,412건 | 48.3% |

> 2024~2025년 최신 판례로 구성되어 있으며, 가장 최근 판결은 **2025년 12월**입니다.

**법원별 분포 (상위 10개):**

| 법원 | 건수 |
| :--- | ---: |
| 대법원 | 1,146건 |
| (법원 미기재) | 3,421건 |
| 서울고등법원 | 109건 |
| 서울중앙지방법원 | 37건 |
| 서울행정법원 | 33건 |
| 수원고등법원 | 28건 |
| 수원지방법원 | 21건 |
| 서울북부지방법원 | 17건 |
| 대구지방법원 | 17건 |
| 부산고등법원 | 16건 |

> 그 외 전국 40개 이상 법원(광주고등법원, 창원지방법원, 특허법원, 제주지방법원 등) 포함

**사건 유형별 분포 (키워드 기반 추정):**

| 사건 유형 | 건수 | 주요 키워드 |
| :--- | ---: | :--- |
| 조세 (세금) | 1,810건 | 부가가치세, 종합소득세, 증여세, 양도세 등 |
| 부동산 | 179건 | 부동산 거래, 등기, 소유권 등 |
| 채권 | 145건 | 채권 조사, 채무부존재확인 등 |
| 계약 | 142건 | 계약 해지, 이행 등 |
| 손해배상 | 138건 | 손해배상(기), 손해배상(자) 등 |
| 노동/근로 | 90건 | 근로기준법위반, 해고, 임금 등 |
| 가사 (상속) | 89건 | 상속세, 상속재산분할 등 |
| 형사 (사기) | 80건 | 사기, 보험사기 등 |
| 보험 | 54건 | 보험금, 보험계약 등 |
| 지식재산 | 37건 | 특허, 저작권 등 |
| 기타 | 2,097건 | 행정, 파산, 회생 등 |

> 조세 관련 판례가 전체의 약 36%로 가장 높은 비중을 차지합니다.

### 예시 데이터

**판례 예시:**

```json
{
  "id": "prec_241657",
  "title": "손해배상(기)",
  "content": "[손해배상(기)]",
  "source": "법제처_판례",
  "category": "판례",
  "case_number": "2023다249456",
  "decision_date": "2024.05.30",
  "court": "대법원",
  "law_number": ""
}
```

**법령 예시:**

```json
{
  "id": "law_234693",
  "title": "건설근로자의 고용개선 등에 관한 법률",
  "content": "[건설근로자의 고용개선 등에 관한 법률]",
  "source": "법제처_법령",
  "category": "법률",
  "case_number": "",
  "decision_date": "",
  "court": "",
  "law_number": ""
}
```

> `content` 필드에는 법령명 또는 판결 요지(판시사항)가 저장되어 있으며,
> Azure AI Search의 시맨틱 검색을 통해 질문과의 관련성을 판단합니다.

### 인덱스 스키마

| 필드 | 타입 | 설명 | 법령 | 판례 |
| :--- | :--- | :--- | :---: | :---: |
| `id` | string | 문서 고유 ID | `law_*` | `prec_*` |
| `title` | string | 법령명 또는 사건명 | O | O |
| `content` | string | 법령명 또는 판결 요지 | O | O |
| `source` | string | 출처 구분 | 법제처_법령 | 법제처_판례 |
| `category` | string | 문서 유형 | 법률 | 판례 |
| `law_number` | string | 법률/조항 번호 | - | - |
| `case_number` | string | 사건번호 | - | O |
| `decision_date` | string | 판결일 | - | O |
| `court` | string | 법원명 | - | O |

### 검색 방식

- **시맨틱 하이브리드 검색**: 키워드 매칭 + 시맨틱 리랭킹(`legal-semantic-config`)
- **인메모리 캐시**: 동일 쿼리 1시간 TTL 캐시로 반복 호출 시 API 비용 절감
- **기본 반환 수**: 쿼리당 상위 5건 (관련성 점수 기준 정렬)

## 🛠 기술 스택 (Tech Stack)

| 영역 | 기술 스택 |
| :--- | :--- |
| **Frontend** | Next.js 15, React 19, Assistant UI, TailwindCSS, Zustand |
| **Backend** | Python 3.13+, FastAPI (Async), UV (Package Manager) |
| **Agent** | LangGraph (Orchestration), CrewAI (Multi-Agent), LangChain, LiteLLM |
| **AI / Model** | Azure OpenAI (GPT-5.1 Primary, GPT-4o Fallback), Azure AI Search (Semantic RAG) |
| **DB / Infra** | Azure CosmosDB (History/Persistence), Azure Key Vault (Secrets) |
