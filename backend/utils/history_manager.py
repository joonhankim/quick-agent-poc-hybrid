# coding: utf-8
"""
PostgreSQL 대화 히스토리 매니저

서비스 레벨의 대화 내역 저장 및 조회를 담당합니다.
Agent의 CosmosDB와는 별개로 운영됩니다.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import asyncpg
from contextlib import asynccontextmanager


class PostgreSQLHistoryManager:
    """PostgreSQL을 사용한 대화 히스토리 매니저"""

    def __init__(self, connection_pool: asyncpg.Pool):
        """
        Args:
            connection_pool: asyncpg connection pool
        """
        self.pool = connection_pool

    @asynccontextmanager
    async def _get_connection(self):
        """Connection pool에서 연결 가져오기"""
        async with self.pool.acquire() as connection:
            yield connection

    async def save_message(
        self,
        room_id: str,
        user_no: str,
        chat_id: str,
        user_query: str,
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        대화 메시지를 PostgreSQL에 저장

        Args:
            room_id: 대화방 ID
            user_no: 사용자 번호
            chat_id: 채팅 세션 ID
            user_query: 사용자 질문
            ai_response: AI 응답
            metadata: 추가 메타데이터 (JSON)

        Returns:
            저장된 메시지의 ID
        """
        query = """
        INSERT INTO chat_messages (
            room_id, user_no, chat_id, user_query, ai_response, metadata, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """

        async with self._get_connection() as conn:
            message_id = await conn.fetchval(
                query,
                room_id,
                user_no,
                chat_id,
                user_query,
                ai_response,
                metadata,
                datetime.now(timezone.utc),
            )
            return message_id

    async def get_room_history(
        self,
        room_id: str,
        user_no: str,
        limit: Optional[int] = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        특정 대화방의 히스토리 조회

        Args:
            room_id: 대화방 ID
            user_no: 사용자 번호
            limit: 조회할 메시지 수 (None이면 전체)
            offset: 시작 위치

        Returns:
            메시지 리스트 (최신순)
        """
        if limit is None:
            query = """
            SELECT id, room_id, user_no, chat_id, user_query, ai_response,
                   metadata, created_at
            FROM chat_messages
            WHERE room_id = $1 AND user_no = $2
            ORDER BY created_at DESC
            OFFSET $3
            """
            params = (room_id, user_no, offset)
        else:
            query = """
            SELECT id, room_id, user_no, chat_id, user_query, ai_response,
                   metadata, created_at
            FROM chat_messages
            WHERE room_id = $1 AND user_no = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            """
            params = (room_id, user_no, limit, offset)

        async with self._get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_user_rooms(
        self,
        user_no: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        사용자의 대화방 목록 조회 (최근 메시지 기준)

        Args:
            user_no: 사용자 번호
            limit: 조회할 대화방 수

        Returns:
            대화방 정보 리스트 (최신순)
        """
        query = """
        SELECT DISTINCT ON (room_id)
            room_id,
            MAX(created_at) as last_message_at,
            COUNT(*) as message_count
        FROM chat_messages
        WHERE user_no = $1
        GROUP BY room_id
        ORDER BY last_message_at DESC
        LIMIT $2
        """

        async with self._get_connection() as conn:
            rows = await conn.fetch(query, user_no, limit)
            return [dict(row) for row in rows]


    async def get_chat_list_at_room(self, room_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        대화방(room_id)내 채팅 목록 조회

        Args:
            room_id: 대화방 ID
            limit: 조회할 채팅 수(None이면 전체)

        Returns:
            채팅 목록 (최신순)
        """
        query = """
        SELECT id, room_id, user_no, chat_id, user_query, output,
               metadata, created_at
        FROM chat_messages
        WHERE room_id = $1
        GROUP BY chat_id
        ORDER BY created_at DESC
        """
        if limit is None:
            query += " LIMIT ALL"
        else:
            query += " LIMIT $2"

        async with self._get_connection() as conn:
            rows = await conn.fetch(query, room_id, limit)
            return [dict(row) for row in rows]

    async def delete_room(self, room_id: str, user_no: str) -> int:
        """
        대화방 삭제 (해당 대화방의 모든 메시지 삭제)

        Args:
            room_id: 대화방 ID
            user_no: 사용자 번호

        Returns:
            삭제된 메시지 수
        """
        query = """
        DELETE FROM chat_messages
        WHERE room_id = $1 AND user_no = $2
        """

        async with self._get_connection() as conn:
            result = await conn.execute(query, room_id, user_no)
            # 'DELETE 5' 형식의 결과에서 숫자 추출
            return int(result.split()[-1])

    async def get_message_count(self, room_id: str, user_no: str) -> int:
        """
        대화방의 메시지 개수 조회

        Args:
            room_id: 대화방 ID
            user_no: 사용자 번호

        Returns:
            메시지 개수
        """
        query = """
        SELECT COUNT(*) as count
        FROM chat_messages
        WHERE room_id = $1 AND user_no = $2
        """

        async with self._get_connection() as conn:
            count = await conn.fetchval(query, room_id, user_no)
            return count or 0
