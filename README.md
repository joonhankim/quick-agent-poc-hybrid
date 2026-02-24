# HD현대 법무 지원 Agent

순수 LangGraph 기반 Multi-Agent 아키텍처의 법무 지원 AI 시스템입니다.
Supervisor 패턴으로 의도를 분류하고, 전문 에이전트(Legal, Research, General)가 각 도메인을 처리합니다.
FSM 기반 Self-Healing과 Azure Private 환경 내 동작을 통해 엔터프라이즈 레벨의 신뢰성을 제공합니다.

## 🎯 프로젝트 목적

1. **법무 업무 자동화**: 법률 질의에 대해 법령·판례를 검색하고 정밀한 분석 답변을 제공합니다.
2. **순수 LangGraph Multi-Agent**: Supervisor 패턴으로 라우팅하고, `create_react_agent`(Legal) 및 2-Stage LLM Chain(Research)으로 전문 처리합니다.
3. **FSM 기반 품질 보증**: 답변 품질이 낮을 경우 `active_agent` 기반으로 해당 에이전트를 자동 재시도하는 Self-Healing 메커니즘을 포함합니다.
4. **보안 및 확장성**: Azure Private 환경 내에서 동작하며, CosmosDB에 대화 맥락을 영구 저장(Persistence)합니다.

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
│   ├── node/                 # Graph Nodes (Supervisor, Legal, Research, Chat, Validation)
│   ├── schema/               # State Definition (AgentState)
│   ├── agents/               # Agent 모듈 (Legal ReAct, Research Chain, Prompts)
│   └── tools/                # Azure AI Search Tool (@tool 데코레이터)
├── db/                       # Database Connections (CosmosDB)
└── config/                   # Configuration (Azure Key Vault, .env)
```

### 핵심 설계 철학

1. **Supervisor 패턴 Multi-Agent**:
   - `supervisor_node`가 키워드 Fast Path + LLM Slow Path로 의도를 분류합니다.
   - 각 경로(legal, research, general)에 맞는 전문 에이전트가 독립적으로 처리합니다.

2. **완전 비동기 (Async/Await)**:
   - 모든 노드가 `async`로 동작하며, LLM 호출은 `ainvoke`를 사용합니다.
   - `asyncio.to_thread` 같은 동기-비동기 브릿지 없이 순수 비동기 파이프라인으로 구성됩니다.

3. **FSM 기반 품질 보증 (Self-Healing)**:
   - `validation_node`가 답변 품질을 검증하고, 실패 시 `active_agent` 기반으로 해당 에이전트를 자동 재시도합니다.
   - 불완전한 답변을 사용자에게 그대로 노출하지 않고, 내부적으로 개선을 시도합니다.

4. **상태 영속성 (Persistence)**:
   - `MemorySaver` 및 `CosmosDB`를 통해 대화 Context를 스레드별로 저장하고 복구합니다.

5. **Latency 최적화**:
   - Legal Agent: `create_react_agent` + gpt-4o로 단일 에이전트 실행 (CrewAI 오버헤드 제거)
   - Azure AI Search 결과 및 Agent 실행 결과에 인메모리 TTL 캐시(1시간) 적용
   - 동일 질문 재요청 시 에이전트 실행을 건너뛰고 즉시 캐시된 결과를 반환

## 🔄 그래프 플로우

LangGraph 기반 6개 노드로 구성된 Supervisor + FSM 흐름입니다.

```plaintext
START → start_node → supervisor_node ─┬─ "general"  → general_chat_node → END
                                       ├─ "legal"    → legal_agent_node → validation_node ─┬─ "passed" → END
                                       └─ "research" → research_agent_node → validation_node┘  │
                                                             ↑                                  │
                                                             └──── "retry" (active_agent 기반) ─┘
                                                                                                │
                                                                                         "failed" → END
