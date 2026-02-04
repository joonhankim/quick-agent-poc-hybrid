# HD현대 법무 지원 Agent (Hybrid Edition)

Azure OpenAI, LangGraph 그리고 CrewAI 기반의 HD현대 법무 지원 AI Agent 시스템

## 📋 프로젝트 개요

HD현대의 법무팀을 위한 AI 기반 지원 시스템입니다. 계약서 검토, 법률 자문, 내부 규정 확인 등 법무 업무를 효율적으로 처리할 수 있도록 설계되었습니다.

### 🎯 주요 목적
- **계약서 자동 검토**: 위험 조항 식별 및 수정 제안
- **법률 규정 준수 확인**: 내부 결재 규정 및 법무 가이드라인 검증
- **지식 기반 챗봇**: 법무 관련 질의응답 및 문서 검색
- **업무 효율화**: 반복적인 법무 검토 작업 자동화

## 🏗️ 시스템 아키텍처

```
quick-agent-poc-hybrid/
├── api/                      # Backend API (FastAPI)
│   ├── main.py              # FastAPI 메인 애플리케이션
│   ├── routers/
│   │   ├── chat.py          # 채팅 API 엔드포인트 (SSE 스트리밍)
│   │   ├── db.py            # 데이터베이스 API
│   │   └── healthcheck.py   # 헬스체크 엔드포인트
│   └── core/
│       ├── logger.py        # 로깅 유틸리티
│       └── singleton.py     # 싱글톤 패턴
├── agent/                   # AI Agent 로직 (Hybrid LangGraph + CrewAI)
│   ├── graph/
│   │   └── core_graph.py    # Hybrid 워크플로우 (Orchestrator)
│   ├── node/
│   │   └── core_node.py     # CrewAI 호출을 포함한 그래프 노드
│   ├── crews/               # [NEW] CrewAI 전문 에이전트 팀
│   │   ├── legal_rag_crew.py # 검색/분석/작성 협업 크루
│   ├── tools/               # [NEW] 에이전트 전용 도구
│   │   └── azure_search_tool.py # Azure AI Search 연동 (RAG)
│   ├── schema/
│   │   └── state.py         # Crew 메타데이터가 포함된 상태 정의
├── frontend/                # Frontend (Next.js 15)
├── start.sh                 # 통합 실행 스크립트
├── pyproject.toml           # Python 의존성 (uv)
└── .env                     # 환경변수 (gitignore)
```

### 🤖 하이브리드 아키텍처 (Hybrid Orchestration)
본 시스템은 **LangGraph**의 견고한 워크플로우 제어와 **CrewAI**의 자율적인 에이전트 협업 지능을 결합한 하이브리드 구조를 채택하고 있습니다.

- **LangGraph (Orchestrator)**: 전체적인 비즈니스 로직의 흐름을 제어하고 대화 상태(State)를 안전하게 관리합니다.
- **CrewAI (Expert Team)**: 특정 복잡한 작업(법률 리서치, 조항 분석 등)이 필요한 노드에서 3인의 전문 에이전트 팀(검색 전문가, 법률 분석가, 법률 작성자)이 자율적으로 협업하여 고품질의 결과를 도출합니다.


## ✨ 핵심 기능

### 🤖 AI Agent 기능
- **LangGraph + CrewAI 하이브리드**: 전역 워크플로우 제어와 에이전트 간 자율 협업의 결합
- **전문 법률 크루 가동**: 검색 전문가, 법률 분석가, 답변 작성자로 구성된 전문 팀 협업
- **Azure AI Search 기반 RAG**: 고도화된 벡터 검색을 통한 신뢰할 수 있는 법률 근거 제시
- **GPT-4o 통합**: 최신 언어 모델을 통한 고품질 추론 및 응답 생성
- **실시간 스트리밍**: Server-Sent Events(SSE)를 통한 즉각적인 응답 제공
- **대화 이력 관리**: CosmosDB를 활용한 지속적인 대화 컨텍스트 유지

### 🛠️ 시스템 기능
- **안전한 에러 핸들링**: 포괄적인 예외 처리 및 회복 메커니즘
- **환경별 설정**: local/development/production 환경 지원
- **Azure Key Vault 연동**: 중앙화된 비밀 관리 및 보안 강화
- **CORS 지원**: 크로스 오리진 요청 처리

