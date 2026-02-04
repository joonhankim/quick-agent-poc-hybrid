"""
Azure AI Search 통합 도구
CrewAI 에이전트가 법률 문서를 검색할 때 사용하는 도구
"""
from typing import List, Dict, Any, Optional
from crewai.tools import BaseTool
from pydantic import Field

from api.core.logger import APILogger

logger = APILogger()


class AzureSearchTool(BaseTool):
    """
    Azure AI Search를 통해 법률 문서를 검색하는 도구
    
    TODO: Azure AI Search 배포 후 실제 연동 구현 필요
    - Azure AI Search endpoint 설정
    - API key 또는 Managed Identity 인증
    - 검색 인덱스 이름 설정
    """
    
    name: str = "azure_legal_search"
    description: str = """법률 문서 데이터베이스에서 관련 문서를 검색합니다.
    입력: 검색 쿼리 (법률 용어, 조항 번호, 판례 번호 등)
    출력: 관련성 높은 법률 문서 목록 (제목, 내용 요약, 출처)"""
    
    # Azure AI Search 설정 (추후 환경변수 또는 config에서 로드)
    search_endpoint: Optional[str] = Field(default=None, description="Azure AI Search endpoint")
    search_key: Optional[str] = Field(default=None, description="Azure AI Search API key")
    index_name: str = Field(default="legal-documents", description="검색 인덱스 이름")
    
    def _run(self, query: str, top_k: int = 5) -> str:
        """
        법률 문서 검색 실행
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 개수
            
        Returns:
            str: 검색 결과 (포맷팅된 문자열)
        """
        logger.info(f"Azure AI Search 실행 - 쿼리: {query}, top_k: {top_k}")
        
        # TODO: Azure AI Search 실제 연동
        # from azure.search.documents import SearchClient
        # from azure.core.credentials import AzureKeyCredential
        # 
        # search_client = SearchClient(
        #     endpoint=self.search_endpoint,
        #     index_name=self.index_name,
        #     credential=AzureKeyCredential(self.search_key)
        # )
        # 
        # results = search_client.search(
        #     search_text=query,
        #     top=top_k,
        #     select=["title", "content", "source", "metadata"]
        # )
        
        # 현재는 Mock 데이터 반환 (Azure AI Search 배포 전)
        mock_results = self._get_mock_results(query, top_k)
        
        # 결과 포맷팅
        formatted_results = self._format_results(mock_results)
        
        logger.info(f"검색 완료 - {len(mock_results)}개 문서 발견")
        return formatted_results
    
    def _get_mock_results(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Mock 검색 결과 생성 (Azure AI Search 배포 전 테스트용)
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 개수
            
        Returns:
            List[Dict]: Mock 문서 목록
        """
        mock_documents = [
            {
                "title": "민법 제750조 - 불법행위의 내용",
                "content": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.",
                "source": "민법",
                "relevance_score": 0.95,
                "metadata": {
                    "document_type": "법령",
                    "category": "민법",
                    "article_number": "제750조"
                }
            },
            {
                "title": "대법원 2020다12345 판결",
                "content": "불법행위로 인한 손해배상청구권의 소멸시효는 피해자나 그 법정대리인이 손해 및 가해자를 안 날로부터 3년간 행사하지 아니하면 시효로 소멸한다.",
                "source": "판례",
                "relevance_score": 0.88,
                "metadata": {
                    "document_type": "판례",
                    "court": "대법원",
                    "case_number": "2020다12345",
                    "date": "2020-05-15"
                }
            },
            {
                "title": "표준 근로계약서 작성 가이드",
                "content": "근로계약서는 근로자와 사용자 간의 권리와 의무를 명확히 하기 위한 필수 문서입니다. 근로기준법 제17조에 따라 작성되어야 합니다.",
                "source": "실무 가이드",
                "relevance_score": 0.72,
                "metadata": {
                    "document_type": "가이드",
                    "category": "노동법",
                    "publisher": "고용노동부"
                }
            }
        ]
        
        # 쿼리 키워드에 따라 관련성 점수 조정 (간단한 키워드 매칭)
        query_lower = query.lower()
        for doc in mock_documents:
            if any(keyword in doc["title"].lower() or keyword in doc["content"].lower() 
                   for keyword in query_lower.split()):
                doc["relevance_score"] = min(doc["relevance_score"] + 0.05, 1.0)
        
        # 관련성 점수로 정렬 후 top_k 반환
        sorted_docs = sorted(mock_documents, key=lambda x: x["relevance_score"], reverse=True)
        return sorted_docs[:top_k]
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        검색 결과를 에이전트가 읽기 쉬운 형태로 포맷팅
        
        Args:
            results: 검색 결과 리스트
            
        Returns:
            str: 포맷팅된 결과 문자열
        """
        if not results:
            return "검색 결과가 없습니다."
        
        formatted = f"총 {len(results)}개의 관련 문서를 찾았습니다:\n\n"
        
        for idx, doc in enumerate(results, 1):
            formatted += f"[문서 {idx}] {doc['title']}\n"
            formatted += f"출처: {doc['source']}\n"
            formatted += f"관련성: {doc['relevance_score']:.2%}\n"
            formatted += f"내용: {doc['content'][:200]}...\n"
            
            if doc.get("metadata"):
                formatted += f"메타데이터: {doc['metadata']}\n"
            
            formatted += "\n" + "-" * 80 + "\n\n"
        
        return formatted


# 에이전트에서 사용할 도구 인스턴스 생성 함수
def get_azure_search_tool() -> AzureSearchTool:
    """
    Azure AI Search 도구 인스턴스 반환
    
    Returns:
        AzureSearchTool: 설정된 검색 도구
    """
    # TODO: 환경변수나 config에서 실제 값 로드
    # from config.settings import get_config
    # config = get_config()
    # endpoint = config.get("azure-search-endpoint")
    # key = config.get("azure-search-key")
    
    return AzureSearchTool(
        search_endpoint=None,  # 추후 설정
        search_key=None,  # 추후 설정
        index_name="legal-documents"
    )
