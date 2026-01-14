"use client";

import { useState, useRef, useEffect } from "react";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { ArrowUpIcon, MessagesSquare, PlusIcon } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export const Assistant = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);

    // 사용자 메시지 추가
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    try {
      console.log("[Assistant] API 호출 시작");

      const response = await fetch("/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [
            ...messages,
            { role: "user", content: userMessage },
          ],
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
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

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
              console.log("[Assistant] 메시지:", message.type);

              if (message.type === "complete") {
                const text =
                  typeof message.content === "string"
                    ? message.content
                    : message.content?.message || "";

                assistantMessage = text;

                // 마지막 메시지 업데이트
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].content = text;
                  return newMessages;
                });

                console.log("[Assistant] 텍스트 업데이트 완료");
              } else if (message.type === "content") {
                assistantMessage += message.content;

                // 마지막 메시지 업데이트
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].content = assistantMessage;
                  return newMessages;
                });
              } else if (message.type === "status") {
                console.log("[Status]", message.content);
              } else if (message.type === "error") {
                throw new Error(message.content);
              }
            } catch (e) {
              console.error("Failed to parse SSE:", jsonStr, e);
            }
          }
        }
      }
    } catch (error) {
      console.error("[Assistant] Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "죄송합니다. 오류가 발생했습니다.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SidebarProvider>
      <div className="flex h-dvh w-full pr-0.5">
        <Sidebar>
          <SidebarHeader className="mb-2 border-b">
            <div className="flex items-center justify-between">
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton size="lg" asChild>
                    <div className="flex items-center gap-2">
                      <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                        <MessagesSquare className="size-4" />
                      </div>
                      <div className="flex flex-col gap-0.5 leading-none">
                        <span className="font-semibold">Chat</span>
                      </div>
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </div>
          </SidebarHeader>
          <SidebarContent className="px-2">
            <div className="flex flex-col gap-1.5">
              <Button
                variant="ghost"
                className="flex items-center justify-start gap-2 rounded-lg px-2.5 py-2 text-start hover:bg-muted"
                onClick={() => {
                  setMessages([]);
                }}
              >
                <PlusIcon className="size-4" />
                New Chat
              </Button>
              {/* 채팅 목록이 여기에 표시됩니다 */}
              <div className="text-sm text-muted-foreground px-3 py-2">
                채팅 목록이 여기에 표시됩니다
              </div>
            </div>
          </SidebarContent>
        </Sidebar>
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink
                    href="https://www.assistant-ui.com/docs/getting-started"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Build Your Own ChatGPT UX
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Starter Template</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </header>

          <div className="flex h-[calc(100vh-4rem)] flex-col">
            {/* 메시지 영역 */}
            <div className="flex-1 overflow-y-auto px-4 py-4">
              {messages.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <h2 className="text-2xl font-semibold">Hello there!</h2>
                    <p className="text-muted-foreground">
                      How can I help you today?
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mx-auto max-w-3xl space-y-4">
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${
                        message.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[80%] rounded-3xl px-5 py-2.5 ${
                          message.role === "user"
                            ? "bg-muted"
                            : "bg-background border"
                        }`}
                      >
                        <div className="whitespace-pre-wrap break-words">
                          {message.content || (
                            <span className="text-muted-foreground">...</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* 입력 영역 */}
            <div className="sticky bottom-0 border-t bg-background p-4">
              <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
                <div className="relative flex items-center gap-2 rounded-3xl border bg-muted px-4 py-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Send a message..."
                    className="flex-1 bg-transparent outline-none"
                    disabled={isLoading}
                  />
                  <Button
                    type="submit"
                    size="icon"
                    className="size-8 rounded-full"
                    disabled={isLoading || !input.trim()}
                  >
                    <ArrowUpIcon className="size-4" />
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};
