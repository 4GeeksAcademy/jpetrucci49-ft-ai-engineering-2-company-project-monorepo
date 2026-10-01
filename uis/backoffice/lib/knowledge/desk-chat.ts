export type DeskChatMessage = {
  message_id: string;
  role: "user" | "assistant";
  text: string;
  status?: "completed" | "interrupted";
};

export type DeskChatFrame = {
  event: string;
  data?: {
    session_id?: string;
    token?: string;
    sequence?: number;
    message_id?: string;
    text?: string;
    status?: "completed" | "interrupted";
    messages?: DeskChatMessage[];
  };
};

export const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000];

export function deskSocketUrl(sessionId: string, token: string): string {
  const origin = (process.env.NEXT_PUBLIC_API_WS_URL ?? "ws://127.0.0.1:8000").replace(/\/$/, "");
  const params = new URLSearchParams({ session_id: sessionId, token });
  return `${origin}/agent/chat?${params.toString()}`;
}

export function applyDeskFrame(current: DeskChatMessage[], frame: DeskChatFrame): DeskChatMessage[] {
  const data = frame.data ?? {};
  if (frame.event === "session_snapshot" && Array.isArray(data.messages)) {
    return data.messages.map((message) => ({
      message_id: message.message_id,
      role: message.role,
      text: message.text,
      status: message.status,
    }));
  }
  if (frame.event === "token_chunk" && data.token) {
    const token = data.token;
    const open = openAssistantIndex(current);
    if (open < 0) {
      return [
        ...current,
        {
          message_id: `pending-${data.sequence ?? current.length}`,
          role: "assistant",
          text: token,
        },
      ];
    }
    return current.map((message, index) =>
      index === open ? { ...message, text: message.text + token } : message
    );
  }
  if (frame.event === "generation_interrupted" && data.message_id) {
    return finishAssistant(current, data.message_id, "interrupted");
  }
  if (frame.event === "generation_completed" && data.message_id) {
    return finishAssistant(current, data.message_id, "completed", data.text);
  }
  return current;
}

function openAssistantIndex(current: DeskChatMessage[]): number {
  for (let index = current.length - 1; index >= 0; index -= 1) {
    const message = current[index];
    if (message.role === "assistant" && message.status !== "completed" && message.status !== "interrupted") {
      return index;
    }
  }
  return -1;
}

function finishAssistant(
  current: DeskChatMessage[],
  messageId: string,
  status: "completed" | "interrupted",
  text?: string
): DeskChatMessage[] {
  const exact = current.findIndex((message) => message.message_id === messageId);
  const target = exact >= 0 ? exact : openAssistantIndex(current);
  if (target < 0) return current;
  return current.map((message, index) =>
    index === target
      ? {
          ...message,
          message_id: messageId,
          text: typeof text === "string" ? text : message.text,
          status,
        }
      : message
  );
}