### 🎨 사용자 인터페이스
- **HD현대 브랜딩**: 기업 디자인 가이드라인 적용
- **반응형 디자인**: 다양한 디바이스 지원
- **직관적인 채팅 인터페이스**: 사용자 친화적인 UI/UX
- **예시 질문 제공**: 법무 관련 샘플 질의로 사용 편의성 증대

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI 0.115+ (고성능 ASGI 프레임워크)
- **ASGI Server**: uvicorn (비동기 웹 서버)
- **AI/ML**: 
  - LangChain 0.3+ (LLM 애플리케이션 프레임워크)
  - LangGraph (워크플로우 오케스트레이션)
  - CrewAI (다중 에이전트 협업 체계)
  - Azure OpenAI (GPT-4o 모델)
  - Azure AI Search (고도화된 RAG 엔진)
- **Python**: 3.13+ (최신 Python 버전)
- **Package Manager**: uv (고속 패키지 매니저)
- **Database**: Azure Cosmos DB (NoSQL 데이터베이스)

### Frontend
- **Framework**: Next.js 15 (React 풀스택 프레임워크)
- **Runtime**: React 19 (최신 React 버전)
- **UI Components**: 
  - Assistant UI (채팅 전용 컴포넌트 라이브러리)
  - Radix UI (접근성 높은 원시 컴포넌트)
- **Styling**: Tailwind CSS (유틸리티 우선 CSS 프레임워크)
- **Language**: TypeScript (타입 안전한 JavaScript)

### DevOps & Infrastructure
- **Cloud**: Microsoft Azure
- **Containerization**: Docker (향후 지원 예정)
- **Secret Management**: Azure Key Vault
- **Monitoring**: Application Insights (향후 연동 예정)

## 🚀 설치 및 실행

### 📋 1. 사전 요구사항

- **Python**: 3.13+ ([uv 설치 가이드](https://docs.astral.sh/uv/))
- **Node.js**: 18+ (LTS 버전 권장)
- **uv**: Python 패키지 매니저 (pip보다 10-100배 빠름)
- **Azure OpenAI**: API 키 및 엔드포인트
- **Azure Cosmos DB**: (선택) 대화 이력 저장용

### ⚙️ 2. 환경 설정

```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd hanhwa-general-insurance-agent

# 2. .env 파일 생성
cp .env.example .env

# 3. .env 파일 편집 (필수 환경변수)
nano .env
```

#### 필수 환경변수 설정
```bash
# 기본 환경 설정
APP_ENV=local

# Azure OpenAI 설정
agent-azure-openai-api-key=your-azure-openai-api-key
agent-azure-openai-endpoint=https://your-resource.openai.azure.com/
agent-azure-openai-api-version=2024-08-01-preview
agent-azure-openai-model-name=gpt-4o

# 선택: Cosmos DB 설정 (대화 이력 저장)
agent-cosmos-endpoint=https://your-cosmos-account.documents.azure.com:443/
agent-cosmos-key=your-cosmos-db-key
```

### 📦 3. 의존성 설치

#### Backend (Python)
```bash
# uv를 사용한 고속 의존성 설치
uv sync

# 또는 pip 사용 (권장하지 않음)
pip install -r requirements.txt  # requirements.txt가 있는 경우
```

#### Frontend (Node.js)
```bash
cd frontend

# npm 사용
npm install

# 또는 pnpm 사용 (더 빠름)
pnpm install

cd ..
```

### 🏃‍♂️ 4. 서버 실행

#### 방법 1: 통합 실행 (권장) 👍
```bash
# 한 번에 Frontend + Backend 실행
./start.sh
```

#### 방법 2: 개별 실행

**Backend 실행**
```bash
# 가상환경 활성화
source .venv/bin/activate  # Linux/Mac
# 또는 .venv\Scripts\activate  # Windows

# FastAPI 서버 실행
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend 실행** (별도 터미널에서)
```bash
cd frontend
npm run dev
# 또는 pnpm dev
```

### 🌐 5. 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Frontend** | http://localhost:3000 | 메인 어플리케이션 |
| **Backend API** | http://localhost:8000 | API 서버 |
| **API 문서** | http://localhost:8000/docs | Swagger UI |
| **헬스체크** | http://localhost:8000/health | 서버 상태 확인 |
| **OpenAPI 스펙** | http://localhost:8000/openapi.json | API 명세 |

### 🔍 6. 실행 확인

```bash
# Backend 상태 확인
curl http://localhost:8000/health
# 응답: {"status": "healthy"}

# Frontend 접속 테스트
# 브라우저에서 http://localhost:3000 접속
# HD현대 로고와 "법무시스템"이 보이면 성공
```

## 📚 API 문서

### 🔄 채팅 API

#### POST /agent/chat

채팅 메시지를 전송하고 SSE(Server-Sent Events) 스트리밍 응답을 받습니다.

**Request Headers**
```http
Content-Type: application/json
```

**Request Body**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "이 계약서에서 위험한 조항을 찾아주세요"
    }
  ],
  "chat_id": "chat-12345",
  "user_no": "user-001",
  "room_id": "room-001"
}
```

**Response**
- Content-Type: `text/event-stream`
- SSE 형식의 실시간 스트리밍 응답

**Response Format**
```
data: {"type": "status", "content": ">>> Graph workflow Start <<<"}

data: {"type": "content", "content": "계약서를 검토한 결과"}

data: {"type": "content", "content": ", 다음과 같은 위험 조항이 발견되었습니다"}

data: {"type": "complete", "content": {"message": "전체 응답 내용", "metadata": {}}}
```

**Response Types**
| Type | Description |
|------|-------------|
| `status` | 워크플로우 상태 메시지 |
| `content` | 실시간 응답 내용 (일부 텍스트) |
| `complete` | 최종 완료 응답 |
| `error` | 에러 메시지 |

### 🗄️ 데이터베이스 API

#### GET /db/get_room_history

특정 사용자와 방의 대화 이력을 조회합니다.

**Query Parameters**
```
user_no: string (required) - 사용자 ID
room_id: string (required) - 방 ID
```

**Response Example**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "계약서 검토 요청",
      "timestamp": "2024-01-20T10:30:00Z"
    },
    {
      "role": "assistant", 
      "content": "계약서 분석 결과...",
      "timestamp": "2024-01-20T10:30:15Z"
    }
  ]
}
```

#### POST /db/save_conversation

대화 내용을 CosmosDB에 저장합니다.

**Request Body**
```json
{
  "chat_id": "chat-12345",
  "user_no": "user-001",
  "room_id": "room-001",
  "user_query": "원본 질문",
  "output": "AI 응답",
  "metadata": {
    "model": "gpt-4o",
    "tokens": 1500
  }
}
```

### 💊 헬스체크 API

#### GET /health

서버 상태를 확인합니다.

**Response**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "version": "0.1.0"
}
```

