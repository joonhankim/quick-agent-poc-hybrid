from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Annotated, Sequence
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages


class AgentState(BaseModel):
    """Plan-and-Execute Agent의 state 정의"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # 기본 정보
    id: str
    user_no: str
    chat_id: str
    documents: Optional[List] = Field(
        default_factory=list
    )  # /chat api 호출 시 검색에 체크한 문서. 리스트로 예상되어 미리 스키마에 추가
    room_id: str
    user_query: str
    exe_date: str

    # 대화 이력
    history: Annotated[Sequence[HumanMessage | AIMessage], add_messages] = []

    # CosmosDB 히스토리 전용 (add_messages 리듀서 없음 → MemorySaver에 의해 누적되지 않음)
    chat_context: List[HumanMessage | AIMessage] = Field(default_factory=list)

    # 모델 설정
    model_name: str = "gpt-5"
    embedder_name: Optional[str] = "text-embedding-3-large"

    # 최종 응답
    final_response: Optional[str] = None
    final_response_metadata: Dict[str, Any] = {}

    # 메타데이터
    planning_metadata: Dict[str, Any] = {}
    execution_metadata: Dict[str, Any] = {}
    agent_metadata: Dict[str, Any] = {}  # 에이전트 실행 결과 및 메타데이터
    error_logs: List[str] = []

    # 라우팅 정보
    next_step: Optional[str] = None
    route: Optional[str] = "legal"  # "general" 또는 "legal" (default: legal)
    active_agent: Optional[str] = None  # 재시도 시 어떤 에이전트로 돌아갈지 결정

    # 임베딩 캐시 (기존 코드 재사용)
    embedding_refs: Dict[str, str] = {}

    # 스트리밍 토큰 전송을 위한 큐 (런타임에서 주입)
    streaming_queue: Optional[Any] = None

    # 검색 참조 문서 정보
    search_reference_info: List = []

    # 이미지 정보 (통계자료)
    image_info: List = []

    # history 기반으로 재생성한 query
    reform_user_query: Optional[str] = ""

    # rag 최종 결과 document_id 리스트
    rag_document_ids: List[str] = []

    # 스텝별 상태 messages
    step_messages: List[str] = []
    
    # 법무지원 RAG 관련 필드
    search_results: List[Dict[str, Any]] = []  # Azure AI Search 검색 결과
    legal_analysis_metadata: Dict[str, Any] = {}  # 법률 분석 메타데이터 (참조 조항, 판례 등)
    
    # [FSM] 재시도 로직을 위한 필드
    retry_count: int = 0  # 현재 재시도 횟수
    max_retries: int = 1  # 최대 재시도 횟수
    validation_status: str = "pending"  # pending, passed, failed