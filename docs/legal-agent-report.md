# HD현대 법무 지원 AI Agent 기술 보고서

## 1. 개요

본 문서는 HD현대 법무 지원 AI Agent 시스템의 기술적 구성, 데이터 전략, 보안 아키텍처를 설명합니다. 이 시스템은 **LangGraph**(상태 기반 오케스트레이션)와 **CrewAI**(멀티 에이전트 협업)를 결합한 하이브리드 아키텍처로, Azure 클라우드 환경에서 법률 질의에 대한 RAG(Retrieval-Augmented Generation) 기반 응답을 제공합니다.

---

## 2. 데이터 전략

### 2.1 데이터 소스 및 수집

모든 데이터는 **법제처 Open API**(https://open.law.go.kr)에서 수집한 대한민국 공공 법률 데이터입니다.

| 구분 | 건수 | 수집 API | RAG 활용 |
| :--- | ---: | :--- | :---: |
| 법령 (조문 전문) | 1,001건 | 법령 API (`법령검색/목록` + 조문 전문) | O |
| 판례 (사건명만) | 5,000건 | 판례 API (`판례검색/목록`) | X |
| **합계** | **6,001건** | | |

### 2.2 왜 법령 조문 전문인가

RAG 시스템의 품질은 검색 소스의 **텍스트 밀도**에 직접 의존합니다. 데이터 선정 시 다음을 고려했습니다.

**법령 데이터 (채택)**
- 법제처 법령 API가 조문 전문을 JSON 필드로 제공하여 구조화된 수집이 가능
- 전체 1,001건 중 **94.4%가 500자 초과의 실질적 법령 본문** 보유 (평균 6,388자)
- 시맨틱 검색 시 질문과 조문 내용 간 의미적 매칭이 가능

**판례 데이터 (제외 사유)**
- 법제처 판례 API의 구조적 한계: 상세 조회 시 판결 전문(판시사항, 판결요지)을 **JSON 필드로 제공하지 않음**
- `content` 필드에 사건명(`[손해배상(기)]`)만 저장되어 시맨틱 검색 시 의미 있는 매칭 불가
- HTML 본문으로만 제공되어 자동화된 구조화 수집이 불가

### 2.3 법령 데이터 품질 분석

**content 길이 분포:**

| content 길이 | 건수 | 비율 |
| :--- | ---: | ---: |
| ~50자 (제목만) | 2건 | 0.2% |
| 51~500자 | 54건 | 5.4% |
| 501~2,000자 | 248건 | 24.8% |
| 2,001~10,000자 | 515건 | 51.4% |
| 10,001~30,000자 | 155건 | 15.5% |
| 30,001~50,000자 | 27건 | 2.7% |

**하위 유형별 분포:**

| 유형 | 본문 보유 | 제목만 | 합계 |
| :--- | ---: | ---: | ---: |
| 법률 | 282건 | 9건 | 291건 |
| 시행령 | 244건 | 3건 | 247건 |
| 시행규칙 | 163건 | 5건 | 168건 |
| 규칙 | 134건 | 19건 | 153건 |
| 규정 | 74건 | 10건 | 84건 |
| 직제 | 22건 | 0건 | 22건 |
| 기타 | 26건 | 10건 | 36건 |

> 건축법 시행령, 공직선거법 등 대형 법령은 50,000자에서 truncation이 적용되어 있습니다.

---

## 3. 시스템 아키텍처

### 3.1 전체 구조

```
┌──────────────────────────────────────────────────────────────┐
│                   Frontend (Next.js 15 / React 19)            │
│                   Assistant UI + TailwindCSS + Zustand         │
│                   http://localhost:3000                        │
└──────────────────────┬───────────────────────────────────────┘
                       │ SSE Streaming (Vercel AI SDK 프로토콜)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              Main API Server (FastAPI, Port 8000)              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ POST /agent/chat                                         │ │
│  │  1. CosmosDB에서 최근 10턴 히스토리 로드                  │ │
│  │  2. AgentState 생성 + AsyncIO 큐 인프라 구성              │ │
│  │  3. LangGraph 실행 (astream)                             │ │
│  │  4. SSE 토큰 스트리밍 → 클라이언트                        │ │
│  │  5. 대화 저장 (Background Task)                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│  Middleware: PerformanceMiddleware + CORSMiddleware            │
└──────────┬──────────────┬───────────────┬────────────────────┘
           │              │               │
           ▼              ▼               ▼
   ┌──────────────┐ ┌──────────┐  ┌─────────────────┐
   │  LangGraph   │ │ CosmosDB │  │ Azure AI Search │
   │  (FSM 그래프)│ │ (히스토리)│  │ (law-unified-   │
   │              │ │          │  │  index, 6001건)  │
   │ 5 Nodes      │ └──────────┘  └─────────────────┘
   │ + MemorySaver│        │               │
   └──────────────┘        │               │
           │               │               │
           ▼               │               │
   ┌──────────────┐        │               │
   │   CrewAI     │        │               │
   │ (asyncio.    │────────┘               │
   │  to_thread)  │───────────────────────┘
   │              │
   │ 2 Agents:    │
   │ - Search     │
   │   Specialist │
   │ - Legal      │
   │   Expert     │
   └──────────────┘
```

### 3.2 컴포넌트 역할

| 컴포넌트 | 기술 | 역할 |
| :--- | :--- | :--- |
| Frontend | Next.js 15, React 19, Assistant UI | 채팅 인터페이스, SSE 수신 |
| Main API | FastAPI (Async) | 채팅 요청 처리, SSE 스트리밍, 히스토리 관리 |
| Service Backend | FastAPI (Port 8001) | DB 조회 (대화방 목록, 히스토리) |
| LangGraph | langgraph ≥0.2.0 | FSM 기반 노드 오케스트레이션, 상태 영속성 |
| CrewAI | crewai ≥0.80.0 | 멀티 에이전트 법률 분석 (검색→분석/작성) |
| Azure AI Search | azure-search-documents ≥11.4.0 | 시맨틱 하이브리드 검색 (법령 조문 RAG) |
| CosmosDB | azure-cosmos ≥4.14.3 | 대화 히스토리 영속 저장 |
| Azure Key Vault | azure-keyvault-secrets ≥4.9.0 | 시크릿 관리 (API 키, 엔드포인트) |
| LiteLLM | litellm ≥1.81.8 | LLM 프로바이더 추상화, 파라미터 호환성 |

---

## 4. LangGraph 오케스트레이션

### 4.1 그래프 플로우 (FSM)

```
START → start_node → router_node ─┬─ "general" → general_chat_node → END
                                   │
                                   └─ "legal" → crew_collaboration_node → validation_node
                                                       ↑                    │
                                                       └── "retry" (max 1) ┘
                                                                            │
                                                                     "passed"/"failed" → END
```

### 4.2 노드 상세

| 노드 | 역할 | 상세 |
| :--- | :--- | :--- |
| **start_node** | 상태 초기화 | Pass-through, 상태 무변경 |
| **router_node** | 의도 분류 | 키워드 Fast Path + LLM Slow Path (이중 경로) |
| **general_chat_node** | 일반 대화 | RAG 없이 LLM 직접 응답, 히스토리 컨텍스트 포함 |
| **crew_collaboration_node** | 법률 RAG | CrewAI 팀 실행 (`asyncio.to_thread`로 비동기 처리) |
| **validation_node** | 품질 검증 | 불완전 응답 감지 → 자동 재시도 (최대 1회) |

### 4.3 라우터 이중 경로 전략

**Fast Path (키워드 매칭)** — 즉시 분류, LLM 호출 없음
```
키워드: "법", "조항", "판례", "소송", "형법", "민법", "상법", "위반", "처벌", "배상"
→ 하나라도 포함 시 즉시 "legal" 라우팅
```

**Slow Path (LLM 의미 분류)** — 키워드 미매칭 시 실행
```
GPT-4o에 "legal" / "general" 이진 분류 요청
→ 실패 시 안전을 위해 "legal"로 기본 라우팅
```

### 4.4 품질 검증 (Self-Healing FSM)

Validation Node가 `final_response`에서 다음 키워드를 탐지하면 재시도합니다:
- `"죄송합니다"`, `"답변을 드릴 수 없습니다"`, `"정보가 부족합니다"`, `"오류가 발생"`

| 상태 | 조건 | 동작 |
| :--- | :--- | :--- |
| `passed` | 키워드 미탐지 | → END (정상 응답) |
| `retry` | 키워드 탐지 + retry_count < max_retries | → crew_collaboration_node 재실행 |
| `failed` | 키워드 탐지 + retry_count ≥ max_retries | → END (실패 메시지 반환) |

---

## 5. CrewAI 멀티 에이전트

### 5.1 Legal RAG Crew 구성

Sequential 프로세스로 2개 에이전트가 순차 실행됩니다.

| 에이전트 | 역할 | 도구 | 페르소나 |
| :--- | :--- | :--- | :--- |
| **Search Specialist** | 법률 문서 검색 | AzureSearchTool | 대형 로펌 15년차 법률 리서치 전문가 |
| **Legal Expert** | 법률 분석 + 답변 작성 | 없음 (텍스트 처리) | 20년 경력 변호사, 복잡한 법을 쉽게 설명 |

### 5.2 작업 흐름

```
Search Specialist                        Legal Expert
━━━━━━━━━━━━━━━━                        ━━━━━━━━━━━━
1. 질문에서 핵심 법률 키워드 추출         1. 검색 결과에서 핵심 조항 추출
2. Azure AI Search 실행                  2. 적용 가능한 법률 원칙 분석
3. 결과 관련성 평가                       3. 상충하는 문서 간 우선순위 판단
4. 상위 3~5건 선별 반환                   4. 실무 적용 방법 설명
                                          5. 출처 명시 (법령명, 조항 번호)
                                          6. 법률 면책 고지문 포함
```

### 5.3 면책 고지문 (모든 법률 응답에 필수 포함)

> 본 답변은 일반적인 법률 정보 제공을 목적으로 하며, 개별 사안에 대한 법률 자문이 아닙니다. 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.

---

## 6. Azure AI Search (RAG 엔진)

### 6.1 검색 구성

| 항목 | 설정 |
| :--- | :--- |
| 인덱스명 | `law-unified-index` |
| 검색 방식 | 시맨틱 하이브리드 (키워드 + 시맨틱 리랭킹) |
| 시맨틱 설정 | `legal-semantic-config` |
| 기본 반환 수 | 쿼리당 상위 5건 |
| 검색 필드 | id, title, content, source, category, law_number, case_number, decision_date, court |

### 6.2 인덱스 스키마

| 필드 | 타입 | 법령 | 판례 |
| :--- | :--- | :--- | :--- |
| `id` | string | `law_*` | `prec_*` |
| `title` | string | 법령명 | 사건명 |
| `content` | string | **조문 전문** (평균 6,388자) | 사건명만 |
| `source` | string | 법제처_법령 | 법제처_판례 |
| `category` | string | 법률/시행령/시행규칙 등 | 판례 |
| `case_number` | string | - | 사건번호 |
| `decision_date` | string | - | 판결일 |
| `court` | string | - | 법원명 |

### 6.3 결과 포맷

검색 결과는 다음 형식으로 CrewAI 에이전트에 전달됩니다:

```
[문서 1] 근로기준법
출처: 법제처_법령
관련성: 8.72
내용: 제1조(목적) 이 법은 헌법에 따라 근로조건의 기준을 정함으로써...(500자 미리보기)
```

---

## 7. 상태 관리 및 영속성

### 7.1 AgentState 주요 필드

```python
# 식별 정보
user_no, chat_id, room_id, user_query

# 대화 히스토리 (LangChain Message 형식)
history: Sequence[HumanMessage | AIMessage]  # add_messages 리듀서로 자동 누적

# 라우팅 및 제어
route: "general" | "legal"
retry_count: int (기본 0)
max_retries: int (기본 1)
validation_status: "pending" | "passed" | "failed" | "retry"

# 검색 및 분석 결과
search_results: List[Dict]
legal_analysis_metadata: Dict
final_response: str

# 스트리밍
streaming_queue: asyncio.Queue (런타임 주입)
```

### 7.2 이중 영속성 구조

| 계층 | 기술 | 범위 | 용도 |
| :--- | :--- | :--- | :--- |
| **단기** | LangGraph MemorySaver | thread_id 기준 | 그래프 실행 중 상태 체크포인트 |
| **장기** | Azure CosmosDB | user_no + room_id 기준 | 대화 히스토리 영구 저장 (서버 재시작 후 복구) |

### 7.3 CosmosDB 대화 저장 구조

```
Database: conversation_history_db
Container: conversation_history (Partition Key: /chat_id)

Document:
├── identifiers: { user_no, chat_id, room_id }
├── system_info: { model_name, embedder_name }
├── runtime_info: { user_query, output, intents, used_tools, exe_date, rag_document_ids, metadata }
└── search_data: { 검색 결과 원본 }
```

- 최근 **10턴**을 로드하여 멀티턴 대화 컨텍스트 유지
- Background Task로 응답 완료 후 비동기 저장 (최대 30초 대기)

---

## 8. SSE 스트리밍 아키텍처

### 8.1 토큰 스트리밍 파이프라인

```
LLM 토큰 생성
  → AdvancedStateCallback.on_llm_new_token()
    → token_queue (asyncio.Queue)
      → drain_tokens()
        → sse_queue (SSE 포맷 변환)
          → HTTP EventSource 스트리밍
            → Frontend (실시간 렌더링)
```

### 8.2 SSE 이벤트 타입 (Vercel AI SDK 호환)

| 이벤트 | 용도 |
| :--- | :--- |
| `start` / `finish` | 응답 라이프사이클 시작/종료 |
| `text-start` / `text-delta` / `text-end` | 토큰 단위 텍스트 스트리밍 |
| `message-metadata` | 진행 상태 ("관련 법률 문서를 검색하고 있습니다...") |
| `error` | 에러 리포팅 |

### 8.3 CrewAI 동기 코드와의 통합

CrewAI는 동기(synchronous) 프레임워크이므로 다음과 같이 비동기 환경과 통합됩니다:

```python
# CrewAI를 별도 스레드에서 실행 (이벤트 루프 차단 방지)
result = await asyncio.to_thread(crew.kickoff, inputs={...})

# 스레드에서 메인 루프로 상태 메시지 전달 (contextvars 기반)
StatusNotifier → run_coroutine_threadsafe() → sse_queue
```

---

## 9. Latency 최적화

| 최적화 | 내용 | 효과 |
| :--- | :--- | :--- |
| **에이전트 통합** | legal_analyst + legal_writer → legal_expert (3→2 에이전트) | LLM 호출 1회 절감 |
| **재시도 축소** | max_retries 3→1 | 최악의 경우 latency 1/3 |
| **Search 캐시** | Azure AI Search 결과 인메모리 TTL 캐시 (1시간) | 동일 검색어 API 호출 생략 |
| **Crew 결과 캐시** | user_query 기준 Crew 전체 결과 캐시 (1시간) | 동일 질문 즉시 응답 (sub-second) |
| **키워드 Fast Path** | 법률 키워드 감지 시 LLM 라우팅 생략 | 라우팅 latency 제거 |
| **비동기 I/O** | 모든 LLM/Tool 호출 async/await | 동시 처리 성능 극대화 |

### 캐시 전략 상세

```
                  ┌─────────────────────────────────────────────┐
                  │                 요청 도착                     │
                  └──────────────────┬──────────────────────────┘
                                     ▼
                  ┌─────────────────────────────────────────────┐
                  │         Crew 결과 캐시 조회                   │
                  │         Key: MD5(user_query)                 │
                  └──────┬──────────────────────┬───────────────┘
                    HIT  │                      │ MISS
                         ▼                      ▼
                  즉시 응답 반환          Search 캐시 조회
                  (sub-second)           Key: MD5(query:top_k)
                                    ┌────┴────┐
                               HIT  │         │ MISS
                                    ▼         ▼
                              캐시 결과    Azure AI Search
                              사용         API 호출
                                    │         │
                                    └────┬────┘
                                         ▼
                                  Legal Expert 분석
                                         │
                                         ▼
                                  결과 캐시 저장
                                  (TTL: 1시간)
```

---

## 10. LLM 구성

### 10.1 모델 전략

| 용도 | 모델 | 프레임워크 |
| :--- | :--- | :--- |
| CrewAI 에이전트 (법률 분석) | GPT-5.1 (Primary) | LiteLLM → SafeLLMWrapper |
| 라우터/일반 대화 | GPT-4o (Secondary) | LangChain AzureChatOpenAI |

### 10.2 GPT-5.x 호환성 처리

GPT-5.x 모델은 `stop`, `temperature`, `top_p` 파라미터를 지원하지 않습니다. CrewAI가 이 파라미터를 강제하므로, `_prepare_completion_params()`를 패치하여 미지원 파라미터를 자동 제거합니다.

```python
litellm.drop_params = True  # 미지원 파라미터 자동 무시
```

### 10.3 SafeLLMWrapper (에러 안전 계층)

CrewAI LLM을 감싸는 래퍼로, 모든 LLM 호출에 대해:
- 예외 발생 시 사용자 친화적 한국어 에러 메시지 자동 생성
- API 키, 상태 코드 등 기술적 정보 마스킹
- 전체 traceback은 내부 로그에만 기록

---

## 11. 보안 아키텍처

### 11.1 시크릿 관리

| 환경 | 방식 |
| :--- | :--- |
| Local | `.env` 파일 (python-dotenv) |
| Development / Production | **Azure Key Vault** (Container Apps Key Vault Reference) |

관리 대상 시크릿:
- Azure OpenAI API 키 및 엔드포인트 (Primary/Secondary)
- Azure AI Search API 키 및 엔드포인트
- CosmosDB 엔드포인트 및 키
- Application Insights 연결 문자열

### 11.2 로그 보안

설정값 로그 출력 시 마스킹 처리:
```
원본: sk-abcdefghijklmnop1234
마스킹: sk-a***1234
```

### 11.3 네트워크 보안

- **CORS**: `localhost:3000`, `127.0.0.1:3000`만 허용 (운영 환경에서는 도메인 제한 필요)
- **CosmosDB 방화벽**: 접속 실패 시 IP 주소를 추출하여 방화벽 규칙 추가를 안내
- **Azure Private 환경**: Container Apps 내부에서 Key Vault, CosmosDB, AI Search에 접근

### 11.4 에러 정보 보호

- LLM API 에러의 기술적 상세(상태 코드, 응답 본문, 엔드포인트 URL)는 사용자에게 노출되지 않음
- `SafeLLMWrapper`가 기술적 에러를 자연어 한국어 메시지로 변환
- 원본 에러는 서버 로그 및 Application Insights에만 기록

### 11.5 법률 면책

모든 법률 응답에 면책 고지문을 필수 포함하여 법률 자문으로 오인되는 것을 방지합니다.

---

## 12. 모니터링 및 관측성

### 12.1 Application Insights 통합

- 구조화된 로그 전송 (custom_dimensions 지원)
- 연결 문자열 또는 Instrumentation Key 기반 설정
- 콘솔 로그와 독립적인 로그 레벨 설정 가능

### 12.2 성능 미들웨어

- 모든 HTTP 요청의 처리 시간 측정
- 0.5초 초과 시 경고 로그 출력
- `X-Process-Time` 응답 헤더로 클라이언트에 처리 시간 전달

### 12.3 상태 메시지 (사용자 가시)

SSE를 통해 처리 단계별 상태를 실시간 전달합니다:
1. "관련 법률 문서를 검색하고 있습니다..."
2. "N개의 관련 문서를 찾았습니다. 법률 분석 중..."
3. "더 나은 답변을 위해 재검토 중..." (재시도 시)

---

## 13. 기술 스택 요약

| 영역 | 기술 | 버전 |
| :--- | :--- | :--- |
| Frontend | Next.js, React, Assistant UI, TailwindCSS, Zustand | 15 / 19 |
| Backend | Python, FastAPI (Async), UV | 3.13+ / ≥0.115.0 |
| AI Orchestration | LangGraph | ≥0.2.0 |
| Multi-Agent | CrewAI | ≥0.80.0 |
| LLM Abstraction | LiteLLM, LangChain, LangChain-OpenAI | ≥1.81.8 / ≥0.3.0 |
| AI Model | Azure OpenAI (GPT-5.1, GPT-4o) | - |
| Search | Azure AI Search (Semantic Hybrid) | ≥11.4.0 |
| Database | Azure CosmosDB | ≥4.14.3 |
| Security | Azure Key Vault, Azure Identity | ≥4.9.0 / ≥1.19.0 |
| Validation | Pydantic, Pydantic Settings | ≥2.9.0 / ≥2.6.0 |

---

## 14. 향후 개선 방향

| 항목 | 현재 상태 | 개선 방안 |
| :--- | :--- | :--- |
| 판례 데이터 | content에 사건명만 포함 | 법제처 API가 JSON 판결 전문 제공 시 보강, 또는 HTML 파싱 |
| 캐시 | 인메모리 (서버 재시작 시 소멸) | Redis 등 외부 캐시로 영속화 |
| CORS | localhost만 허용 | 운영 환경 도메인 등록 |
| 검색 범위 | 법령 1,001건 | 추가 법령 수집 및 주기적 업데이트 |
| 멀티턴 | 최근 10턴 | 대화 요약(summarization) 적용으로 장기 대화 지원 |
