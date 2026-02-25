# HD현대 법무 지원 Agent

순수 LangGraph 기반 **Advanced Multi-Agent + Advanced RAG** 아키텍처의 법무 지원 AI 시스템입니다.
Supervisor 패턴으로 의도를 분류하고, 전문 에이전트(Legal, General)가 각 도메인을 처리합니다.
Legal Agent는 Dual-Source Retrieval(Azure AI Search + Tavily 웹 검색), Multi-Query Retrieval, Semantic Reranker 필터링, Cross-Agent Context Propagation,
Domain-Aware Structural Validation 등 고급 RAG/에이전트 기법을 적용하여
실무자가 상급자에게 보고할 수 있는 수준의 구조화된 법률 답변을 생성합니다.

## 🎯 프로젝트 목적

1. **법무 업무 자동화**: 법률 질의에 대해 법령·판례를 검색하고 정밀한 분석 답변을 제공합니다.
2. **Advanced Multi-Agent**: Supervisor 패턴 라우팅 + Cross-Agent Context Propagation으로 멀티턴 대화를 지원하며, 에이전트별 Domain-Aware Validation으로 품질을 보증합니다.
3. **Advanced RAG**: Dual-Source Retrieval(법령 DB + 웹 검색) + Multi-Query Retrieval(2~3회 다각도 검색) + Semantic Reranker 기반 관련성 필터링 + 확장된 컨텍스트 윈도우(2000자)로 법령 조문의 핵심 조항을 보존합니다.
4. **FSM 기반 Self-Healing**: 에이전트 유형별 구조 검증(법조항 인용, 면책 조항, 최소 길이)으로 불완전한 답변을 자동 재시도합니다.
5. **보안 및 확장성**: Azure Private 환경 내에서 동작하며, CosmosDB에 대화 맥락을 영구 저장(Persistence)합니다.

## 🏗 시스템 아키텍처

```plaintext
quick-agent-poc/
├── api/                      # Main Backend API (FastAPI)
│   ├── main.py               # App Entrypoint (SSE Streaming)
│   └── routers/              # Chat Logic Router (/agent/chat)
├── backend/                  # Support Backend Service (FastAPI)
│   └── api/routers/db        # DB Interaction (History, Metadata)
├── agent/                    # AI Core (Pure LangGraph Multi-Agent)
│   ├── graph/                # LangGraph (Orchestrator + Persistence)
│   ├── node/                 # Graph Nodes (Supervisor, Legal, Chat, Validation)
│   ├── schema/               # State Definition (AgentState)
│   ├── agents/               # Agent 모듈 (Legal ReAct, Prompts)
│   └── tools/                # Azure AI Search + Tavily Web Search (@tool 데코레이터)
├── db/                       # Database Connections (CosmosDB)
└── config/                   # Configuration (Azure Key Vault, .env)
```

### 핵심 설계 철학

1. **Supervisor 패턴 Multi-Agent**:
   - `supervisor_node`가 키워드 Fast Path + LLM Slow Path로 의도를 분류합니다.
   - 각 경로(legal, general)에 맞는 전문 에이전트가 독립적으로 처리합니다.

2. **완전 비동기 (Async/Await)**:
   - 모든 노드가 `async`로 동작하며, LLM 호출은 `ainvoke`를 사용합니다.
   - `asyncio.to_thread` 같은 동기-비동기 브릿지 없이 순수 비동기 파이프라인으로 구성됩니다.

3. **FSM 기반 품질 보증 (Self-Healing)**:
   - `validation_node`가 답변 품질을 검증하고, 실패 시 Legal Agent를 자동 재시도합니다.
   - 불완전한 답변을 사용자에게 그대로 노출하지 않고, 내부적으로 개선을 시도합니다.

4. **상태 영속성 (Persistence)**:
   - `MemorySaver` 및 `CosmosDB`를 통해 대화 Context를 스레드별로 저장하고 복구합니다.

5. **Latency 최적화**:
   - Legal Agent: `create_react_agent` + gpt-4o로 단일 에이전트 실행 (CrewAI 오버헤드 제거)
   - Azure AI Search 결과, Tavily 웹 검색 결과, Agent 실행 결과에 인메모리 TTL 캐시(1시간) 적용
   - 동일 질문 재요청 시 에이전트 실행을 건너뛰고 즉시 캐시된 결과를 반환

## 🔄 멀티에이전트 작동 흐름

