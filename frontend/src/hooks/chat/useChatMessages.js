import { useState, useCallback } from "react";

/**
 * 채팅 메시지 히스토리, 세션 ID, 재무 파라미터 캐시를 관리하는 훅.
 * UserChat에서 사용된다.
 */
export function useChatMessages() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [latestParams, setLatestParams] = useState(null);

  const addMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const updateAt = useCallback((index, updates) => {
    setMessages((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  }, []);

  return {
    messages,
    sessionId,
    setSessionId,
    latestParams,
    setLatestParams,
    addMessage,
    updateAt,
  };
}
