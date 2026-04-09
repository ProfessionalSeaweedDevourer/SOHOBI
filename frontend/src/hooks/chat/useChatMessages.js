import { useState, useCallback, useEffect, useRef } from "react";

const STORAGE_KEY_PREFIX = "sohobi_messages_";
const SESSION_KEY = "sohobi_session_id";
const PARAMS_KEY = "sohobi_latest_params";

/**
 * sessionStorage에 messages를 저장한다. quota 초과 시 무시.
 */
function persistToSession(sessionId, messages, latestParams) {
  if (!sessionId) return;
  try {
    sessionStorage.setItem(
      STORAGE_KEY_PREFIX + sessionId,
      JSON.stringify(messages),
    );
    if (latestParams) {
      sessionStorage.setItem(PARAMS_KEY, JSON.stringify(latestParams));
    }
  } catch {
    // sessionStorage quota 초과 — graceful degradation
  }
}

/**
 * sessionStorage에서 messages를 복원한다.
 */
function restoreFromSession(sessionId) {
  if (!sessionId) return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_PREFIX + sessionId);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function restoreParams() {
  try {
    const raw = sessionStorage.getItem(PARAMS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * 채팅 메시지 히스토리, 세션 ID, 재무 파라미터 캐시를 관리하는 훅.
 * UserChat에서 사용된다.
 *
 * Layer 1: sessionStorage에 자동 persist/restore (같은 탭 새로고침 시 복원)
 * Layer 2: restoreFromApi()를 통한 백엔드 복원 (로그인 사용자, 다른 탭/기기)
 */
export function useChatMessages() {
  // localStorage에서 이전 sessionId 복원
  const savedSessionId = localStorage.getItem(SESSION_KEY) || null;

  const [messages, setMessages] = useState(() => {
    // Layer 1: sessionStorage에서 즉시 복원 시도
    const restored = restoreFromSession(savedSessionId);
    return restored || [];
  });
  const [sessionId, setSessionIdRaw] = useState(savedSessionId);
  const [latestParams, setLatestParams] = useState(() => restoreParams());

  // persist 중복 방지를 위한 ref (초기 복원 시 불필요한 persist 스킵)
  const isInitialMount = useRef(true);

  // messages 변경 시 sessionStorage에 persist
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    persistToSession(sessionId, messages, latestParams);
  }, [messages, sessionId, latestParams]);

  const setSessionId = useCallback((id) => {
    setSessionIdRaw((prev) => {
      // 세션 변경 시 이전 캐시 정리
      if (prev && prev !== id) {
        try {
          sessionStorage.removeItem(STORAGE_KEY_PREFIX + prev);
        } catch {
          // ignore
        }
      }
      return id;
    });
  }, []);

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

  /**
   * Layer 2: 백엔드 API에서 복원된 messages 배열을 프론트 메시지 형식으로 변환·적용.
   * chart/charts는 백엔드에 저장하지 않으므로 null.
   */
  const restoreFromApi = useCallback((apiMessages) => {
    if (!apiMessages?.length) return;
    const restored = apiMessages.map((m) => ({
      question: m.question || "",
      domain: m.domain || "",
      grade: m.grade || "",
      draft: m.draft || "",
      confidenceNote: m.confidence_note || "",
      suggestedActions: m.suggested_actions || [],
      chart: null,
      charts: null,
      status: "approved",
      isPartial: false,
    }));
    setMessages(restored);
  }, []);

  return {
    messages,
    sessionId,
    setSessionId,
    latestParams,
    setLatestParams,
    addMessage,
    updateAt,
    restoreFromApi,
  };
}
