export async function POST(req: Request) {
  try {
    const body = await req.json();
    console.log('[ROUTE] 받은 body:', JSON.stringify(body, null, 2));

    // 프론트엔드에서 보낸 QueryRequest 형식을 그대로 백엔드로 전달
    const { user_query, user_no, room_id, chat_id, exe_date } = body as {
      user_query: string;
      user_no: string;
      room_id: string;
      chat_id: string;
      exe_date?: string;
    };

    const backendPayload = {
      user_query,
      user_no,
      room_id,
      chat_id,
      exe_date: exe_date || new Date().toISOString(),
    };

    console.log('[ROUTE] 백엔드로 전송:', JSON.stringify(backendPayload, null, 2));

    const backendResponse = await fetch('http://localhost:8000/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendPayload),
    });

    if (!backendResponse.ok) {
      const detail = await backendResponse.text().catch(() => '');
      console.error('[ROUTE] 백엔드 에러:', backendResponse.status, detail);
      return new Response(
        JSON.stringify({ error: 'Backend API 호출 실패', detail }),
        {
          status: backendResponse.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // SSE 스트림을 그대로 프록시
    return new Response(backendResponse.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
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
