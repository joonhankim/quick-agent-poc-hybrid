"""
Azure AI Search 통합 도구
LangGraph 에이전트가 법률 문서를 검색할 때 사용하는 LangChain Tool
"""
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.tools import tool
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from api.core.logger import APILogger

logger = APILogger()

SELECT_FIELDS = [
    "id", "title", "content", "source", "category",
    "law_number", "case_number", "decision_date", "court",
]

# 모듈 레벨 인메모리 캐시 (TTL: 1시간)
_search_cache: Dict[str, Tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 3600  # 1시간

# 모듈 레벨 SearchClient 싱글턴
_search_client: Optional[SearchClient] = None


def _get_cache_key(query: str, top_k: int) -> str:
    """캐시 키 생성"""
    raw = f"{query}:{top_k}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_from_cache(key: str) -> Optional[str]:
    """캐시에서 결과 조회 (TTL 만료 시 None 반환)"""
    if key in _search_cache:
        cached_time, cached_result = _search_cache[key]
        if time.time() - cached_time < _CACHE_TTL_SECONDS:
            return cached_result
        else:
            del _search_cache[key]
    return None


def _set_cache(key: str, result: str) -> None:
    """캐시에 결과 저장"""
    _search_cache[key] = (time.time(), result)


def _get_search_client() -> SearchClient:
    """SearchClient 싱글턴 lazy 초기화"""
    global _search_client
    if _search_client is None:
        from config.settings import get_config

        config = get_config()
        endpoint = config.get("AZURE_SEARCH_ENDPOINT")
        key = config.get("AZURE_SEARCH_API_KEY")
        index_name = config.get("AZURE_SEARCH_INDEX_NAME", "law-unified-index")

        if not endpoint or not key:
            raise ValueError(
                "AZURE_SEARCH_ENDPOINT와 AZURE_SEARCH_API_KEY 환경변수가 설정되어야 합니다."
            )

        _search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(key),
        )
    return _search_client


def _format_results(results: List[Dict[str, Any]]) -> str:
    """검색 결과를 에이전트가 읽기 쉬운 형태로 포맷팅"""
    if not results:
        return "검색 결과가 없습니다."

    formatted = f"총 {len(results)}개의 관련 문서를 찾았습니다:\n\n"

    for idx, doc in enumerate(results, 1):
        formatted += f"[문서 {idx}] {doc.get('title', '제목 없음')}\n"
        formatted += f"출처: {doc.get('source', '알 수 없음')}\n"

        score = doc.get("relevance_score", 0)
        if score:
            formatted += f"관련성: {score:.4f}\n"

        content = doc.get("content", "")
        if content:
            formatted += f"내용: {content[:500]}...\n" if len(content) > 500 else f"내용: {content}\n"

        metadata_fields = {
            "분류": doc.get("category"),
            "법률번호": doc.get("law_number"),
            "사건번호": doc.get("case_number"),
            "판결일": doc.get("decision_date"),
            "법원": doc.get("court"),
        }
        metadata = {k: v for k, v in metadata_fields.items() if v}
        if metadata:
            formatted += f"메타데이터: {metadata}\n"

        formatted += "\n" + "-" * 80 + "\n\n"

    return formatted


@tool
def azure_legal_search(query: str, top_k: int = 5) -> str:
    """법률 문서 데이터베이스에서 관련 문서를 검색합니다.
    입력: 검색 쿼리 (법률 용어, 조항 번호, 판례 번호 등)
    출력: 관련성 높은 법률 문서 목록 (제목, 내용 요약, 출처)

    Args:
        query: 검색 쿼리
        top_k: 반환할 문서 개수 (기본값: 5)
    """
    from agent.utils.callbacks import push_status

    logger.info(f"Azure AI Search 실행 - 쿼리: {query}, top_k: {top_k}")

    # 캐시 확인
    cache_key = _get_cache_key(query, top_k)
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        logger.info(f"캐시 히트 - 쿼리: {query}")
        push_status("캐시된 검색 결과를 사용합니다.")
        return cached_result

    push_status("관련 법률 문서를 검색하고 있습니다...")

    try:
        client = _get_search_client()
        results = client.search(
            search_text=query,
            query_type="semantic",
            semantic_configuration_name="legal-semantic-config",
            top=top_k,
            select=SELECT_FIELDS,
        )

        docs: List[Dict[str, Any]] = []
        for result in results:
            doc = {field: result.get(field) for field in SELECT_FIELDS}
            doc["relevance_score"] = result.get("@search.reranker_score", result.get("@search.score", 0))
            docs.append(doc)

        formatted = _format_results(docs)
        logger.info(f"검색 완료 - {len(docs)}개 문서 발견")
        for idx, doc in enumerate(docs, 1):
            score = doc.get("relevance_score", 0)
            title = doc.get("title", "제목 없음")
            case_num = doc.get("case_number", "")
            law_num = doc.get("law_number", "")
            ref = case_num or law_num or "-"
            content_len = len(doc.get("content", ""))
            logger.info(f"  [{idx}] {title} | {ref} | score={score:.4f} | content={content_len}자")
        push_status(f"{len(docs)}개의 관련 문서를 찾았습니다. 법률 분석 중...")

        # 캐시 저장
        _set_cache(cache_key, formatted)

        return formatted

    except Exception as e:
        logger.error(f"Azure AI Search 오류: {e}")
        return f"검색 중 오류가 발생했습니다: {e}"