```

| 노드 | 역할 |
| :--- | :--- |
| **start_node** | 상태 초기화 |
| **supervisor_node** | 의도 분류 (키워드 Fast Path + LLM Slow Path → general / legal / research) |
| **general_chat_node** | 일반 대화 처리 (도구 없이 fast_llm 직접 응답) |
| **legal_agent_node** | 법률 RAG 에이전트 실행 (`create_react_agent` + `azure_legal_search`) |
| **research_agent_node** | 리서치 에이전트 실행 (2-Stage LLM Chain: researcher → editor) |
| **validation_node** | 답변 품질 검증 및 `active_agent` 기반 동적 재시도 (최대 1회) |

## 🤖 에이전트 구성

### Legal Agent (법무지원)

- **방식**: `create_react_agent` (LangGraph ReAct 패턴)
- **모델**: gpt-4o (fast_llm)
- **도구**: `azure_legal_search` (Azure AI Search 시맨틱 하이브리드 검색)
- **캐싱**: `user_query` 기준 MD5 키, 1시간 TTL 인메모리 캐시
- **출력 정제**: Thought/Action 패턴 노출 감지 시 폴백 응답 반환

### Research Agent (리서치)

- **방식**: 2-Stage LLM Chain (도구 없이 순수 LLM 호출)
- **모델**: gpt-5.1 (langchain_llm, reasoning 모델)
- **Stage 1** (Researcher): 심층 리서치 보고서 작성
- **Stage 2** (Editor): 사용자 친화적으로 편집

### General Chat (일반 대화)

- **방식**: 단일 LLM 호출 (도구 없음)
- **모델**: gpt-4o (fast_llm)
- **컨텍스트**: CosmosDB에서 로드한 최근 3턴(6개 메시지) 포함

## ⚡ Latency 최적화

| 최적화 | 내용 | 효과 |
| :--- | :--- | :--- |
| **CrewAI 제거** | 순수 LangGraph 에이전트로 전환 (동기 브릿지 제거) | 오버헤드 제거, 완전 비동기 |
| **단일 ReAct Agent** | Legal 처리를 단일 `create_react_agent`로 통합 | LLM 호출 최소화 |
| **재시도 축소** | max_retries = 1, active_agent 기반 동적 라우팅 | 최악의 경우에도 빠른 종료 |
| **Search 캐시** | Azure AI Search 결과 인메모리 TTL 캐시 (1시간) | 동일 검색어 API 호출 생략 |
| **Agent 결과 캐시** | user_query 기준 에이전트 결과 캐시 (1시간) | 동일 질문 즉시 응답 |

## 🔌 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
| :--- | :--- | :--- |
| `/agent/chat` | POST | 법률/일반/리서치 질문 처리 (SSE 스트리밍 응답) |
| `/agent/health` | GET | 헬스 체크 |
| `/db/room_list` | GET | 대화방 목록 조회 |
| `/db/room_history` | GET | 대화 히스토리 조회 |

- **SSE 스트리밍**: Vercel AI SDK 프로토콜 호환 (`text/event-stream`)
- **대화 히스토리**: CosmosDB에서 최근 10턴을 로드하여 멀티턴 대화 지원

## 📚 법률 데이터 현황

Azure AI Search 인덱스(`law-unified-index`)에 적재된 데이터는 **[법제처 Open API](https://open.law.go.kr)**를 통해 수집한 대한민국 공공 법률 데이터입니다.

| 구분 | 건수 | 출처 | 수집 API | RAG 활용 |
| :--- | ---: | :--- | :--- | :---: |
| **법령** | 1,001건 | 법제처 | 법령 API (`법령검색/목록` + 조문 전문) | **O** |
| **판례** | 5,000건 | 법제처 | 판례 API (`판례검색/목록`) | X |
| **합계** | **6,001건** | | | |

> **RAG에는 법령 조문 전문(1,001건)만 활용됩니다.** 판례 5,000건은 인덱스에 존재하지만 content에 사건명만 포함되어 있어 RAG 검색 대상에서 실질적으로 제외됩니다.

### 법령 데이터 (1,001건)

법제처 Open API의 법령 API에서 **조문 전문**을 수집하여 `content` 필드에 적재한 데이터입니다. 대한민국 현행 법률, 시행령, 시행규칙 등 다양한 법규의 실제 조문 텍스트를 포함하고 있어 RAG 시스템의 핵심 검색 소스로 활용됩니다.

**content 길이 분포:**

전체 1,001건 중 **94.4%가 500자 초과의 실질적 법령 본문**을 보유하고 있습니다 (평균 6,388자).

| content 길이 | 건수 | 비율 |
| :--- | ---: | ---: |
| ~50자 (제목만) | 2건 | 0.2% |
| 51~500자 | 54건 | 5.4% |
| 501~2,000자 | 248건 | 24.8% |
| 2,001~10,000자 | 515건 | 51.4% |
| 10,001~30,000자 | 155건 | 15.5% |
| 30,001~50,000자 | 27건 | 2.7% |

> 50,000자에서 truncation이 적용되어 있습니다. 건축법 시행령, 공직선거법 등 일부 대형 법령은 조문 전문이 잘릴 수 있습니다.

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

### 예시 데이터

**법령 예시 (조문 전문 포함):**

```json
{
  "id": "law_234693",
  "title": "건설근로자의 고용개선 등에 관한 법률",
  "content": "건설근로자의 고용개선 등에 관한 법률\n\n제1조(목적) 이 법은 건설근로자의 고용안정 ...(이하 조문 전문)",
  "source": "법제처_법령",
  "category": "법률",
  "case_number": "",
  "decision_date": "",
  "court": "",
  "law_number": ""
}
```

### 판례 데이터 제한 사항 (5,000건)

판례 5,000건은 인덱스에 존재하지만, `content` 필드에 **사건명만 포함**되어 있어 RAG에 부적합합니다.

```json
{
  "id": "prec_241657",
  "title": "손해배상(기)",
  "content": "[손해배상(기)]",
  "source": "법제처_판례",
  "category": "판례",
  "case_number": "2023다249456",
  "decision_date": "2024.05.30",
  "court": "대법원"
}
```

**보강 불가 사유:** 법제처 Open API의 판례 상세 조회 API가 판결 전문(판시사항, 판결요지)을 JSON 필드로 제공하지 않습니다. HTML 본문으로만 제공되어 구조화된 수집이 불가능합니다.

> 향후 법제처 API가 판결 전문을 JSON으로 제공하거나, HTML 파싱을 통한 수집이 가능해지면 판례 데이터를 보강할 수 있습니다.

### 인덱스 스키마

| 필드 | 타입 | 설명 | 법령 | 판례 |
| :--- | :--- | :--- | :---: | :---: |
| `id` | string | 문서 고유 ID | `law_*` | `prec_*` |
| `title` | string | 법령명 또는 사건명 | O | O |
| `content` | string | 조문 전문 또는 사건명 | **조문 전문** | 사건명만 |
| `source` | string | 출처 구분 | 법제처_법령 | 법제처_판례 |
| `category` | string | 문서 유형 | 법률/시행령 등 | 판례 |
| `law_number` | string | 법률/조항 번호 | - | - |
| `case_number` | string | 사건번호 | - | O |
| `decision_date` | string | 판결일 | - | O |
| `court` | string | 법원명 | - | O |

### 검색 방식

- **시맨틱 하이브리드 검색**: 키워드 매칭 + 시맨틱 리랭킹(`legal-semantic-config`)
- **검색 대상**: 법령 조문 전문(1,001건) 중심으로 검색 — 판례는 사건명만 있어 매칭 가능성 낮음
- **인메모리 캐시**: 동일 쿼리 1시간 TTL 캐시로 반복 호출 시 API 비용 절감
- **기본 반환 수**: 쿼리당 상위 5건 (관련성 점수 기준 정렬)

## 🛠 기술 스택

| 영역 | 기술 스택 |
| :--- | :--- |
| **Frontend** | Next.js 15, React 19, Assistant UI, TailwindCSS, Zustand |
| **Backend** | Python 3.13+, FastAPI (Async), UV (Package Manager) |
| **Agent** | LangGraph (Orchestration + Multi-Agent), LangChain, `create_react_agent` |
| **AI / Model** | Azure OpenAI (GPT-5.1 Reasoning, GPT-4o Fast), Azure AI Search (Semantic RAG) |
| **DB / Infra** | Azure CosmosDB (History/Persistence), Azure Key Vault (Secrets) |
