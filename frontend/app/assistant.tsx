"use client";

import { useState, useRef, useEffect } from "react";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  Sidebar,
  SidebarContent,
  SidebarHeader,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { ArrowUpIcon, MessagesSquare, PlusIcon, Trash2Icon, Sparkles, Lightbulb, Code, User, Copy, RotateCcw, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Chat {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

// 테스트용 상수 (실제 운영에서는 인증 시스템에서 가져와야 함)
const TEST_USER_NO = "test-user-001";
const TEST_ROOM_ID = "test-room-001";

// HD현대 공식 로고 컴포넌트
const HDHyundaiLogo = ({ className = "w-full h-full" }: { className?: string }) => (
  <svg viewBox="0 0 581 253" className={className} xmlns="http://www.w3.org/2000/svg">
    {/* Forward Mark - 녹색 화살표 심볼 */}
    <g id="forward-mark-bright">
      <path fill="#02e400" opacity="1.00" d=" M 2.68 4.22 C 49.98 4.14 97.30 4.08 144.60 4.25 C 166.68 42.56 188.79 80.86 210.73 119.25 C 212.35 121.77 214.29 124.13 215.18 127.05 L 214.44 126.61 C 144.09 85.94 73.83 45.10 3.37 4.63 L 2.68 4.22 Z" />
    </g>
    <g id="forward-mark-medium">
      <path fill="#00ad1d" opacity="1.00" d=" M 3.37 4.63 C 73.83 45.10 144.09 85.94 214.44 126.61 C 213.13 129.78 211.53 132.83 209.73 135.75 C 189.44 170.81 169.24 205.92 148.98 241.00 C 147.43 243.53 146.52 246.45 144.64 248.77 C 144.24 248.81 143.45 248.88 143.05 248.91 C 134.89 235.65 127.46 221.93 119.47 208.56 C 108.38 189.02 96.96 169.69 85.80 150.19 C 81.51 142.76 76.90 135.48 73.18 127.75 C 71.92 124.27 69.97 121.13 68.10 117.96 C 55.41 95.65 42.73 73.35 29.91 51.12 C 21.03 35.65 11.90 20.29 3.37 4.63 Z" />
    </g>
    <g id="hd-text">
      <path fill="#012f87" opacity="1.00" d=" M 274.15 47.15 C 286.38 47.17 298.62 47.16 310.85 47.15 C 310.89 67.46 310.71 87.76 310.93 108.07 C 327.49 108.35 344.07 107.99 360.63 108.23 C 364.05 115.90 368.70 122.94 372.57 130.38 C 373.55 132.44 374.43 134.59 375.96 136.32 C 376.42 106.61 376.05 76.87 376.14 47.14 C 388.38 47.17 400.62 47.17 412.85 47.15 C 412.83 100.38 412.83 153.62 412.86 206.85 C 400.62 206.83 388.38 206.82 376.14 206.86 C 376.11 184.88 376.29 162.90 376.07 140.93 C 354.36 140.77 332.64 140.78 310.93 140.93 C 310.71 162.90 310.89 184.88 310.85 206.85 C 298.62 206.84 286.38 206.83 274.15 206.86 C 274.18 153.62 274.17 100.38 274.15 47.15 Z" />
      <path fill="#012f87" opacity="1.00" d=" M 442.14 47.15 C 467.10 47.17 492.05 47.18 517.00 47.14 C 523.82 46.83 530.87 47.84 536.96 51.07 C 541.27 53.24 545.79 55.29 549.19 58.81 C 552.66 62.34 556.19 65.81 559.67 69.32 C 562.80 72.42 564.47 76.55 566.73 80.25 C 571.89 88.53 574.55 98.08 576.28 107.60 C 577.04 112.04 578.10 116.47 577.89 121.00 C 577.58 128.63 578.57 136.37 576.73 143.87 C 574.55 158.85 568.62 173.31 559.15 185.15 C 553.78 190.46 548.85 196.42 542.14 200.10 C 535.89 204.30 528.47 206.30 521.03 206.85 C 494.74 206.83 468.44 206.82 442.15 206.85 C 442.17 153.62 442.18 100.38 442.14 47.15 M 478.94 74.93 C 478.77 109.97 478.77 145.02 478.93 180.07 C 488.29 180.32 497.65 180.06 507.01 180.21 C 513.69 180.31 520.65 178.26 525.51 173.51 C 534.06 164.95 538.42 153.15 540.61 141.46 C 541.52 137.56 540.77 133.50 541.74 129.61 C 542.58 126.74 541.09 123.92 541.18 121.04 C 541.31 112.78 538.68 104.79 535.98 97.09 C 534.10 91.50 530.26 86.92 526.49 82.51 C 521.63 77.07 514.16 74.66 507.01 74.79 C 497.65 74.95 488.29 74.68 478.94 74.93 Z" />
    </g>
    <g id="forward-mark-dark">
      <path fill="#008231" opacity="1.00" d=" M 67.29 137.26 C 69.15 134.03 70.73 130.60 73.18 127.75 C 76.90 135.48 81.51 142.76 85.80 150.19 C 96.96 169.69 108.38 189.02 119.47 208.56 C 127.46 221.93 134.89 235.65 143.05 248.91 C 96.40 248.80 49.75 248.75 3.10 248.93 C 10.62 234.70 19.17 221.05 27.01 206.99 C 40.42 183.74 53.89 160.52 67.29 137.26 Z" />
    </g>
  </svg>
);

// 예시 질문 데이터
const EXAMPLE_QUESTIONS = [
  {
    icon: Sparkles,
    question: "이 계약이 우리 회사 내부 결재 규정이나 법무 가이드라인을 위반하는 부분이 있는지 확인해줘",
    color: "from-violet-500/20 to-purple-500/20"
  },
  {
    icon: Lightbulb,
    question: "이 영문 계약서에서 준거법과 관할 조항이 우리 회사에 어떤 영향을 주는지 쉽게 설명해줘",
    color: "from-blue-500/20 to-cyan-500/20"
  },
  {
    icon: Code,
    question: "이 NDA에서 우리 회사에 불리한 조항이 있는지 핵심만 정리해주고, 수정 제안도 같이 해줘.",
    color: "from-indigo-500/20 to-blue-500/20"
  }
];

export const Assistant = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // CosmosDB에서 대화 내역 가져오기
  const fetchRoomHistory = async (userNo: string, roomId: string): Promise<Message[]> => {
    try {
      const response = await fetch(
        `/db/get_room_history?user_no=${userNo}&room_id=${roomId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`History fetch failed (${response.status}):`, errorText);
        return [];
      }

      const data = await response.json();

      if (data.error) {
        console.error("Server returned error:", data.error);
        return [];
      }

      return data.messages || [];
    } catch (error) {
      console.error("Failed to fetch room history:", error);
      return [];
    }
  };

  // CosmosDB에서 채팅 히스토리 로드 (localStorage 제거)
  useEffect(() => {
    const loadHistory = async () => {
      setIsLoadingHistory(true);

      try {
        const serverMessages = await fetchRoomHistory(TEST_USER_NO, TEST_ROOM_ID);

        if (serverMessages.length > 0) {
          // 서버 데이터로 새로운 채팅 생성
          const serverChatId = `server-${TEST_ROOM_ID}`;
          const serverChat: Chat = {
            id: serverChatId,
            title: `💾 이전 대화 (${TEST_ROOM_ID})`,
            messages: serverMessages,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          };

          setChats([serverChat]);

          // 서버 채팅을 자동 선택
          setCurrentChatId(serverChatId);
          setMessages(serverMessages);
        } else {
          // CosmosDB에 데이터가 없으면 빈 상태
          setChats([]);
        }
      } catch (error) {
        console.error("Failed to load server history:", error);
        // 서버 로드 실패 시 빈 상태 유지
        setChats([]);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, []);

  // 채팅 히스토리 저장 (메모리만 사용, localStorage 제거)
  const saveChats = (updatedChats: Chat[]) => {
    setChats(updatedChats);
    // localStorage 저장 제거: CosmosDB만 사용
  };

  // 새 채팅 생성
  const createNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
    setInput("");
  };

  // 채팅 선택
  const selectChat = (chatId: string) => {
    const chat = chats.find((c) => c.id === chatId);
    if (chat) {
      setCurrentChatId(chatId);
      setMessages(chat.messages);
    }
  };

  // 채팅 삭제
  const deleteChat = (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updatedChats = chats.filter((c) => c.id !== chatId);
    saveChats(updatedChats);
    if (currentChatId === chatId) {
      if (updatedChats.length > 0) {
        const lastChat = updatedChats[updatedChats.length - 1];
        setCurrentChatId(lastChat.id);
        setMessages(lastChat.messages);
      } else {
        createNewChat();
      }
    }
  };

  // 채팅 제목 생성 (첫 번째 사용자 메시지에서)
  const generateChatTitle = (messages: Message[]): string => {
    const firstUserMessage = messages.find((m) => m.role === "user");
    if (firstUserMessage) {
      return firstUserMessage.content.slice(0, 30) + (firstUserMessage.content.length > 30 ? "..." : "");
    }
    return "New Chat";
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 예시 질문 클릭 핸들러
  const handleExampleClick = (question: string) => {
    setInput(question);
  };

  // 메시지 복사 핸들러
  const handleCopy = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  // 재시도 핸들러
  const handleRetry = (index: number) => {
    // 해당 메시지 이전까지의 메시지만 남기고 재전송
    const userMessageIndex = index - 1;
    if (userMessageIndex >= 0 && messages[userMessageIndex].role === "user") {
      const userMessage = messages[userMessageIndex].content;
      const messagesUntilUser = messages.slice(0, userMessageIndex);
      setMessages(messagesUntilUser);
      setInput(userMessage);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);

    // 새 채팅인 경우 ID 생성
    let chatId = currentChatId;
    if (!chatId) {
      chatId = `chat-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      setCurrentChatId(chatId);
    }

    // 사용자 메시지 추가
    const updatedMessages = [...messages, { role: "user" as const, content: userMessage }];
    setMessages(updatedMessages);

    try {
      console.log("[Assistant] API 호출 시작");

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_query: userMessage,
          user_no: TEST_USER_NO,
          room_id: TEST_ROOM_ID,
          chat_id: chatId,
          exe_date: new Date().toISOString(),
        }),
      });

      console.log("[Assistant] 응답 상태:", response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantMessage = "";

      // 빈 assistant 메시지 추가
      const finalMessages = [...updatedMessages, { role: "assistant" as const, content: "" }];
      setMessages(finalMessages);
      setStatusMessage("");

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("[Assistant] 스트림 종료");
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.substring(6).trim();
            if (!jsonStr) continue;

            try {
              const message = JSON.parse(jsonStr);
              console.log("[Assistant] SSE 이벤트:", message.type);

              if (message.type === "text-delta") {
                // Vercel AI SDK: 토큰 단위 텍스트 스트리밍
                assistantMessage += message.delta || "";
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = {
                    ...newMessages[newMessages.length - 1],
                    content: assistantMessage,
                  };
                  return newMessages;
                });
              } else if (message.type === "message-metadata") {
                // 진행 상태 업데이트
                const status = message.messageMetadata?.status || "";
                console.log("[Status]", status);
                setStatusMessage(status);
              } else if (message.type === "text-start") {
                console.log("[Assistant] 텍스트 스트리밍 시작:", message.id);
              } else if (message.type === "text-end") {
                console.log("[Assistant] 텍스트 스트리밍 종료:", message.id);
              } else if (message.type === "start") {
                console.log("[Assistant] 메시지 시작");
              } else if (message.type === "finish") {
                console.log("[Assistant] 메시지 완료");
                setStatusMessage("");
              } else if (message.type === "error") {
                throw new Error(message.errorText || "알 수 없는 오류");
              }
            } catch (e) {
              if (e instanceof Error && e.message !== "알 수 없는 오류") {
                // JSON 파싱 에러가 아닌 throw된 에러는 re-throw
                if (!(e instanceof SyntaxError)) throw e;
              }
              console.error("Failed to parse SSE:", jsonStr, e);
            }
          }
        }
      }

      setStatusMessage("");

      // 채팅 저장
      const finalMessagesWithResponse = [...updatedMessages, { role: "assistant" as const, content: assistantMessage }];
      const chatTitle = generateChatTitle(finalMessagesWithResponse);
      
      const updatedChats = chats.filter((c) => c.id !== chatId);
      const chat: Chat = {
        id: chatId!,
        title: chatTitle,
        messages: finalMessagesWithResponse,
        createdAt: chats.find((c) => c.id === chatId)?.createdAt || Date.now(),
        updatedAt: Date.now(),
      };
      saveChats([...updatedChats, chat]);
    } catch (error) {
      console.error("[Assistant] Error:", error);
      const errorMessages = [...updatedMessages, {
        role: "assistant" as const,
        content: "죄송합니다. 오류가 발생했습니다.",
      }];
      setMessages(errorMessages);
    } finally {
      setIsLoading(false);
      setStatusMessage("");
    }
  };

  return (
    <SidebarProvider>
      <div className="flex h-dvh w-full bg-background">
        <Sidebar className="border-r-2 border-sidebar-border/80">
          <SidebarHeader className="mb-2 border-b border-sidebar-border/50 bg-sidebar p-4">
            <div className="flex items-center gap-3">
              <div className="flex aspect-square size-12 items-center justify-center rounded-xl bg-white p-2 shadow-xl">
                <HDHyundaiLogo className="w-full h-full" />
              </div>
              <div className="flex flex-col gap-1 leading-none">
                <span className="font-bold text-lg text-sidebar-foreground">HD HYUNDAI</span>
                <span className="text-xs text-sidebar-foreground/60">법무시스템</span>
              </div>
            </div>
          </SidebarHeader>
          <SidebarContent className="px-3 py-2 custom-scrollbar">
            <div className="flex flex-col gap-2">
              <Button
                variant="ghost"
                className="flex items-center justify-center gap-2 rounded-xl px-4 py-3 bg-gradient-to-r from-primary/10 to-accent/10 hover:from-primary/20 hover:to-accent/20 border border-primary/20 hover:border-primary/40 smooth-transition shadow-md hover:shadow-lg text-sidebar-foreground"
                onClick={createNewChat}
              >
                <PlusIcon className="size-4" />
                <span className="font-semibold">새 대화</span>
              </Button>
              <div className="flex-1 overflow-y-auto custom-scrollbar mt-2">
                {isLoadingHistory && chats.length === 0 ? (
                  <div className="text-sm text-sidebar-foreground/60 px-3 py-6 text-center">
                    <div className="typing-indicator flex gap-1 justify-center">
                      <span className="w-2 h-2 bg-primary rounded-full"></span>
                      <span className="w-2 h-2 bg-primary rounded-full"></span>
                      <span className="w-2 h-2 bg-primary rounded-full"></span>
                    </div>
                    <p className="mt-2">불러오는 중...</p>
                  </div>
                ) : chats.length === 0 ? (
                  <div className="text-sm text-sidebar-foreground/50 px-3 py-6 text-center">
                    <p className="font-medium">대화 내역 없음</p>
                    <p className="text-xs mt-1">새 대화를 시작하세요</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1.5">
                    {chats
                      .sort((a, b) => b.updatedAt - a.updatedAt)
                      .map((chat) => (
                        <div
                          key={chat.id}
                          className={cn(
                            "group flex items-center gap-3 rounded-lg px-3 py-3 text-sm smooth-transition cursor-pointer",
                            currentChatId === chat.id
                              ? "bg-sidebar-accent shadow-lg border border-primary/30"
                              : "hover:bg-sidebar-accent/60 border border-transparent hover:border-sidebar-border/50"
                          )}
                          onClick={() => selectChat(chat.id)}
                        >
                          <MessagesSquare className={cn(
                            "size-4 shrink-0",
                            currentChatId === chat.id ? "text-primary" : "text-sidebar-foreground/50"
                          )} />
                          <span className={cn(
                            "flex-1 truncate text-left",
                            currentChatId === chat.id
                              ? "text-sidebar-foreground font-semibold"
                              : "text-sidebar-foreground/80 font-medium"
                          )}>
                            {chat.title}
                          </span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 smooth-transition hover:bg-destructive/20 hover:text-destructive rounded-lg"
                            onClick={(e) => deleteChat(chat.id, e)}
                          >
                            <Trash2Icon className="size-3.5" />
                          </Button>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </SidebarContent>
        </Sidebar>
        <SidebarInset className="bg-background">
          <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border/70 px-6 backdrop-blur-sm bg-background/95 shadow-sm relative">
            <SidebarTrigger className="hover:bg-secondary/80 smooth-transition rounded-lg" />
            <Separator orientation="vertical" className="mr-2 h-6 bg-border/50" />
            {/* 절대 중앙 정렬을 위한 absolute positioning */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
            </div>
          </header>

          <div className="flex h-[calc(100vh-4rem)] flex-col">
            {/* 메시지 영역 */}
            <div className="flex-1 overflow-y-auto px-4 py-6 custom-scrollbar">
              {messages.length === 0 ? (
                <div className="flex h-full items-center justify-center px-4">
                  <div className="w-full max-w-3xl text-center space-y-8">
                    {/* 헤더 */}
                    <div className="space-y-4">
                      <div className="mx-auto w-40 h-40 rounded-3xl bg-white flex items-center justify-center p-6 shadow-2xl">
                        <HDHyundaiLogo className="w-full h-full" />
                      </div>
                      <h2 className="text-4xl font-bold text-foreground space-y-2">
                        <div>안녕하세요 <span className="bg-gradient-to-r from-primary via-teal-400 to-primary bg-clip-text text-transparent font-bold">HD현대 법무 지원 Agent</span>입니다</div>
                      </h2>
                      <p className="text-muted-foreground text-lg">
                        무엇을 도와드릴까요?
                      </p>
                    </div>

                    {/* 예시 질문 카드 */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
                      {EXAMPLE_QUESTIONS.map((example, index) => {
                        const IconComponent = example.icon;
                        return (
                          <button
                            key={index}
                            onClick={() => handleExampleClick(example.question)}
                            className="suggestion-card rounded-xl p-5 text-center group"
                          >
                            <div className="flex flex-col items-center gap-3">
                              <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${example.color} flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                                <IconComponent className="size-5 text-primary" />
                              </div>
                              <p className="text-sm text-foreground/90 leading-relaxed line-clamp-3 group-hover:text-foreground transition-colors">
                                {example.question}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mx-auto max-w-4xl space-y-6">
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex gap-3 message-enter ${
                        message.role === "user" ? "flex-row-reverse" : "flex-row"
                      }`}
                    >
                      {/* 아바타 아이콘 */}
                      <div className={`flex-shrink-0 ${
                        message.role === "user"
                          ? "w-9 h-9 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg"
                          : "w-9 h-9 rounded-full ai-avatar flex items-center justify-center shadow-xl"
                      }`}>
                        {message.role === "user" ? (
                          <User className="size-5 text-primary-foreground" />
                        ) : (
                          <Sparkles className="size-5 text-white ai-avatar-inner" />
                        )}
                      </div>

                      {/* 메시지 버블 */}
                      <div className="flex flex-col gap-1.5 max-w-[80%]">
                        <span className={`text-xs font-semibold ${
                          message.role === "user"
                            ? "text-right text-muted-foreground"
                            : "text-left text-muted-foreground"
                        }`}>
                          {message.role === "user" ? "Me" : "AI Assistant"}
                        </span>
                        <div
                          className={`rounded-2xl px-5 py-4 shadow-md smooth-transition ${
                            message.role === "user"
                              ? "bg-gradient-to-br from-primary via-primary to-accent text-primary-foreground shadow-xl border border-primary/30"
                              : "bg-card/80 backdrop-blur-sm border border-border/60 shadow-lg"
                          }`}
                        >
                          <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                            {message.content || (
                              <div className="typing-indicator flex gap-1.5 py-1">
                                <span className="w-2 h-2 bg-primary rounded-full"></span>
                                <span className="w-2 h-2 bg-primary rounded-full"></span>
                                <span className="w-2 h-2 bg-primary rounded-full"></span>
                              </div>
                            )}
                          </div>
                          {/* 진행 상태 표시 (마지막 assistant 메시지 + 로딩 중일 때) */}
                          {message.role === "assistant" && isLoading && index === messages.length - 1 && statusMessage && (
                            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground border-t border-border/30 pt-2">
                              <span className="inline-block w-1.5 h-1.5 bg-primary rounded-full animate-pulse"></span>
                              <span>{statusMessage}</span>
                            </div>
                          )}
                        </div>

                        {/* AI 메시지 액션 버튼 */}
                        {message.role === "assistant" && message.content && (
                          <div className="flex gap-1 mt-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 rounded-lg hover:bg-secondary/80 smooth-transition"
                              onClick={() => handleCopy(message.content, index)}
                              title="복사"
                            >
                              {copiedIndex === index ? (
                                <Check className="size-4 text-green-500" />
                              ) : (
                                <Copy className="size-4 text-muted-foreground hover:text-foreground" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 rounded-lg hover:bg-secondary/80 smooth-transition"
                              onClick={() => handleRetry(index)}
                              title="재시도"
                            >
                              <RotateCcw className="size-4 text-muted-foreground hover:text-foreground" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* 입력 영역 */}
            <div className="sticky bottom-0 border-t border-border/70 backdrop-blur-md bg-background/95 p-6 shadow-2xl">
              <form onSubmit={handleSubmit} className="mx-auto max-w-4xl">
                <div className="relative flex items-center gap-3 rounded-2xl bg-card/50 backdrop-blur-sm px-5 py-3.5 shadow-xl border-2 border-border/50 focus-within:border-primary/40 focus-within:shadow-2xl smooth-transition">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="메시지를 입력하세요..."
                    className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground/60 text-sm text-foreground"
                    disabled={isLoading}
                  />
                  <Button
                    type="submit"
                    size="icon"
                    className="size-11 rounded-xl bg-gradient-to-br from-primary via-primary to-accent hover:from-primary/90 hover:via-primary/90 hover:to-accent/90 smooth-transition shadow-xl disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none hover:scale-105"
                    disabled={isLoading || !input.trim()}
                  >
                    <ArrowUpIcon className="size-5" />
                  </Button>
                </div>
                {isLoading && (
                  <p className="text-xs text-muted-foreground text-center mt-3 flex items-center justify-center gap-2">
                    <span className="inline-block w-1 h-1 bg-primary rounded-full animate-pulse"></span>
                    {statusMessage || "AI가 응답을 생성하는 중..."}
                  </p>
                )}
              </form>
            </div>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};
