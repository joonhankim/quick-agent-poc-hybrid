from db.connect.connect_cosmosdb import CosmosDBClient
from api.core.logger import APILogger

# Lazy initialization - 실제 사용 시점에 초기화
_cosmos_db_client = None
_prompt_container = None
_chat_history_container = None
_session_container = None
_customer_info_container = None
logger = APILogger()


def _init_cosmos_client():
    """CosmosDB 클라이언트를 초기화합니다."""
    global _cosmos_db_client
    if _cosmos_db_client is None:
        _cosmos_db_client = CosmosDBClient()
    return _cosmos_db_client


# Property-like access for backward compatibility
class _LazyContainer:
    def __init__(self, db_name, container_name, partition_key):
        self.db_name = db_name
        self.container_name = container_name
        self.partition_key = partition_key
        self._container = None
        self._is_connected = False
        self._info_fail_connection = None

    def __getattr__(self, name):
        """
        Container의 메서드나 속성에 처음 접근할 때 연결 및 초기화
        예: chat_history_container.create_item() 호출 시 이 메서드가 실행됨
        """
        if self._container is None:
            try:
                logger.info(f"CosmosDB 연결 시작: {self.db_name}/{self.container_name}")
                client = _init_cosmos_client()
                # get_container 내부에서 create_database_if_not_exists와
                # create_container_if_not_exists를 호출하므로 자동으로 생성됨
                self._container = client.get_container(
                    database_name=self.db_name,
                    container_name=self.container_name,
                    partition_key_path=self.partition_key,
                )
                self._is_connected = True
                self._info_fail_connection = None
                logger.info(f"CosmosDB 연결 완료: {self.db_name}/{self.container_name}")
            except Exception as e:
                # 방화벽 에러인 경우 특별 처리
                error_str = str(e)
                if "firewall" in error_str.lower() or "forbidden" in error_str.lower():
                    # IP 주소 추출
                    import re
                    ip_match = re.search(r'IP (\d+\.\d+\.\d+\.\d+)', error_str)
                    current_ip = ip_match.group(1) if ip_match else "알 수 없음"

                    logger.error("=" * 80)
                    logger.error(">>> CosmosDB 방화벽 차단 에러")
                    logger.error(f">>> 현재 IP 주소: {current_ip}")
                    logger.error("=" * 80)

                # 로깅 후 재발생 - 이렇게 하면 첫 API 호출 시 명확한 에러 메시지
                logger.error(
                    f"CosmosDB 컨테이너 초기화 실패 ({self.container_name}): {e}"
                )
                self._is_connected = False
                self._info_fail_connection = e
                raise
        return getattr(self._container, name)

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected and self._container is not None

    def get_info_fail_connection(self):
        """연결 실패 정보 반환"""
        if self._info_fail_connection is None:
            return "연결을 시도하지 않았습니다."
        return str(self._info_fail_connection)


# 기존 코드와의 호환성 유지
cosmos_db_client = None  # 직접 접근 시 초기화 필요

chat_history_container = _LazyContainer(
    db_name="conversation_history_db",
    container_name="conversation_history",
    partition_key="/chat_id",
)


def verify_cosmosdb_connection():
    """
    CosmosDB 연결을 실제로 시도하고 결과를 로깅
    모듈 import 시점이 아닌 애플리케이션 시작 시점에 호출해야 함
    """
    try:
        # 연결을 실제로 시도하기 위해 임시로 속성에 접근
        # 이렇게 하면 __getattr__가 호출되어 연결이 시도됨
        if chat_history_container.is_connected():
            logger.info(">>> CosmosDB 연결 성공 (이미 연결됨)")
            return True
        else:
            # 아직 연결되지 않았으면 강제로 연결 시도
            try:
                logger.info(">>> CosmosDB 연결 시도 중...")
                # 임의 속성 접근으로 연결 트리거 (__getattr__ 호출)
                _ = chat_history_container.id
                if chat_history_container.is_connected():
                    logger.info(">>> ✅ CosmosDB 연결 성공!")
                    return True
                else:
                    error_info = chat_history_container.get_info_fail_connection()
                    logger.error(f">>> ❌ CosmosDB 연결 실패: {error_info}")
                    return False
            except Exception as e:
                error_info = chat_history_container.get_info_fail_connection()
                # 방화벽 에러는 이미 __getattr__에서 상세 로그가 출력됨
                if "firewall" not in str(e).lower() and "forbidden" not in str(e).lower():
                    logger.error(f">>> ❌ CosmosDB 연결 실패: {error_info}")
                    logger.error(f">>> 예외 상세: {type(e).__name__}: {e}")
                return False
    except Exception as e:
        error_info = chat_history_container.get_info_fail_connection()
        if "firewall" not in str(e).lower() and "forbidden" not in str(e).lower():
            logger.error(f">>> ❌ CosmosDB 연결 실패: {error_info}")
            logger.error(f">>> 예외 상세: {type(e).__name__}: {e}")
        return False
