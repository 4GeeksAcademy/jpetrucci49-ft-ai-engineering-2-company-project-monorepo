export type DeskChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: "completed" | "interrupted";
};

export type DeskChatFrame = {
  type: string;
  session_id?: string;
  message_id?: string;
  text?: string;
  status?: "completed" | "interrupted";
  messages?: DeskChatMessage[];
  detail?: string;
};

export const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000];

export function deskSocketUrl(sessionId: string, token: string): string {
  const origin = (process.env.NEXT_PUBLIC_API_WS_URL ?? "ws://127.0.0.1:8000").replace(/\/$/, "");
  const params = new URLSearchParams({ session_id: sessionId, token });
  return `${origin}/agent/chat?${params.toString()}`;
}

export function applyDeskFrame(current: DeskChatMessage[], frame: DeskChatFrame): DeskChatMessage[] {
  if (frame.type === "history" && Array.isArray(frame.messages)) {
    return frame.messages.map((message) => ({
      id: message.id,
      role: message.role,
      text: message.text,
      status: message.status,
    }));
  }
  if (frame.type === "token_chunk" && frame.message_id && frame.text) {
    const existing = current.find((message) => message.id === frame.message_id);
    if (!existing) {
      return [
        ...current,
        { id: frame.message_id, role: "assistant", text: frame.text },
      ];
    }
    return current.map((message) =>
      message.id === frame.message_id ? { ...message, text: message.text + frame.text } : message
    );
  }
  if (frame.type === "generation_interrupted" && frame.message_id) {
    return current.map((message) =>
      message.id === frame.message_id ? { ...message, status: "interrupted" } : message
    );
  }
  if (frame.type === "generation_completed" && frame.message_id) {
    return current.map((message) =>
      message.id === frame.message_id
        ? {
            ...message,
            text: typeof frame.text === "string" ? frame.text : message.text,
            status: "completed",
          }
        : message
    );
  }
  return current;
}