본 시스템은 **Supervisor Agent**가 사용자 의도를 판단하고, 2개의 전문 에이전트(Legal / General) 중 하나를 선택하여 실행하는 **Supervisor 패턴 멀티에이전트** 구조입니다. Legal Agent는 Dual-Tool(법령 DB + 웹 검색)을 갖추고 있으며, 공통 Validation 노드가 품질을 보증합니다.

### 전체 흐름도

```plaintext
START → start_node → supervisor_node ─┬─ "general" → general_chat_node → END
                                       └─ "legal"   → legal_agent_node → validation_node ─┬─ "passed" → END
                                                            ↑                               │
                                                            └──── "retry" ─────────────────┘
                                                                                            │
                                                                                     "failed" → END
```

### 단계별 에이전트 작동 순서

**Step 1. Supervisor Agent (의도 분류)**
- 사용자 질문이 들어오면 가장 먼저 `supervisor_node`가 실행됩니다.
- 키워드 Fast Path: `["법", "조항", "판례", "소송", ...]` 등 법률 키워드가 있으면 LLM 호출 없이 즉시 `legal` 라우팅
- LLM Slow Path: 키워드가 없으면 gpt-4o가 `"legal"` / `"general"` 중 하나로 분류
- **결과**: `state.route`에 라우팅 경로가 설정되어 해당 전문 에이전트로 분기

**Step 2. 전문 에이전트 실행 (2개 중 1개)**

| 에이전트 | 라우팅 조건 | 모델 | 내부 동작 | 도구 |
| :--- | :--- | :--- | :--- | :--- |
| **Legal Agent** | `route == "legal"` | gpt-4o | ReAct 루프: Dual-Source 검색 (법령 DB + 웹) → Reranker 필터링 → 5단계 구조화 답변 | `azure_legal_search`, `tavily_legal_search` |
| **General Chat** | `route == "general"` | gpt-4o | 단일 LLM 호출 (최근 3턴 대화 컨텍스트 포함) | 없음 (순수 LLM) |

- Legal Agent는 대화 이력(최근 2턴)을 함께 전달받아 꼬리질문을 처리합니다.
- Legal Agent는 질문의 성격에 따라 법령 DB 검색과 웹 검색을 자율적으로 선택/병행합니다.
- General Chat은 검증 없이 바로 응답을 반환합니다.

**Step 3. Validation Agent (품질 검증 — Legal만)**
- Legal Agent의 응답은 반드시 `validation_node`를 거칩니다.
- 공통 검증: 실패 키워드(`"죄송합니다"`, `"오류가 발생"` 등) 검사
- Legal 전용 구조 검증: 최소 200자 + 면책 조항 + 법조항 인용(`제N조`) 패턴
- **통과** → 사용자에게 응답 반환
- **실패** → Legal Agent를 1회 재실행
- **재실패** → 현재 응답 그대로 반환 (무한 루프 방지)

### 에이전트 간 협업 구조

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                    AgentState (공유 상태)                     │
│  user_query, chat_context, route, active_agent,             │
│  final_response, validation_status, retry_count ...         │
└──────────┬──────────────────────────────┬────────────────────┘
           │                              │
     ┌─────▼─────┐                  ┌─────▼─────┐
     │  Legal     │                  │ General   │
     │  Agent     │                  │ Chat      │
     │ (ReAct +   │                  │ (단일 LLM │
     │  Dual-Tool)│                  │  호출)    │
     └─────┬─────┘                  └─────┬─────┘
           │                              │
           ▼                              ▼
   Validation Node                    직접 END
   (Domain-Aware)
