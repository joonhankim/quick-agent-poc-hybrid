"""
Vercel AI SDK UI Message Stream 호환 SSE 포맷터

프론트엔드(@assistant-ui/react + ai SDK)가 기대하는
uiMessageChunkSchema에 맞춰 SSE 메시지를 생성합니다.

지원 chunk 타입:
  - start / finish          : 메시지 라이프사이클
  - text-start / text-delta / text-end : 텍스트 스트리밍
  - data-status             : 진행 상태 표시 (커스텀 data-* 확장)
  - error                   : 에러
"""
import json


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


# ── 메시지 라이프사이클 ──────────────────────────────────────────────
def sse_start(message_id: str | None = None) -> str:
    chunk: dict = {"type": "start"}
    if message_id:
        chunk["messageId"] = message_id
    return _sse(chunk)


def sse_finish() -> str:
    return _sse({"type": "finish"})


# ── 텍스트 스트리밍 ──────────────────────────────────────────────────
def sse_text_start(part_id: str) -> str:
    return _sse({"type": "text-start", "id": part_id})


def sse_text_delta(part_id: str, delta: str) -> str:
    return _sse({"type": "text-delta", "id": part_id, "delta": delta})


def sse_text_end(part_id: str) -> str:
    return _sse({"type": "text-end", "id": part_id})


# ── 진행 상태 (message-metadata) ─────────────────────────────────────
def sse_status(message: str) -> str:
    """
    message.metadata.status를 업데이트하여 프론트엔드에서 진행 상태를 표시합니다.
    매번 호출 시 기존 status 값을 덮어씁니다.
    """
    return _sse({
        "type": "message-metadata",
        "messageMetadata": {"status": message},
    })


# ── 에러 ─────────────────────────────────────────────────────────────
def sse_error(error_text: str) -> str:
    return _sse({"type": "error", "errorText": error_text})


# ── 하위 호환용 (기존 create_sse_message 래퍼) ───────────────────────
def create_sse_message(type: str, content) -> str:
    """
    기존 코드와의 하위 호환을 위한 래퍼.
    새 코드에서는 위의 개별 함수를 직접 사용하세요.
    """
    if type == "status":
        return sse_status(content if isinstance(content, str) else str(content))
    elif type == "error":
        return sse_error(content if isinstance(content, str) else str(content))
    else:
        # 하위 호환: 알 수 없는 타입은 message-metadata로 래핑
        return _sse({"type": "message-metadata", "messageMetadata": {type: content}})