## ⚙️ 환경변수 설정

### 🔑 필수 환경변수

| 변수명 | 설명 | 예시값 | 비고 |
|--------|------|--------|------|
| `APP_ENV` | 실행 환경 | `local` | `development`, `production` |
| `agent-azure-openai-api-key` | Azure OpenAI API 키 | `xxxxxxxx` | Azure Portal에서 발급 |
| `agent-azure-openai-endpoint` | Azure OpenAI 엔드포인트 | `https://resource.openai.azure.com/` | 리소스 URL |
| `agent-azure-openai-api-version` | API 버전 | `2024-08-01-preview` | 고정값 권장 |
| `agent-azure-openai-model-name` | 사용할 모델 | `gpt-4o` | `gpt-4o-mini`도 가능 |

### 🗄️ 데이터베이스 환경변수 (선택)

| 변수명 | 설명 | 예시값 | 비고 |
|--------|------|--------|------|
| `agent-cosmos-endpoint` | Cosmos DB 엔드포인트 | `https://account.documents.azure.com:443/` | 대화 이력 저장용 |
| `agent-cosmos-key` | Cosmos DB 키 | `xxxxxxxx` | Primary/Secondary 키 |

### 🔍 검색 및 모니터링 (선택)

| 변수명 | 설명 | 예시값 |
|--------|------|--------|
| `agent-azure-search-endpoint` | Azure Search 엔드포인트 | `https://search.service.search.windows.net` |
| `agent-azure-search-key` | Azure Search API 키 | `xxxxxxxx` |
| `agent-application-insights-connection-string` | App Insights 연결 | `InstrumentationKey=xxx` |

### 📝 .env 파일 예시

```bash
# 기본 환경 설정
APP_ENV=local

# Azure OpenAI (필수)
agent-azure-openai-api-key=your-openai-api-key-here
agent-azure-openai-endpoint=https://your-openai-resource.openai.azure.com/
agent-azure-openai-api-version=2024-08-01-preview
agent-azure-openai-model-name=gpt-4o

# Cosmos DB (선택 - 대화 이력 저장)
agent-cosmos-endpoint=https://your-cosmos-account.documents.azure.com:443/
agent-cosmos-key=your-cosmos-db-key

# Azure Search (선택 - RAG 기능)
agent-azure-search-endpoint=https://your-search-service.search.windows.net
agent-azure-search-key=your-search-api-key

# Application Insights (선택 - 모니터링)
agent-application-insights-connection-string=InstrumentationKey=your-key
```

