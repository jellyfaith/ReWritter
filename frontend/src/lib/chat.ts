import { API_BASE, buildAuthHeaders } from "./auth";

export interface ChatSession {
  session_id: string;
  title: string;
  model: string;
  enable_thinking: boolean;
  updated_at: number;
  created_at: number;
}

export interface ChatMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  thinking_content?: string;
  thinking_duration_ms?: number;
  model?: string;
  enable_thinking?: boolean;
  created_at: number;
}

interface SendMessageResponse {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export type ChatStreamEvent =
  | { type: "thinking_delta"; delta: string }
  | { type: "content_delta"; delta: string }
  | { type: "done"; session: ChatSession; assistant_message: ChatMessage }
  | { type: "error"; message: string };

async function parseError(response: Response, fallback: string): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return new Error(payload.detail);
    }
  } catch {
    // Ignore non-JSON errors and return fallback.
  }
  return new Error(fallback);
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const response = await fetch(`${API_BASE}/api/chat/sessions`, {
    method: "GET",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw await parseError(response, "获取会话失败");
  }

  return (await response.json()) as ChatSession[];
}

export async function createChatSession(title?: string): Promise<ChatSession> {
  const response = await fetch(`${API_BASE}/api/chat/sessions`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw await parseError(response, "创建会话失败");
  }

  return (await response.json()) as ChatSession;
}

export async function renameChatSession(sessionId: string, title: string): Promise<ChatSession> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
    method: "PATCH",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw await parseError(response, "重命名会话失败");
  }

  return (await response.json()) as ChatSession;
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw await parseError(response, "删除会话失败");
  }
}

export async function listSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}/messages`, {
    method: "GET",
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw await parseError(response, "获取消息失败");
  }

  return (await response.json()) as ChatMessage[];
}

export async function sendChatMessage(params: {
  sessionId: string;
  content: string;
  model: string;
  enableThinking: boolean;
  useRag?: boolean;
  ragGroupId?: string;
  ragTopK?: number;
}): Promise<SendMessageResponse> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${params.sessionId}/messages`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      content: params.content,
      model: params.model,
      enable_thinking: params.enableThinking,
      use_rag: params.useRag ?? false,
      rag_group_id: params.ragGroupId,
      rag_top_k: params.ragTopK ?? 6,
    }),
  });

  if (!response.ok) {
    throw await parseError(response, "发送消息失败");
  }

  return (await response.json()) as SendMessageResponse;
}

export async function streamChatMessage(
  params: {
    sessionId: string;
    content: string;
    model: string;
    enableThinking: boolean;
    useRag?: boolean;
    ragGroupId?: string;
    ragTopK?: number;
  },
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat/sessions/${params.sessionId}/messages/stream`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    }),
    body: JSON.stringify({
      content: params.content,
      model: params.model,
      enable_thinking: params.enableThinking,
      use_rag: params.useRag ?? false,
      rag_group_id: params.ragGroupId,
      rag_top_k: params.ragTopK ?? 6,
    }),
  });

  if (!response.ok) {
    throw await parseError(response, "发送消息失败");
  }

  if (!response.body) {
    throw new Error("浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  const processBlock = (rawBlock: string) => {
    const lines = rawBlock
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.startsWith("data:"));

    if (lines.length === 0) {
      return;
    }

    const payloadText = lines.map((line) => line.slice(5).trim()).join("\n");
    if (!payloadText) {
      return;
    }

    let event: ChatStreamEvent;
    try {
      event = JSON.parse(payloadText) as ChatStreamEvent;
    } catch {
      // Ignore invalid stream chunks.
      return;
    }

    onEvent(event);
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    blocks.forEach(processBlock);
  }

  if (buffer.trim()) {
    processBlock(buffer);
  }
}
