import { useState, useRef, useEffect, useCallback } from "react";
import { sendChatMessage } from "../api/agentApi";
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

export default function ChatPanel({ isOpen, onToggle, onNavigate, mapContext, onClearContext, onHighlightArea }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [sessionId, setSessionId] = useState(null);
  const [lastLocation, setLastLocation] = useState(null);   // 직전 분석 지역 (UI 표시용)
  const [lastBusiness, setLastBusiness] = useState(null);   // 직전 분석 업종 (UI 표시용)
  const [lightboxSrc, setLightboxSrc] = useState(null);     // 팝업으로 크게 볼 이미지

  const messagesEndRef = useRef(null);
  const timerRef = useRef(null);
  const prevContextRef = useRef(null);
  const lastLocationRef = useRef(null);    // 직전 분석 지역 (클로저 캡처용)
  const lastBusinessRef = useRef(null);    // 직전 분석 업종 (클로저 캡처용)

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
        const simpleBusinessPattern = /^(카페|한식|중식|일식|양식|치킨|분식|호프|술집|베이커리|패스트푸드|미용실|네일|노래방|편의점|커피|빵집|치킨집|중국집|초밥|라멘|파스타|햄버거|떡볶이|포차|디저트|브런치)\s*(집|점|가게|창업|분석|상권)?/;
        if (simpleBusinessPattern.test(text)) {
          question = `${currentAreaName} ${text} 상권 분석해줘`;
        }
      }
    }

    // ── 직전 대화 맥락으로 부족한 파라미터 자동 보완 ──────────
    // 지역 없이 업종만 입력 → 직전 지역 보완
    if (!useAdmCd && !userMentionedArea && lastLocationRef.current) {
      const hasBizKeyword = /카페|한식|중식|일식|양식|치킨|분식|호프|술집|베이커리|패스트푸드|미용실|네일|노래방|편의점|커피|빵집|치킨집|중국집|초밥|라멘|파스타|햄버거|떡볶이|포차|디저트|브런치|헤어/.test(text);
      if (hasBizKeyword) {
        question = `${lastLocationRef.current} ${text} 상권 분석해줘`;
      }
    }
    // 업종 없이 지역만 입력 → 직전 업종 보완
    if (userMentionedArea && lastBusinessRef.current) {
      const hasBizKeyword = /카페|한식|중식|일식|양식|치킨|분식|호프|술집|베이커리|패스트푸드|미용실|네일|노래방|편의점|커피|빵집|치킨집|중국집|초밥|라멘|파스타|햄버거|떡볶이|포차|디저트|브런치|헤어/.test(text);
      if (!hasBizKeyword) {
        question = `${text} ${lastBusinessRef.current} 상권 분석해줘`;
      }
    }

    setLoading(true);
    try {
      const res = await sendChatMessage(question, sessionId, useAdmCd ? mapContext.admCd : null);
      if (res.session_id) setSessionId(res.session_id);

      // 분석 결과의 지역/업종 기억 (에러 시 부분 파라미터도 저장)
      if (res.location) {
        lastLocationRef.current = res.location;
        setLastLocation(res.location);
      }
      if (res.business_type) {
        lastBusinessRef.current = res.business_type;
        setLastBusiness(res.business_type);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.analysis || "응답을 받지 못했습니다.",
          charts: res.charts || [],
        },
      ]);

      // 단일 분석 결과 → 지도에 해당 행정동 하이라이트 + 이동
      if (res.type === "analyze" && res.adm_codes?.length && onHighlightArea) {
        onHighlightArea(res.adm_codes);
      }

      // 비교 분석이거나 다른 지역 분석 시 → 이전 하이라이트 초기화
      if (res.type === "compare" && onHighlightArea) {
        onHighlightArea([]);  // 빈 배열 → 하이라이트 초기화만
      }

      // 다른 지역 입력 시 컨텍스트 자동 해제
      if (userMentionedArea && !mentionedCurrentArea && mapContext?.admCd) {
        onClearContext?.();
      }
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
  const contextLabel = mapContext?.guName
    ? `${mapContext.guName} ${mapContext.dongName || ""}`.trim()
    : mapContext?.dongName || "";

  let placeholder;
  if (contextLabel) {
    placeholder = `${contextLabel} 지역에 대해 질문하세요 (예: 카페 창업 분석)`;
  } else if (lastLocation && lastBusiness) {
    placeholder = `업종 또는 지역을 입력하세요 (예: 치킨, 잠실)`;
  } else if (lastLocation) {
    placeholder = `업종을 입력하세요 (예: 카페, 치킨, 한식)`;
  } else if (lastBusiness) {
    placeholder = `지역을 입력하세요 (예: 홍대, 강남, 잠실)`;
  } else {
    placeholder = "상권 분석 질문을 입력하세요 (예: 홍대 카페 상권 분석)";
  }

  return (
    <>
      {/* 차트 팝업 모달 */}
      {lightboxSrc && (
        <div
          onClick={() => setLightboxSrc(null)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            background: "rgba(0,0,0,0.82)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "zoom-out",
          }}
        >
          <img
            src={lightboxSrc}
            alt="차트 크게 보기"
            style={{
              maxWidth: "92vw",
              maxHeight: "92vh",
              borderRadius: 10,
              boxShadow: "0 8px 40px rgba(0,0,0,0.6)",
            }}
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={() => setLightboxSrc(null)}
            style={{
              position: "absolute",
              top: 18,
              right: 22,
              background: "rgba(255,255,255,0.15)",
              border: "none",
              color: "#fff",
              fontSize: 28,
              lineHeight: 1,
              width: 42,
              height: 42,
              borderRadius: "50%",
              cursor: "pointer",
            }}
            title="닫기"
          >
            ✕
          </button>
        </div>
      )}

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

        {/* ── 현재 선택된 지역 컨텍스트 표시 (지도 클릭) ── */}
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

        {/* ── 대화 맥락 표시 (직전 분석의 지역/업종 기억) ── */}
        {!mapContext?.dongName && (lastLocation || lastBusiness) && (
          <div className="mv-chat-context mv-chat-context--memory">
            <span className="mv-chat-context__label">
              🔄 {[lastLocation, lastBusiness].filter(Boolean).join(" · ")}
            </span>
            <button
              className="mv-chat-context__clear"
              onClick={() => {
                lastLocationRef.current = null;
                lastBusinessRef.current = null;
                setLastLocation(null);
                setLastBusiness(null);
              }}
              title="대화 맥락 초기화"
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
              {msg.charts?.map((b64, i) => (
                <img
                  key={i}
                  src={`data:image/png;base64,${b64}`}
                  alt={`상권분석 차트 ${i + 1}`}
                  style={{
                    display: "block",
                    marginTop: 8,
                    borderRadius: 8,
                    maxWidth: "100%",
                    cursor: "zoom-in",
                  }}
                  onClick={() => setLightboxSrc(`data:image/png;base64,${b64}`)}
                  title="클릭하면 크게 볼 수 있습니다"
                />
              ))}
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