```

- **모든 에이전트는 `AgentState`를 공유**합니다. Supervisor가 `route`를 설정하면, 해당 에이전트가 `final_response`를 채우고, Validation이 `validation_status`를 판정합니다.
- **에이전트 간 직접 통신은 없습니다.** 상태 객체(`AgentState`)를 매개로 간접 협업하는 LangGraph의 **상태 기반 오케스트레이션** 패턴입니다.
- **Supervisor → 전문 에이전트 → Validation**의 3단계 파이프라인이 모든 요청에 대해 일관되게 적용됩니다.

| 노드 | 역할 |
| :--- | :--- |
| **start_node** | 상태 초기화 |
| **supervisor_node** | 의도 분류 (키워드 Fast Path + LLM Slow Path → general / legal) |
| **general_chat_node** | 일반 대화 처리 (도구 없이 fast_llm 직접 응답) |
| **legal_agent_node** | 법률 RAG 에이전트 실행 (`create_react_agent` + `azure_legal_search` + `tavily_legal_search`) |
| **validation_node** | 답변 품질 검증 및 동적 재시도 (최대 1회) |

## 🤖 에이전트 구성

### Legal Agent (법무지원) — Advanced RAG + Dual-Tool

- **방식**: `create_react_agent` (LangGraph ReAct 패턴)
- **모델**: gpt-4o (fast_llm)
- **도구**:
  - `azure_legal_search` (Azure AI Search 시맨틱 하이브리드 검색) — 법령 원문, 조문, 판례 텍스트
  - `tavily_legal_search` (Tavily 웹 검색) — 최신 판례 동향, 법률 개정 뉴스, 법률 해석
- **Dual-Source Retrieval**: ReAct 루프가 질문의 성격에 따라 법령 DB 검색과 웹 검색을 자율적으로 선택/병행
- **Multi-Query Retrieval**: 시스템 프롬프트가 서로 다른 키워드로 2~3회 검색을 지시하여 단일 쿼리의 recall 한계를 극복
- **Semantic Reranker 필터링**: Azure semantic reranker 점수 1.0 미만(0-4 스케일) 문서를 제거하여 노이즈 차단 (최소 1건 유지)
- **확장된 컨텍스트 윈도우**: 검색 결과 content를 500자→2000자로 확대하여 법령 조문의 핵심 조항 보존 (평균 6,388자 조문의 31%)
- **Cross-Agent Context Propagation**: CosmosDB 대화 이력에서 최근 2턴(4메시지)을 추출하여 ReAct 에이전트에 전달, 꼬리질문 지원
- **컨텍스트 인식 캐싱**: `user_query + chat_context` 해시 기반 캐시 키로 동일 질문이라도 대화 맥락에 따라 다른 응답 생성
- **구조화된 답변**: 5단계 강제 구조 (한줄요약 → 적용법률분석 → 실무조치사항 → 리스크요약 → 참고법령)
- **출력 정제**: Thought/Action 패턴 노출 감지 시 폴백 응답 반환

### General Chat (일반 대화)

- **방식**: 단일 LLM 호출 (도구 없음)
- **모델**: gpt-4o (fast_llm)
- **컨텍스트**: CosmosDB에서 로드한 최근 3턴(6개 메시지) 포함

## ⚡ Latency 최적화

| 최적화 | 내용 | 효과 |
| :--- | :--- | :--- |
| **CrewAI 제거** | 순수 LangGraph 에이전트로 전환 (동기 브릿지 제거) | 오버헤드 제거, 완전 비동기 |
| **단일 ReAct Agent** | Legal 처리를 단일 `create_react_agent`로 통합 | LLM 호출 최소화 |
| **재시도 축소** | max_retries = 1, 동적 라우팅 | 최악의 경우에도 빠른 종료 |
| **Search 캐시** | Azure AI Search + Tavily 결과 인메모리 TTL 캐시 (1시간) | 동일 검색어 API 호출 생략 |
| **Agent 결과 캐시** | user_query + chat_context 기준 에이전트 결과 캐시 (1시간) | 동일 질문 즉시 응답 |
| **관련성 필터링** | Semantic Reranker score < 1.0 문서 제거 (최소 1건 유지) | 노이즈 감소로 LLM 판단력 향상 |

## 🧠 Advanced RAG / Multi-Agent 기법 해설

본 시스템이 단순 RAG(Retrieve-and-Generate)와 기본 멀티에이전트를 넘어서는 지점은 다음과 같습니다.

### Advanced RAG 기법

| 기법 | 기존 (Naive RAG) | 본 시스템 | 효과 |
| :--- | :--- | :--- | :--- |
| **Dual-Source Retrieval** | 단일 검색 소스 | 법령 DB(Azure AI Search) + 웹 검색(Tavily)을 ReAct가 자율 선택/병행 | 법령 원문과 최신 동향을 동시에 커버 |
| **Multi-Query Retrieval** | 사용자 쿼리 1회 그대로 검색 | 시스템 프롬프트가 2~3개 키워드 변형으로 다각도 검색 지시 | 단일 쿼리의 recall 한계 극복, 다수 관련 법령 포착 |
| **Semantic Reranker 필터링** | 검색 결과 전체를 LLM에 전달 | Reranker score < 1.0 문서 제거 (최소 1건 유지) | 저관련성 노이즈 제거로 LLM의 정밀도 향상 |
| **컨텍스트 윈도우 확대** | 검색 결과 500자 truncation | 2000자로 확대 + 전체 길이 표기 | 법령 조문 핵심 조항 보존 (8% → 31%) |
| **구조화된 생성 지시** | "간결하게 답변" 일반 지시 | 5단계 강제 구조 (한줄요약→법률분석→실무조치→리스크→참고법령) | 보고서 수준의 일관된 출력 품질 |

### Advanced Multi-Agent 기법

| 기법 | 기존 (Basic Multi-Agent) | 본 시스템 | 효과 |
| :--- | :--- | :--- | :--- |
| **Cross-Agent Context Propagation** | 에이전트에 현재 쿼리만 전달 | CosmosDB → AgentState → legal_agent_node → ReAct messages로 최근 2턴 전파 | 꼬리질문("그럼 벌금은?") 시 이전 맥락 유지 |
| **Context-Aware Caching** | user_query만으로 캐시 키 생성 | user_query + chat_context 해시로 캐시 키 생성 | 동일 질문이라도 대화 맥락에 따라 다른 응답 캐싱 |
| **Domain-Aware Structural Validation** | 실패 키워드만 검사하는 단일 검증 | 에이전트 유형별 구조 검증 (법조항 인용 `제N조`, 면책 조항, 최소 길이) | 법령 인용 없는 일반론 답변 자동 재시도 |
| **Self-Healing with Active Agent Routing** | 고정된 재시도 경로 | `active_agent` 기반 동적 라우팅으로 실패한 에이전트만 정확히 재실행 | 에이전트별 독립적 품질 보증 |

## 🔌 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
| :--- | :--- | :--- |
| `/agent/chat` | POST | 법률/일반 질문 처리 (SSE 스트리밍 응답) |
| `/agent/health` | GET | 헬스 체크 |
| `/db/room_list` | GET | 대화방 목록 조회 |
| `/db/room_history` | GET | 대화 히스토리 조회 |

- **SSE 스트리밍**: Vercel AI SDK 프로토콜 호환 (`text/event-stream`)
- **대화 히스토리**: CosmosDB에서 최근 10턴을 로드하여 멀티턴 대화 지원

## 🧩 에이전트 아키텍처 상세

### Supervisor 패턴 (의도 분류)

사용자 질문이 들어오면 `supervisor_node`가 2단계로 의도를 분류합니다.

```
사용자 질문 → [키워드 Fast Path] ──법률 키워드 발견──→ "legal"
                    │
                    └──키워드 미발견──→ [LLM Slow Path (gpt-4o)] → "legal" / "general"