> **💡 팁**: `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 필요한 값만 설정하세요.

## 👨‍💻 개발 가이드

### 📊 로깅 및 디버깅

#### 로그 확인
```bash
# FastAPI 애플리케이션 로그 (uvicorn 실행 시)
# 로그는 터미널에 직접 표시됨

# 개발 환경에서 디버그 모드 활성화
APP_ENV=local uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

#### 브라우저 개발자 도구
```bash
# Frontend 디버깅
# 1. 브라우저 F12 개발자 도구 열기
# 2. Network 탭에서 API 요청/응답 확인
# 3. Console 탭에서 SSE 스트리밍 메시지 확인
```

### 🏗️ 개발 워크플로우

#### 1. LangGraph 워크플로우 수정

새로운 노드 추가 또는 기존 노드 수정:

```python
# agent/node/core_node.py
def new_analysis_node(state: AgentState) -> AgentState:
    """새로운 분석 노드"""
    user_query = state.user_query
    
    # 분석 로직 구현
    analysis_result = analyze_contract(user_query)
    
    state.analysis_result = analysis_result
    state.step_messages.append("분석 완료")
    return state

# agent/graph/core_graph.py
def create_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("new_analysis_node", new_analysis_node)
    
    # 노드 연결
    workflow.add_edge("start_node", "new_analysis_node")
    workflow.add_edge("new_analysis_node", "generate_response_node")
    
    return workflow.compile()
```

#### 2. 새로운 API 엔드포인트 추가

```python
# api/routers/legal_analyzer.py
from fastapi import APIRouter, HTTPException
from agent.schema.legal import LegalAnalysisRequest

router = APIRouter()

@router.post("/analyze-contract")
async def analyze_contract(request: LegalAnalysisRequest):
    """계약서 분석 API"""
    try:
        # 분석 로직 호출
        result = await analyze_legal_document(request.document)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# api/main.py
from api.routers import legal_analyzer
app.include_router(legal_analyzer.router, prefix="/api", tags=["legal"])
```

#### 3. 프론트엔드 컴포넌트 추가

```typescript
// frontend/components/legal/ContractAnalyzer.tsx
'use client';

import { useState } from 'react';

export const ContractAnalyzer = () => {
  const [document, setDocument] = useState('');
  const [analysis, setAnalysis] = useState(null);

  const handleAnalyze = async () => {
    const response = await fetch('/api/analyze-contract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document })
    });
    
    const result = await response.json();
    setAnalysis(result.result);
  };

  return (
    <div>
      <textarea 
        value={document} 
        onChange={(e) => setDocument(e.target.value)}
        placeholder="계약서 내용을 입력하세요..."
      />
      <button onClick={handleAnalyze}>분석</button>
      {analysis && <pre>{JSON.stringify(analysis, null, 2)}</pre>}
    </div>
  );
};
```

### 🔧 환경별 설정

#### Local 개발 환경
```bash
# .env 파일 사용
APP_ENV=local

# 환경변수는 .env 파일에서 로드
ConfigManager._load_from_env_file()
```

#### Production 환경 (Azure Container Apps)
```bash
# Azure Key Vault 사용
APP_ENV=production

# Key Vault 참조를 통한 환경변수 로드
# Container App 설정에서 Key Vault 시크릿 참조
ConfigManager._load_from_key_vault()
```

### 🧪 테스트

#### 단위 테스트 예시
```python
# tests/test_agent_logic.py
import pytest
from agent.node.core_node import generate_response_node
from agent.schema.state import AgentState

@pytest.mark.asyncio
async def test_generate_response_node():
    """응답 생성 노드 테스트"""
    state = AgentState(
        user_query="테스트 질문",
        history=[]
    )
    
    result = await generate_response_node(state)
    
    assert result.final_response is not None
    assert len(result.final_response) > 0
```

### 📝 코드 스타일 가이드

- **Python**: Black + isort 코드 포맷팅
- **TypeScript**: Prettier + ESLint
- **커밋 메시지**: Conventional Commits 형식 권장
- **PR 규칙**: 최소 1명의 리뷰어 승인 필요

## 🚀 배포 가이드

### ☁️ Azure Container Apps 배포

#### 1. 사전 준비
```bash
# Azure CLI 로그인
az login

# 리소스 그룹 생성
az group create --name hd-legal-ai-rg --location koreacentral

# Container Registry 생성
az acr create --resource-group hd-legal-ai-rg --name hdlegalaiacr --sku Basic
```

