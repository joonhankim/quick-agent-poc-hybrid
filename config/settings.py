import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from api.core.logger import APILogger

logger = APILogger()


class ConfigManager:
    """
    환경별 설정 관리자 (싱글톤 패턴)

    APP_ENV 환경변수에 따라 설정 소스를 결정합니다:
    - local: .env 파일에서 환경변수 로드
    - development: Azure Key Vault에서만 환경변수 로드
    - production: Azure Key Vault에서만 환경변수 로드

    서버 시작 시 한 번만 설정을 로드하며, 이후에는 메모리에 캐시된 값을 사용합니다.
    """

    def __init__(self, env: str = "local"):
        self.env = env
        self.config: Dict[str, Any] = {}

        # 필요한 환경 변수 목록
        self.required_keys = [
            "AGENT_AZURE_OPENAI_API_KEY",
            "AGENT_AZURE_OPENAI_ENDPOINT",
            "AGENT_AZURE_OPENAI_API_VERSION",
            "AGENT_AZURE_OPENAI_MODEL_NAME",
            "GPT4O_AZURE_OPENAI_API_KEY",
            "GPT4O_AZURE_OPENAI_ENDPOINT",
            "GPT4O_AZURE_OPENAI_API_VERSION",
            "GPT4O_AZURE_OPENAI_MODEL_NAME",
        ]

        self._load_config()

    def _load_config(self):
        """환경에 따른 설정 로드"""
        logger.info(f"현재 환경: {self.env} zone")

        if self.env in ["development", "production"]:
            # development, production: Azure Key Vault 사용
            self._load_from_key_vault()
        else:
            # local 또는 기타: .env 파일 사용
            if self.env != "local":
                logger.warning(
                    f"알 수 없는 환경 '{self.env}' - 로컬 환경으로 처리합니다."
                )
            self._load_from_env_file()

    def _load_from_env_file(self):
        """로컬 환경: .env 파일에서 환경변수 로드"""
        env_file = ".env"

        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            logger.info(f".env 파일 로드: {env_file}")
        else:
            logger.warning(f".env 파일이 존재하지 않습니다: {env_file}")

        # 환경 변수 로드
        loaded_keys = []
        missing_keys = []

        for key in self.required_keys:
            value = os.getenv(key)
            if value:
                self.config[key] = value
                loaded_keys.append(key)
            else:
                missing_keys.append(key)

        logger.info(
            f".env 파일 환경변수 로드 완료 - "
            f"성공: {len(loaded_keys)}/{len(self.required_keys)}"
        )
        if missing_keys:
            logger.warning(f"설정되지 않은 키: {', '.join(missing_keys)}")

    def _load_from_key_vault(self):
        """Container Apps에서 환경변수 로드

        Container Apps의 Key Vault 참조 기능을 사용하므로
        환경변수는 이미 Container Apps 플랫폼에 의해 설정되어 있음.
        따라서 단순히 환경변수 존재 여부만 확인.
        """
        logger.info("Container Apps 환경 - Key Vault 참조를 통한 환경변수 확인")

        # .env 파일 로드 (로컬 테스트용)
        if os.path.exists(".env"):
            load_dotenv()
            logger.info(".env 파일 로드 완료")

        # Container Apps는 Key Vault 참조를 통해 환경변수가 이미 설정됨
        # 따라서 환경변수 존재 여부만 확인
        logger.info("환경변수 확인 중...")

        loaded_count = 0
        missing_keys = []

        for key in self.required_keys:
            value = os.getenv(key)
            if value:
                self.config[key] = value
                loaded_count += 1
                # 값의 일부만 마스킹하여 로깅
                if len(value) > 8:
                    masked = value[:4] + "***" + value[-4:]
                else:
                    masked = "***"
                logger.info(f"✓ {key}: {masked}")
            else:
                missing_keys.append(key)
                logger.warning(f"✗ {key}: 환경변수가 설정되지 않음")

        # 로드 결과 요약
        logger.info("=" * 50)
        logger.info(
            f"환경변수 로드 결과 - " f"성공: {loaded_count}/{len(self.required_keys)}"
        )

        if missing_keys:
            logger.warning(f"누락된 환경변수 {len(missing_keys)}개:")
            for key in missing_keys:
                logger.warning(f"  - {key}")

            # Container Apps에서 Key Vault 참조가 제대로 설정되었는지 확인 메시지
            logger.info("Container Apps의 Key Vault 참조 설정을 확인하세요.")
            logger.info("필요한 경우 az containerapp secret set 명령을 사용하세요.")

        logger.info("=" * 50)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        설정 값 가져오기

        Args:
            key: 환경변수 키
            default: 환경변수가 없을 경우 반환할 기본값

        Returns:
            Optional[str]: 환경변수 값
        """
        return self.config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """모든 설정 값 가져오기"""
        return self.config.copy()


# 싱글톤 인스턴스
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """설정 관리자 인스턴스 가져오기"""
    global _config_manager
    if _config_manager is None:
        env = os.getenv("APP_ENV", "local")
        _config_manager = ConfigManager(env=env)
    return _config_manager