```

- **Fast Path**: `["법", "조항", "판례", "소송", "형법", "민법", ...]` 등 법률 키워드가 포함되면 LLM 호출 없이 즉시 `legal` 라우팅
- **Slow Path**: 키워드가 없는 경우 gpt-4o가 2개 카테고리 중 하나로 분류

### LLM 모델 전략

| 인스턴스 | 모델 | 용도 | 특성 |
| :--- | :--- | :--- | :--- |
| `fast_llm` | gpt-4o | Supervisor, Legal Agent, General Chat | 빠른 응답, 도구 호출 지원 |

- 모든 LLM은 `streaming=True`로 초기화되어 SSE 토큰 스트리밍을 지원합니다.

### Legal Agent 내부 동작 — Advanced RAG Pipeline + Dual-Tool

`create_react_agent`가 Dual-Source Retrieval(법령 DB + 웹 검색) + Semantic Reranker 필터링을 거친 고품질 검색 결과를 기반으로 구조화된 답변을 생성합니다.

```
[CosmosDB 대화 이력]
        │ 최근 2턴(4메시지) 추출
        ↓
사용자 질문 + chat_context → [ReAct Agent (gpt-4o)]
                                   │
                                   ├─ Thought: 질문 분석 → 도구 선택 전략 수립
                                   │
                                   ├─ [법령 DB 검색 경로]
                                   │    ├─ Action: azure_legal_search("산업안전보건법 도급인 의무")
                                   │    │    └─ [Semantic Reranker 필터링] score ≥ 1.0 문서만 통과
                                   │    │    └─ [컨텍스트 윈도우 2000자] 조문 원문 보존
                                   │    ├─ Action: azure_legal_search("산업재해보상보험법 원청 책임")
                                   │    └─ Action: azure_legal_search("중대재해처벌법 도급인")
                                   │
                                   ├─ [웹 검색 경로]
                                   │    └─ Action: tavily_legal_search("2024년 중대재해처벌법 판례 동향")
                                   │         └─ 최신 판례 뉴스, 법률 해석, 개정 동향
                                   │
                                   ├─ Thought: 복수 소스 결과 종합하여 답변 구성
                                   └─ Final Answer: 5단계 구조화 답변
                                        ├─ 1. 한줄 요약
                                        ├─ 2. 적용 법률 분석 (조·항·호 + 조문 원문 인용)
                                        ├─ 3. 실무 조치사항 (체크리스트 + 위반 시 제재)
                                        ├─ 4. 리스크 요약 (보고용)
                                        └─ 5. 📎 참고 법령 (+ 웹 출처 URL)
