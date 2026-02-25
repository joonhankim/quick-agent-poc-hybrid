"""
Tavily 웹 검색 도구
LangGraph 에이전트가 최신 법률 동향, 판례 뉴스, 법률 해석을 검색할 때 사용하는 LangChain Tool
"""
import hashlib
import time
from typing import Dict, Optional, Tuple

from langchain_core.tools import tool

from api.core.logger import APILogger

logger = APILogger()

# 모듈 레벨 인메모리 캐시 (TTL: 1시간)
_search_cache: Dict[str, Tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 3600

# 모듈 레벨 TavilyClient 싱글턴
_tavily_client = None


def _get_cache_key(query: str, max_results: int) -> str:
    """캐시 키 생성"""
    raw = f"tavily:{query}:{max_results}"
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


def _get_tavily_client():
    """TavilyClient 싱글턴 lazy 초기화"""
    global _tavily_client
    if _tavily_client is None:
        from config.settings import get_config
        from tavily import TavilyClient

        config = get_config()
        api_key = config.get("TAVILY_API_KEY")

        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY 환경변수가 설정되어야 합니다."
            )

        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def _format_results(results: list) -> str:
    """검색 결과를 에이전트가 읽기 쉬운 형태로 포맷팅"""
    if not results:
        return "웹 검색 결과가 없습니다."

    formatted = f"총 {len(results)}개의 웹 검색 결과를 찾았습니다:\n\n"

    for idx, item in enumerate(results, 1):
        title = item.get("title", "제목 없음")
        url = item.get("url", "")
        content = item.get("content", "")
        score = item.get("score", 0)

        formatted += f"[결과 {idx}] {title}\n"
        formatted += f"URL: {url}\n"
        if score:
            formatted += f"관련성: {score:.4f}\n"
        if content:
            if len(content) > 2000:
                formatted += f"내용: {content[:2000]}\n[... 이하 생략 (전체 {len(content)}자)]\n"
            else:
                formatted += f"내용: {content}\n"
        formatted += "\n" + "-" * 80 + "\n\n"

    return formatted


@tool
def tavily_legal_search(query: str, max_results: int = 5) -> str:
    """최신 판례 동향, 법률 개정 뉴스, 법률 해석 등을 웹에서 검색합니다.
    법령 DB에 없는 최신 정보나 법률 해석, 뉴스가 필요할 때 사용하세요.
    입력: 검색 쿼리 (법률 동향, 판례 뉴스, 법률 해석 관련 키워드)
    출력: 관련 웹 검색 결과 목록 (제목, URL, 내용 요약)

    Args:
        query: 검색 쿼리
        max_results: 반환할 결과 개수 (기본값: 5)
    """
    from agent.utils.callbacks import push_status

    logger.info(f"Tavily 웹 검색 실행 - 쿼리: {query}, max_results: {max_results}")

    # 캐시 확인
    cache_key = _get_cache_key(query, max_results)
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        logger.info(f"Tavily 캐시 히트 - 쿼리: {query}")
        push_status("캐시된 웹 검색 결과를 사용합니다.")
        return cached_result

    push_status("최신 법률 동향을 웹에서 검색하고 있습니다...")

    try:
        client = _get_tavily_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
        )

        results = response.get("results", [])
        formatted = _format_results(results)
        logger.info(f"Tavily 검색 완료 - {len(results)}개 결과 발견")
        for idx, item in enumerate(results, 1):
            title = item.get("title", "제목 없음")
            url = item.get("url", "")
            score = item.get("score", 0)
            logger.info(f"  [{idx}] {title} | {url} | score={score:.4f}")
        push_status(f"{len(results)}개의 웹 검색 결과를 찾았습니다. 분석 중...")

        # 캐시 저장
        _set_cache(cache_key, formatted)

        return formatted

    except Exception as e:
        logger.error(f"Tavily 웹 검색 오류: {e}")
        return f"웹 검색 중 오류가 발생했습니다: {e}"
