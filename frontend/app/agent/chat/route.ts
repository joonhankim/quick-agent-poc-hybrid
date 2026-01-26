type AssistantMessage = {
  id?: string;
  role: string;
  content?:
    | string
    | Array<
        | { type: 'text'; text: string }
        | { type: 'input_text'; content?: { text?: string } }
        | Record<string, unknown>
      >;
  parts?: Array<
    | { type: 'text'; text: string }
    | Record<string, unknown>
  >;
  metadata?: Record<string, unknown>;
};

const coerceContentToString = (content: AssistantMessage['content']): string => {
  // 문자열인 경우 그대로 반환
  if (typeof content === 'string') {
    return content;
  }

  // null이나 undefined인 경우 빈 문자열 반환
  if (content == null) {
    return '';
  }

  // 배열이 아닌 경우 빈 문자열 반환
  if (!Array.isArray(content)) {
    // 객체인 경우 JSON.stringify로 변환 시도 (디버깅용)
    if (typeof content === 'object') {
      console.warn('Unexpected content format (object):', content);
    }
    return '';
  }

  // 빈 배열인 경우 빈 문자열 반환
  if (content.length === 0) {
    return '';
  }

  // 배열의 각 블록을 처리
  return content
    .map((block) => {
      if (block == null) {
        return '';
      }

      // 블록이 문자열인 경우
      if (typeof block === 'string') {
        return block;
      }

      // 블록이 객체인 경우
      if (typeof block === 'object') {
        // type: 'text' 형식
        if ('type' in block && block.type === 'text' && 'text' in block) {
          const textValue = block.text;
          return typeof textValue === 'string' ? textValue : '';
        }

        // type: 'input_text' 형식
        if (
          'type' in block &&
          block.type === 'input_text' &&
          'content' in block &&
          block.content &&
          typeof block.content === 'object' &&
          'text' in block.content
        ) {
          const textValue = (block.content as { text?: unknown }).text;
          return typeof textValue === 'string' ? textValue : '';
        }

        // 다른 형식의 객체인 경우 (디버깅용)
        console.warn('Unexpected block format:', block);
      }

      return '';
    })
    .filter((chunk) => chunk.length > 0)
    .join('\n');
};

// Chat ID 생성 및 관리
let chatId: string | null = null;

export async function POST(req: Request) {
  console.log('[ROUTE] ===== /agent/chat API 호출됨 =====');
  try {
    const body = await req.json();
    console.log('[ROUTE] 1. 받은 body:', JSON.stringify(body, null, 2));

    const { messages = [] } = body as {
      messages?: AssistantMessage[];
    };
    console.log('[ROUTE] 2. 추출한 전체 messages 수:', messages.length);

    // 최신 메시지만 추출 (마지막 user 메시지)
    const lastMessage = messages[messages.length - 1];

    if (!lastMessage) {
      return new Response(
        JSON.stringify({ error: '메시지가 없습니다.' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Chat ID가 없으면 생성
    if (!chatId) {
      chatId = `chat-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      console.log('[ROUTE] 새 채팅 생성:', chatId);
    }

    // 최신 메시지 정규화
    const contentSource = lastMessage.parts || lastMessage.content;
    const content = coerceContentToString(contentSource);

    console.log('[ROUTE] 3. 전송할 최신 메시지:', {
      chat_id: chatId,
      role: lastMessage.role,
      content: content.substring(0, 100) + (content.length > 100 ? '...' : '')
    });

    // chat_id와 최신 메시지만 전송
    console.log('[ROUTE] 4. 백엔드 호출 시작:', {
      url: 'http://localhost:8000/agent/chat',
      chat_id: chatId,
      user_query: content.substring(0, 50)
    });

    const backendResponse = await fetch('http://localhost:8000/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Chat-Id': chatId,
      },
      body: JSON.stringify({
        chat_id: chatId,
        user_query: content,
        user_no: 'test-user-001',
        room_id: 'test-room-001',
        exe_date: new Date().toISOString(),
      }),
    });

    console.log('[ROUTE] 5. 백엔드 응답 받음:', {
      status: backendResponse.status,
      ok: backendResponse.ok,
      headers: Object.fromEntries(backendResponse.headers.entries())
    });

    if (!backendResponse.ok) {
      const detail = await backendResponse.text().catch(() => '');
      return new Response(
        JSON.stringify({ error: 'Backend API 호출 실패', detail }),
        {
          status: backendResponse.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // 백엔드 응답을 그대로 프록시 (변환 없이)
    console.log('[ROUTE] 6. 백엔드 응답을 그대로 전달');

    return new Response(backendResponse.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Chat API Error:', error);
    return new Response(
      JSON.stringify({ error: '서버 오류가 발생했습니다.' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}