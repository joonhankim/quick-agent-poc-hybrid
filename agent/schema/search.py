from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone


_date = datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S")

class SearchResultInfo(BaseModel):
    """검색 결과의 메타 정보"""

    filename: Optional[str] = None
    create_date: Optional[str] = None
    update_date: Optional[str] = None


class SearchResult(BaseModel):
    """개별 검색 결과"""

    id: Optional[str] = ""
    category_code: Optional[str] = ""
    info: Optional[SearchResultInfo] = Field(default_factory=dict)
    product_name: Optional[str] = ""
    page_number: Optional[int] = None
    KO_content_summary: Optional[str] = ""
    EN_content_summary: Optional[str] = ""
    KO_content: Optional[str] = ""
    EN_content: Optional[str] = ""
    section_title: Optional[str] = ""
    search_score: Optional[float] = Field(0.0, alias="@search.score")
    search_reranker_score: Optional[float] = Field(0.0, alias="@search.reranker_score")


class SearchQuery(BaseModel):
    """서치 쿼리 및 그 결과들"""

    search_query: Optional[str]
    index: Optional[str]
    search_results: Optional[List[SearchResult]] = Field(default_factory=list)


class SubQuery(BaseModel):
    """서브 쿼리 및 하위 스키마"""

    sub_query: str
    search_queries: Optional[List[SearchQuery]] = Field(default_factory=list)


class SearchData(BaseModel):
    "전체 검색 데이터 스키마"

    origin_query: str
    sub_queries: Optional[List[SubQuery]] = Field(default_factory=list)
