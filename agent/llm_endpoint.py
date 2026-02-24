from langchain_openai import AzureChatOpenAI
from config.settings import get_config
from api.core.logger import APILogger

logger = APILogger()

# reasoning 모델 접두사 (temperature 미지원)
_REASONING_PREFIXES = ("gpt-5", "o1", "o3")


def get_langchain_llm(model_name: str = "gpt-4o") -> AzureChatOpenAI:
    """
    LangChain 호환 LLM 인스턴스 반환
    - streaming=True 기본 활성화
    - reasoning 모델(gpt-5.x, o1, o3 등) 감지 시 temperature 생략
    """
    config = get_config()

    config_prefix = "AGENT"
    if model_name.lower() == "gpt-4o":
        config_prefix = "GPT4O"

    is_reasoning = any(model_name.lower().startswith(p) for p in _REASONING_PREFIXES)

    kwargs = dict(
        azure_deployment=config.get(f"{config_prefix}_AZURE_OPENAI_DEPLOYMENT_NAME") or model_name,
        api_version=config.get(f"{config_prefix}_AZURE_OPENAI_API_VERSION"),
        azure_endpoint=config.get(f"{config_prefix}_AZURE_OPENAI_ENDPOINT"),
        api_key=config.get(f"{config_prefix}_AZURE_OPENAI_API_KEY"),
        streaming=True,
    )

    if not is_reasoning:
        kwargs["temperature"] = 0.7

    logger.info(f">>>> Load LangChain LLM: {model_name} (prefix={config_prefix}, reasoning={is_reasoning})")
    return AzureChatOpenAI(**kwargs)


def generate_error_message(error_type: str, error_string: str, llm: AzureChatOpenAI) -> str:
    """에러 메시지를 사용자 친화적으로 생성 (노드 레벨에서 호출)"""
    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = """당신은 보험 상담 AI 어시스턴트입니다.
현재 고객의 질문을 처리하는 중 기술적인 문제가 발생했습니다.
고객에게 상황을 정중하고 친절하게 설명하고, 적절한 대안을 제시해야 합니다.

**톤앤매너:**
- 정중하고 친절한 어조
- 사과의 표현 포함 (과도하지 않게)
- 긍정적이고 해결 지향적
- 2-3문장으로 간결하게

**피해야 할 표현:**
- 기술 용어 (API, 400 error, content filter 등)
- 시스템 내부 동작 설명
"""

    user_message = f"""
**발생한 에러:**
{error_string}

**에러 타입:**
{error_type}

위 정보를 바탕으로, 고객에게 보낼 친절하고 정중한 안내 문구를 2-3문장으로 작성해주세요.
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = llm.invoke(messages)
    return response.content.strip()
