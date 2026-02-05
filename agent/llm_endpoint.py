from typing import Callable
from functools import wraps
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from crewai import LLM
import litellm
from config.settings import get_config
from api.core.logger import APILogger

# GPT-5.1 지원을 위한 litellm 전역 설정
litellm.drop_params = True

logger = APILogger()


class LLMInvokeException(Exception):
    """LLM 호출 중 발생하는 예외"""
    def __init__(self, message: str, error_type: str = None, original_error: Exception = None,
                 user_query: str = None, error_code: int = None, additional_info: dict = None):
        self.message = message
        self.error_type = error_type
        self.original_error = original_error
        self.user_query = user_query
        self.error_code = error_code
        self.additional_info = additional_info or {}
        super().__init__(self.message)


class SafeLLMWrapper:
    """
    LLM을 감싸서 자동으로 에러 처리하는 Wrapper
    모든 메서드를 자동으로 래핑
    """
    
    # 래핑이 필요한 메서드들 (invoke 계열)
    WRAPPED_METHODS = {'invoke', 'ainvoke', 'stream', 'astream', 'batch', 'abatch'}
    
    # 특수 처리가 필요한 메서드들 (래핑된 객체 반환)
    CHAIN_METHODS = {
        'with_structured_output',
        'with_retry',
        'with_fallbacks',
        'bind',
        'bind_tools',
        'with_config',
        'with_listeners'
    }
    
    def __init__(self, model_name: str):
        """
        Args:
            model_name: 사용할 모델명
        """
        config = get_config()
        
        # Ensure model name has 'azure/' prefix for CrewAI compatibility
        azure_model = model_name
        if not azure_model.startswith("azure/"):
            azure_model = f"azure/{azure_model}"

        # Determine which config to use
        config_prefix = "AGENT"
        if model_name.lower() == "gpt-4o":
            config_prefix = "GPT4O"
            
        self._llm = LLM(
            model=azure_model,
            base_url=config.get(f"{config_prefix}_AZURE_OPENAI_ENDPOINT"),
            api_key=config.get(f"{config_prefix}_AZURE_OPENAI_API_KEY"),
            api_version=config.get(f"{config_prefix}_AZURE_OPENAI_API_VERSION"),
            extra_kwargs={
                "drop_params": True,
                "additional_drop_params": ["stop", "temperature", "top_p"]
            },
        )
        logger.info(f">>>> Load Model Name : {azure_model} (using {config_prefix} config)")
        self._model_name = model_name
        
        # 위 self._llm은 'with_structured_output'등 적용으로 변경될 수 있어, 에러메세지 생성용 초기 LLM 보관
        self._base_llm = self._llm
    
    def _wrap_invoke_method(self, method: Callable) -> Callable:
        """
        invoke 계열 메서드를 에러 처리로 래핑
        
        Args:
            method: 원본 메서드
        
        Returns:
            래핑된 메서드
        """
        @wraps(method)
        def sync_wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                logger.error(f">>> {method.__name__} 실행 에러: {e}")
                user_query = self._extract_user_query(args, kwargs)
                self._handle_bad_request(e, user_query)
        
        @wraps(method)
        async def async_wrapper(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except Exception as e:
                logger.error(f">>> {method.__name__} 실행 에러: {e}")
                user_query = self._extract_user_query(args, kwargs)
                self._handle_bad_request(e, user_query)
        
        # async 메서드인지 확인
        import inspect
        if inspect.iscoroutinefunction(method):
            return async_wrapper
        else:
            return sync_wrapper
    
    def _wrap_chain_method(self, method: Callable) -> Callable:
        """
        체이닝 메서드를 래핑 (SafeLLMWrapper 반환)
        
        Args:
            method: 원본 메서드
        
        Returns:
            래핑된 메서드
        """
        @wraps(method)
        def wrapper(*args, **kwargs):
            # 원본 메서드 호출
            result = method(*args, **kwargs)
            
            # 결과를 SafeLLMWrapper로 래핑
            wrapped = SafeLLMWrapper.__new__(SafeLLMWrapper)
            wrapped._llm = result  # 변환된 LLM 저장
            wrapped._model_name = self._model_name
            wrapped._base_llm = self._base_llm
            
            return wrapped
        
        return wrapper
    
    def __getattr__(self, name: str):
        """
        동적으로 메서드 접근 처리
        
        Args:
            name: 속성/메서드 이름
        
        Returns:
            래핑된 메서드 또는 속성
        """
        # 원본 LLM에서 속성/메서드 가져오기
        attr = getattr(self._llm, name)
        
        # 호출 가능한지 확인
        if not callable(attr):
            # 일반 속성은 그대로 반환
            return attr
        
        # invoke 계열 메서드 → 에러 처리 래핑
        if name in self.WRAPPED_METHODS:
            return self._wrap_invoke_method(attr)
        
        # 체이닝 메서드 → SafeLLMWrapper 반환하도록 래핑
        elif name in self.CHAIN_METHODS:
            return self._wrap_chain_method(attr)
        
        # 기타 메서드는 그대로 반환
        else:
            return attr
    
    def _extract_user_query(self, args: tuple, kwargs: dict) -> str:
        """args/kwargs에서 사용자 질문 추출"""
        try:
            # messages 인자 찾기
            messages = None
            if args and len(args) > 0:
                messages = args[0]
            elif 'messages' in kwargs:
                messages = kwargs['messages']
            elif 'input' in kwargs:
                messages = kwargs['input']
            
            if messages and isinstance(messages, list):
                # 뒤에서부터 HumanMessage 찾기
                for msg in reversed(messages):
                    if isinstance(msg, HumanMessage):
                        return msg.content
        except Exception as e:
            logger.debug(f"Failed to extract user query: {e}")
        
        return "(질문 내용을 확인할 수 없습니다)"
    
    def _handle_bad_request(self, error: Exception, user_query: str):
        """Invoke Error 처리"""
        import traceback

        error_str = str(error)
        error_type = type(error).__name__
        error_code = getattr(error, "status_code", None)

        # 상세 에러 정보 로깅
        logger.error(f"=== LLM Invoke Error 상세 정보 ===")
        logger.error(f"Error Type: {error_type}")
        logger.error(f"Error Message: {error_str}")
        logger.error(f"Error Code: {error_code}")
        logger.error(f"Error Body: {getattr(error, 'body', None)}")
        logger.error(f"Error Response: {getattr(error, 'response', None)}")
        logger.error(f"Error Cause: {error.__cause__}")
        logger.error(f"Error Context: {error.__context__}")
        logger.error(f"Full Traceback:\n{traceback.format_exc()}")
        logger.error(f"================================")

        try:
            generate_message = self.generate_error_message(error_type, error_str)
        except Exception as gen_error: 
            logger.error(f">>> Error generating friendly message: {gen_error}")
            generate_message = "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

        raise LLMInvokeException(
            message=generate_message,
            error_type=error_type,
            original_error=error,
            user_query=user_query,
            error_code=error_code,
            additional_info={"model": self._model_name},
        )
    
    def generate_error_message(self, error_type: str, error_string: str) -> str:
        """에러 메시지를 사용자 친화적으로 생성"""
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
            HumanMessage(content=user_message)
        ]
        # 변경 가능성이 존재하는 LLM(with_structured_output 등 적용 가능성)이 아닌 최초 LLM 사용
        response = self._base_llm.invoke(messages)
        return response.content.strip()


def get_safe_llm(model_name: str = "gpt-4o") -> SafeLLMWrapper:
    """안전한 LLM 인스턴스 반환"""
    return SafeLLMWrapper(model_name=model_name)