#### 2. Docker 이미지 빌드 및 푸시
```dockerfile
# Dockerfile (향후 생성 예정)
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv sync --frozen

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 이미지 빌드
docker build -t hdlegalaiacr.azurecr.io/hd-legal-ai:latest .

# ACR 로그인 및 푸시
az acr login --name hdlegalaiacr
docker push hdlegalaiacr.azurecr.io/hd-legal-ai:latest
```

#### 3. Key Vault 설정
```bash
# Key Vault 생성
az keyvault create --name hd-legal-ai-kv --resource-group hd-legal-ai-rg

# 시크릿 설정
az keyvault secret set --vault-name hd-legal-ai-kv --name "agent-azure-openai-api-key" --value "your-api-key"
az keyvault secret set --vault-name hd-legal-ai-kv --name "agent-azure-openai-endpoint" --value "your-endpoint"
```

#### 4. Container App 생성
```bash
# Container App 생성
az containerapp create \
  --resource-group hd-legal-ai-rg \
  --name hd-legal-ai-app \
  --image hdlegalaiacr.azurecr.io/hd-legal-ai:latest \
  --target-port 8000 \
  --ingress external \
  --environment hd-legal-ai-env

# Key Vault 연동
az containerapp secret show \
  --resource-group hd-legal-ai-rg \
  --name hd-legal-ai-app \
  --secret-name agent-azure-openai-api-key \
  --key-vault-secret-id <secret-id>
```

## 🔧 트러블슈팅

### ⚡ 일반적인 문제 해결

#### Backend 서버 시작 실패
```bash
# 1. 의존성 재설치
uv sync --reinstall

# 2. Python 버전 확인
python --version  # 3.13+ 필요

# 3. 환경변수 확인
cat .env | grep -E "(agent-azure-openai|APP_ENV)"

# 4. 포트 충돌 확인
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

#### Frontend 연결 실패
```bash
# 1. Backend 상태 확인
curl http://localhost:8000/health

# 2. CORS 설정 확인
# api/main.py의 allow_origins 확인
# http://localhost:3000이 허용되어 있는지 확인

# 3. Frontend API URL 확인
# frontend/app/api/chat/route.ts의 백엔드 URL 확인
```

#### Azure OpenAI 연결 오류
```bash
# 1. API 키 및 엔드포인트 확인
echo "API Key: ${agent-azure-openai-api-key:0:10}..."
echo "Endpoint: $agent-azure-openai-endpoint"

# 2. API 테스트
curl -X POST "$agent-azure-openai-endpoint/openai/deployments/$agent-azure-openai-model-name/chat/completions?api-version=$agent-azure-openai-api-version" \
  -H "Content-Type: application/json" \
  -H "api-key: $agent-azure-openai-api-key" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

#### SSE 스트리밍 문제
```bash
# 1. curl로 스트리밍 테스트
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"chat_id":"test","user_no":"test","room_id":"test"}' \
  -N

# 2. 브라우저 네트워크 탭에서 EventSource 확인
# Content-Type: text/event-stream인지 확인
```

### 🐛 디버깅 팁

#### 로그 레벨 조정
```python
# api/main.py
import logging
logging.basicConfig(level=logging.DEBUG)

# 또는 uvicorn 실행 시
uvicorn api.main:app --log-level debug
```

#### LangGraph 디버깅
```python
# agent/graph/core_graph.py
import langchain
langchain.debug = True  # 상세한 LangChain 로그 활성화

# 그래프 실행 시 상태 확인
async for state in base_graph.astream(initial_state, config={'callbacks': [callback]}):
    print(f"Current state: {state}")
```

## 📄 라이선스

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🤝 기여 가이드

### 기여 방법
1. 이슈 생성: 버그 리포트 또는 기능 제안
2. Fork 레포지토리 및 브랜치 생성
3. 변경 사항 커밋 (컨벤셔널 커밋 형식 권장)
4. 테스트 실행 및 코드 스타일 확인
5. Pull Request 생성

### 커밋 메시지 규칙
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅 (로직 변경 없음)
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드/프로세스 수정
```

### 코드 리뷰 프로세스
- 모든 PR은 최소 1명의 리뷰어 승인 필요
- 자동화된 CI/CD 파이프라인 통과 필요
- 테스트 커버리지 80% 이상 권장

---

📞 **문의**: HD현대 법무팀 또는 개발팀에 문의해주세요.
