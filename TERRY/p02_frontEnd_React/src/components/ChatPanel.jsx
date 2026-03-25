import { useState, useRef, useEffect, useCallback } from "react";
import { sendChatMessage } from "../api/agentApi";
import "./ChatPanel.css";

const KAKAO_REST_KEY = import.meta.env.VITE_KAKAO_API_KEY;

// "강남역 보여줘" 같은 지도 이동 패턴
const NAV_PATTERN = /(.+?)\s*(보여줘|보여 줘|이동|찾아줘|찾아 줘|어디)/;

export default function ChatPanel({ isOpen, onToggle, onNavigate, mapContext }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [sessionId, setSessionId] = useState(null);

  const messagesEndRef = useRef(null);
  const timerRef = useRef(null);
  const prevContextRef = useRef(null);

  // 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // 로딩 타이머
  useEffect(() => {
    if (loading) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [loading]);

  // 지도 컨텍스트 변경 시 시스템 메시지
  useEffect(() => {
    if (!mapContext || !mapContext.dongName) return;
    const key = `${mapContext.guName}_${mapContext.dongName}`;
    if (key === prevContextRef.current) return;
    prevContextRef.current = key;

    const label = mapContext.guName
      ? `${mapContext.guName} ${mapContext.dongName}`
      : mapContext.dongName;

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "system",
        content: `${label} 선택됨`,
      },
    ]);
  }, [mapContext]);

  // 카카오 키워드 검색으로 좌표 조회
  const geocodeAndNavigate = useCallback(
    async (placeName) => {
      if (!KAKAO_REST_KEY || !onNavigate) return false;
      try {
        const res = await fetch(
          `/kakao/v2/local/search/keyword.json?query=${encodeURIComponent(placeName)}&size=1`,
          { headers: { Authorization: `KakaoAK ${KAKAO_REST_KEY}` } }
        );
        const data = await res.json();
        const place = data.documents?.[0];
        if (place) {
          onNavigate(parseFloat(place.x), parseFloat(place.y), 16);
          return true;
        }
      } catch {
        /* 무시 */
      }
      return false;
    },
    [onNavigate]
  );

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    // 유저 메시지 추가
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: text },
    ]);
    setInput("");

    // 지도 이동 패턴 체크
    const navMatch = text.match(NAV_PATTERN);
    if (navMatch) {
      const moved = await geocodeAndNavigate(navMatch[1].trim());
      if (moved) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: `${navMatch[1].trim()}(으)로 지도를 이동했습니다.`,
          },
        ]);
        return;
      }
    }

    // 에이전트에게 질문 - 컨텍스트가 있으면 지역명 포함
    let question = text;
    if (mapContext?.dongName && !text.includes(mapContext.dongName)) {
      // 사용자가 업종만 입력한 경우 지역 자동 추가
      const simpleBusinessPattern = /^(카페|한식|중식|일식|양식|치킨|분식|호프|술집|베이커리|패스트푸드|미용실|네일|노래방|편의점|커피)\s*(창업|분석|상권)?/;
      if (simpleBusinessPattern.test(text)) {
        question = `${mapContext.dongName} ${text} 상권 분석해줘`;
      }
    }

    setLoading(true);
    try {
      const res = await sendChatMessage(question, sessionId);
      if (res.session_id) setSessionId(res.session_id);

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.analysis || "응답을 받지 못했습니다.",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `오류가 발생했습니다: ${err.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, mapContext, geocodeAndNavigate]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 현재 컨텍스트에 따른 placeholder
  const placeholder = mapContext?.dongName
    ? `${mapContext.dongName} 지역에 대해 질문하세요 (예: 카페 창업 분석)`
    : "상권 분석 질문을 입력하세요 (예: 홍대 카페 상권 분석)";

  return (
    <>
      {/* 토글 버튼 */}
      {!isOpen && (
        <button className="mv-chat-toggle" onClick={onToggle} title="상권분석 채팅">
          💬
        </button>
      )}

      {/* 패널 */}
      <div className={`mv-chat-panel ${isOpen ? "" : "mv-chat-panel--closed"}`}>
        <div className="mv-chat-header">
          <span>상권분석 AI</span>
          <button className="mv-chat-header__close" onClick={onToggle}>
            ✕
          </button>
        </div>

        <div className="mv-chat-messages">
          {messages.length === 0 && (
            <div className="mv-chat-msg mv-chat-msg--system">
              지역과 업종을 입력하면 상권을 분석해드립니다.
              <br />
              지도에서 행정동을 클릭하면 해당 지역이 자동 선택됩니다.
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`mv-chat-msg mv-chat-msg--${msg.role}`}>
              {msg.content}
            </div>
          ))}

          {loading && (
            <div className="mv-chat-loading">
              <div className="mv-chat-dots">
                <span />
                <span />
                <span />
              </div>
              <span>분석 중... ({elapsed}초)</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="mv-chat-input-area">
          <textarea
            className="mv-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={loading}
          />
          <button
            className="mv-chat-send"
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            ➤
          </button>
        </div>
      </div>
    </>
  );
}
