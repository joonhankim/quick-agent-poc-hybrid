import json


def create_sse_message(type: str, content) -> str:
    """
    커스텀 SSE 형식의 데이터를 생성합니다.
    일관된 JSON 구조로 타입별 메시지를 구분합니다.

    Args:
        type: 메시지 타입
            - "start": 작업 시작 메시지
            - "status": 중간 진행 상태 메시지 ('검색중', '작업 진행중' 등)
            - "content": 응답 텍스트 청크 (스트리밍)
            - "complete": 최종 완료 메시지 (문자열 또는 {"message": "...", "metadata": {...}})
            - "error": 에러 메시지
            - "heartbeat": 연결 확인 메시지
        content: 메시지 내용 (str 또는 dict)

    Returns:
        str: SSE 형식의 메시지 문자열

    Example:
        >>> create_sse_message("status", "검색중...")
        'data: {"type": "status", "content": "검색중..."}\n\n'

        >>> create_sse_message("complete", {"message": "안녕하세요", "metadata": {}})
        'data: {"type": "complete", "content": {"message": "안녕하세요", "metadata": {}}}\n\n'
    """

    # 메시지 구조: 항상 {"type": "...", "content": ...} 형태로 통일
    message = {
        "type": type,
        "content": content
    }

    # JSON 직렬화 (한글 유니코드 이스케이프 방지)
    json_str = json.dumps(message, ensure_ascii=False)

    # SSE 형식으로 반환
    return f"data: {json_str}\n\n"