```

- **Dual-Source Retrieval**: ReAct 루프가 질문의 성격에 따라 `azure_legal_search`(법령 DB)와 `tavily_legal_search`(웹)를 자율적으로 선택/병행
- **Multi-Query Retrieval**: 시스템 프롬프트가 서로 다른 키워드로 2~3회 검색을 지시 → 단일 쿼리 대비 recall 향상
- **Semantic Reranker 필터링**: Azure semantic reranker 점수 1.0 미만 문서 제거, 최소 1건 유지로 빈 결과 방지
- **확장된 컨텍스트 윈도우**: 검색 결과 500자→2000자 확대로 법령 조문 핵심 조항 보존 (gpt-4o 128K 컨텍스트 내 5문서 × 2000자 ≈ 10K 토큰)
- **Cross-Agent Context Propagation**: `CosmosDB → AgentState.chat_context → legal_agent_node → run_legal_agent → ReAct messages`로 대화 맥락 전파
- **캐싱**: 법령 DB 검색 결과, 웹 검색 결과, 에이전트 최종 응답 각각 1시간 TTL 캐시
- **출력 정제**: ReAct 내부 텍스트(Thought/Action/Observation)가 최종 응답에 노출되면 폴백 응답으로 대체

### Validation & Self-Healing — Domain-Aware Structural Validation

`validation_node`는 공통 품질 검증에 더해, 에이전트 유형별 도메인 특화 구조 검증을 수행합니다.

```
에이전트 응답 → [validation_node]
                    │
                    ├─ [공통 검증] 실패 키워드 검사 ("죄송합니다", "오류가 발생" 등)
                    │
                    ├─ [Legal 전용 구조 검증] (active_agent == "legal" 일 때)
                    │    ├─ 최소 길이 200자 이상
                    │    ├─ 면책 조항 포함 여부 (※ / 법률 정보 제공 목적)
                    │    └─ 법조항 인용 패턴 존재 여부 (제N조 정규식 매칭)
                    │
                    ├─ 모든 검증 통과 → "passed" → END
                    │
                    └─ 검증 실패
                         ├─ retry_count < max_retries → "retry" → legal_agent_node로 복귀
                         └─ retry_count >= max_retries → "failed" → END
```

- **Domain-Aware Validation**: Legal 에이전트 응답에 대해 법조항 인용(`제\d+조`), 면책 조항, 최소 길이를 구조적으로 검증하여, 법령 인용 없이 일반론만 서술하는 저품질 답변을 차단합니다.
- **재시도 제한**: 최대 1회로 제한하여 무한 루프를 방지합니다.

### SSE 스트리밍 파이프라인

```
LLM (streaming=True)
    │ on_llm_new_token 콜백
    ↓
token_queue (asyncio.Queue)
    │ drain_tokens 태스크
    ↓
sse_queue (asyncio.Queue) ← push_status (contextvars 기반)
    │
    ↓
SSE Response (text/event-stream, Vercel AI SDK 호환)
```

- `AdvancedStateCallback`이 LLM 토큰을 실시간으로 `token_queue`에 전달합니다.
- `StatusNotifier`는 `contextvars` 기반으로 어떤 노드에서든 `push_status()`를 호출하여 상태 이벤트를 전송할 수 있습니다.
- `create_react_agent` 내부 LLM 호출에서도 콜백이 자동 전파되어 토큰 스트리밍이 동작합니다.

## 🛠 기술 스택

| 영역 | 기술 스택 |
| :--- | :--- |
| **Frontend** | Next.js 15, React 19, Assistant UI, TailwindCSS, Zustand |
| **Backend** | Python 3.13+, FastAPI (Async), UV (Package Manager) |
| **Agent** | LangGraph (Orchestration + Multi-Agent), LangChain, `create_react_agent` |
| **AI / Model** | Azure OpenAI (GPT-4o Fast), Azure AI Search (Semantic RAG), Tavily (Web Search) |
| **DB / Infra** | Azure CosmosDB (History/Persistence), Azure Key Vault (Secrets) |
