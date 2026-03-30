import { useState, useRef, useEffect, useCallback } from "react";
import { streamQuery } from "../../api";
import "./ChatPanel.css";

const KAKAO_REST_KEY = import.meta.env.VITE_KAKAO_API_KEY;

// "강남역 보여줘" 같은 지도 이동 패턴
const NAV_PATTERN = /(.+?)\s*(보여줘|보여 줘|이동|찾아줘|찾아 줘|어디)/;

// 사용자 입력에 지역명이 포함되었는지 판별하는 키워드 목록
const AREA_KEYWORDS = [
  "강남", "강동", "강북", "강서", "관악", "광진", "구로", "금천",
  "노원", "도봉", "동대문", "동작", "마포", "서대문", "서초", "성동",
  "성북", "송파", "양천", "영등포", "용산", "은평", "종로", "중구",
  "중랑", "홍대", "신촌", "이태원", "잠실", "건대", "압구정", "청담",
  "삼성", "역삼", "선릉", "논현", "신사", "방배", "사당", "신림",
  "여의도", "목동", "합정", "망원", "연남", "성수", "왕십리", "혜화",
  "대학로", "을지로", "명동", "남대문", "북촌", "서촌", "익선동",
];

export default function ChatPanel({ isOpen, onToggle, onNavigate, mapContext, onClearContext }) {
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

    // ── 지역명 포함 여부 판별 ──────────────────────────────────
    // 사용자가 직접 지역명을 입력했으면 → admCd 없이 텍스트 기반 분석
    // 업종만 입력했으면 → 현재 컨텍스트의 admCd 사용
    const userMentionedArea = AREA_KEYWORDS.some((kw) => text.includes(kw));
    const currentAreaName = mapContext?.guName?.replace(/구$/, "") || "";
    const mentionedCurrentArea = currentAreaName && text.includes(currentAreaName);

    // admCd 사용 조건: 컨텍스트가 있고, 사용자가 다른 지역을 언급하지 않았을 때
    const useAdmCd = mapContext?.admCd && (!userMentionedArea || mentionedCurrentArea);

    let question = text;
    if (useAdmCd && mapContext?.guName) {
      // 업종만 입력한 경우 → 컨텍스트 지역명 자동 추가
      const alreadyHasArea = text.includes(currentAreaName) || (mapContext.dongName && text.includes(mapContext.dongName));
      if (!alreadyHasArea) {
        const simpleBusinessPattern = /^(카페|한식|중식|일식|양식|치킨|분식|호프|술집|베이커리|패스트푸드|미용실|네일|노래방|편의점|커피)\s*(창업|분석|상권)?/;
        if (simpleBusinessPattern.test(text)) {
          question = `${currentAreaName} ${text} 상권 분석해줘`;
        }
      }
    }

    setLoading(true);
    const streamMsgId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: streamMsgId, role: "assistant", content: "" },
    ]);
    let accumulated = "";
    try {
      await streamQuery(question, 3, sessionId, (eventName, data) => {
        if (eventName === "chunk") {
          accumulated += data.text || data.content || "";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamMsgId ? { ...m, content: accumulated } : m,
            ),
          );
        } else if (eventName === "complete") {
          if (data.session_id) setSessionId(data.session_id);
          const draft = data.draft || accumulated || "응답을 받지 못했습니다.";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamMsgId ? { ...m, content: draft } : m,
            ),
          );
        } else if (eventName === "error" || eventName === "rejected") {
          const msg = data.message || data.reason || "오류가 발생했습니다.";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamMsgId ? { ...m, content: msg } : m,
            ),
          );
        }
      });
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === streamMsgId
            ? { ...m, content: `오류가 발생했습니다: ${err.message}` }
            : m,
        ),
      );
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
  const contextLabel = mapContext?.guName
    ? `${mapContext.guName} ${mapContext.dongName || ""}`.trim()
    : mapContext?.dongName || "";
  const placeholder = contextLabel
    ? `${contextLabel} 지역에 대해 질문하세요 (예: 카페 창업 분석)`
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

        {/* ── 현재 선택된 지역 컨텍스트 표시 ── */}
        {mapContext?.dongName && (
          <div className="mv-chat-context">
            <span className="mv-chat-context__label">
              📍 {mapContext.guName ? `${mapContext.guName} ` : ""}{mapContext.dongName}
            </span>
            <button
              className="mv-chat-context__clear"
              onClick={() => onClearContext?.()}
              title="선택 해제 (다른 지역 자유 입력)"
            >
              ✕
            </button>
          </div>
        )}

        <div className="mv-chat-messages">
          {messages.length === 0 && (
            <div className="mv-chat-msg mv-chat-msg--system">
              지역과 업종을 입력하면 상권을 분석해드립니다.
              <br />
              다른 지역명을 직접 입력하면 해당 지역으로 분석됩니다.
              <br />
              (예: "홍대 카페 분석", "강남 vs 잠실 한식 비교")
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
