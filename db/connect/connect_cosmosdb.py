import os
import socket
from urllib.parse import urlparse
from azure.cosmos import CosmosClient, PartitionKey
from api.core.logger import APILogger

logger = APILogger()


class CosmosDBClient:

    def __init__(self, endpoint: str = None, key: str = None):
        # main.py에서 이미 환경변수가 로드되었으므로 os.getenv() 사용
        self.endpoint = endpoint or os.getenv("agent-cosmos-endpoint")
        self.key = key or os.getenv("agent-cosmos-key")

        if not (self.endpoint and self.key):
            raise ValueError(
                "CosmosDB 엔드포인트와 키가 필요합니다. 환경변수 agent-cosmos-endpoint와 agent-cosmos-key를 설정하거나 직접 전달하세요."
            )

        # CosmosClient 생성
        self.client = CosmosClient(self.endpoint, credential=self.key)

    def get_container(
        self, database_name: str, container_name: str, partition_key_path: str
    ):
        database = self.client.create_database_if_not_exists(id=database_name)
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path=partition_key_path),
        )
        return container
