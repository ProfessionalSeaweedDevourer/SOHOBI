import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamQuery } from "../../api";
import ProgressPanel from "../ProgressPanel";
import ActionButtons from "../ActionButtons";
import { motion, AnimatePresence } from "motion/react";
import { MessageSquare, X, MapPin, Send } from "lucide-react";
import SimulationChart from "../SimulationChart";
import "./ChatPanel.css";

const KAKAO_REST_KEY = import.meta.env.VITE_KAKAO_API_KEY;

// 지역명 공유 배열 (한 번만 정의)
const AREA_NAMES = [
   "강남",
   "강동",
   "강북",
   "강서",
   "관악",
   "광진",
   "구로",
   "금천",
   "노원",
   "도봉",
   "동대문",
   "동작",
   "마포",
   "서대문",
   "서초",
   "성동",
   "성북",
   "송파",
   "양천",
   "영등포",
   "용산",
   "은평",
   "종로",
   "중구",
   "중랑",
   "홍대",
   "신촌",
   "이태원",
   "잠실",
   "건대",
   "압구정",
   "청담",
   "삼성",
   "역삼",
   "선릉",
   "논현",
   "신사",
   "방배",
   "사당",
   "신림",
   "여의도",
   "목동",
   "합정",
   "망원",
   "연남",
   "성수",
   "왕십리",
   "혜화",
   "대학로",
   "을지로",
   "명동",
   "남대문",
   "북촌",
   "서촌",
   "익선동",
];

// 응답 텍스트의 지역명을 클릭 가능한 span으로 변환 (접미사 조건으로 오탐 방지)
const AREA_PATTERN = new RegExp(
   `(${AREA_NAMES.join("|")})(?=구|동|역|로|\\s|,|\\.|!|\\?|$)`,
   "g",
);

function renderWithAreaLinks(text, onHighlight, keyBase) {
   const parts = text.split(AREA_PATTERN);
   return parts.map((part, i) =>
      i % 2 === 1 ? (
         <span
            key={`al-${keyBase}-${i}`}
            className="mv-chat-area-link"
            onClick={() => onHighlight?.(part)}
            title={`${part} 지도에서 보기`}
         >
            {part}
         </span>
      ) : (
         part
      ),
   );
}

// "강남역 보여줘" 같은 지도 이동 패턴
const NAV_PATTERN = /(.+?)\s*(보여줘|보여 줘|이동|찾아줘|찾아 줘|어디)/;

// 사용자 입력에 지역명이 포함되었는지 판별하는 키워드 목록
const AREA_KEYWORDS = AREA_NAMES;

export default function ChatPanel({
   isOpen,
   onToggle,
   dongPanelOpen,
   hasPopup,
   onNavigate,
   mapContext,
   onClearContext,
   onHighlightArea,
   onFindAndHighlightByName,
   onSearchArea,
}) {
   const [messages, setMessages] = useState([]);
   const [input, setInput] = useState("");
   const [loading, setLoading] = useState(false);
   const [elapsed, setElapsed] = useState(0);
   const [sessionId, setSessionId] = useState(null);
   const [activeEvents, setActiveEvents] = useState([]);
   const [enlargedChart, setEnlargedChart] = useState(null);

   const messagesEndRef = useRef(null);
   const timerRef = useRef(null);
   const prevContextRef = useRef(null);
   const lastLocationRef = useRef(null);
   const lastBusinessRef = useRef(null);
   const chipsRef = useRef(null);
   const chipsDragRef = useRef({
      dragging: false,
      moved: false,
      startX: 0,
      scrollLeft: 0,
   });
   const autoSendTimerRef = useRef(null);
   const handleSendRef = useRef(null);

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

   // 지도 컨텍스트 변경 시 시스템 메시지 + 지역 단독 쿼리 자동 전송
   useEffect(() => {
      if (!mapContext || !mapContext.dongName) return;
      const key = `${mapContext.guName}_${mapContext.dongName}`;
      if (key === prevContextRef.current) return;
      prevContextRef.current = key;

      const label = mapContext.guName
         ? `${mapContext.guName.replace(/구$/, "")} ${mapContext.dongName}`
         : mapContext.dongName;

      setMessages((prev) => [
         ...prev,
         {
            id: crypto.randomUUID(),
            role: "system",
            content: `${mapContext.guName ? `${mapContext.guName} ` : ""}${mapContext.dongName} 선택됨`,
         },
      ]);
      // 지역만 담긴 쿼리 → 백엔드가 업종 선택 버튼 반환 (300ms debounce: 빠른 연속 클릭 방어)
      clearTimeout(autoSendTimerRef.current);
      autoSendTimerRef.current = setTimeout(() => {
         handleSendRef.current?.(`${label} 상권 분석`);
      }, 300);
      return () => clearTimeout(autoSendTimerRef.current);
      // eslint-disable-next-line react-hooks/exhaustive-deps
   }, [mapContext]);

   // 카카오 키워드 검색으로 좌표 조회
   const geocodeAndNavigate = useCallback(
      async (placeName) => {
         if (!KAKAO_REST_KEY || !onNavigate) return false;
         try {
            const res = await fetch(
               `/kakao/v2/local/search/keyword.json?query=${encodeURIComponent(placeName)}&size=1`,
               { headers: { Authorization: `KakaoAK ${KAKAO_REST_KEY}` } },
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
      [onNavigate],
   );

   const handleSend = useCallback(
      async (directText) => {
         const text = (
            typeof directText === "string" ? directText : input
         ).trim();
         if (!text || loading) return;

         setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "user", content: text },
         ]);
         if (typeof directText !== "string") setInput("");

         // 지도 이동 패턴 체크
         const navMatch = text.match(NAV_PATTERN);
         if (navMatch) {
            const placeName = navMatch[1].trim();
            const moved = await geocodeAndNavigate(placeName);
            if (moved) {
               setMessages((prev) => [
                  ...prev,
                  {
                     id: crypto.randomUUID(),
                     role: "system",
                     content: `${placeName}(으)로 지도를 이동했습니다.`,
                  },
               ]);
               return;
            }
            if (onSearchArea) {
               onSearchArea(placeName);
               setMessages((prev) => [
                  ...prev,
                  {
                     id: crypto.randomUUID(),
                     role: "system",
                     content: `지도에서 "${placeName}" 검색 중입니다.`,
                  },
               ]);
               return;
            }
            setMessages((prev) => [
               ...prev,
               {
                  id: crypto.randomUUID(),
                  role: "system",
                  content: `지도 이동 기능을 사용할 수 없습니다. 상권 분석은 "홍대 카페 분석" 형식으로 입력하세요.`,
               },
            ]);
            return;
         }

         // 지역명 / 업종 포함 여부 판별
         const userMentionedArea = AREA_KEYWORDS.some((kw) =>
            text.includes(kw),
         );
         const currentAreaName = mapContext?.guName?.replace(/구$/, "") || "";
         const mentionedCurrentArea =
            currentAreaName && text.includes(currentAreaName);
         const bizPattern =
            /카페|한식|중식|일식|양식|치킨|분식|호프|술집|베이커리|패스트푸드|미용실|네일|노래방|편의점|커피/;
         const hasBizKeyword = bizPattern.test(text);

         const useAdmCd =
            mapContext?.admCd && (!userMentionedArea || mentionedCurrentArea);

         let question = text;
         if (useAdmCd && mapContext?.guName) {
            const alreadyHasArea =
               text.includes(currentAreaName) ||
               (mapContext.dongName && text.includes(mapContext.dongName));
            if (!alreadyHasArea && hasBizKeyword) {
               question = `${currentAreaName} ${text} 상권 분석해줘`;
            }
         } else if (
            !userMentionedArea &&
            hasBizKeyword &&
            lastLocationRef.current
         ) {
            question = `${lastLocationRef.current} ${text} 상권 분석해줘`;
         } else if (
            userMentionedArea &&
            !hasBizKeyword &&
            lastBusinessRef.current
         ) {
            question = `${text} ${lastBusinessRef.current} 상권 분석해줘`;
         }

         setLoading(true);
         setActiveEvents([]);
         const streamMsgId = crypto.randomUUID();
         setMessages((prev) => [
            ...prev,
            { id: streamMsgId, role: "assistant", content: "" },
         ]);
         let accumulated = "";
         try {
            await streamQuery(question, 3, sessionId, (eventName, data) => {
               setActiveEvents((prev) => [
                  ...prev,
                  { event: eventName, ...data },
               ]);

               if (eventName === "chunk") {
                  accumulated += data.text || data.content || "";
                  setMessages((prev) =>
                     prev.map((m) =>
                        m.id === streamMsgId
                           ? { ...m, content: accumulated }
                           : m,
                     ),
                  );
               } else if (eventName === "complete") {
                  setActiveEvents([]);
                  if (data.session_id) setSessionId(data.session_id);
                  const draft =
                     data.draft || accumulated || "응답을 받지 못했습니다.";
                  const charts = data.charts || [];
                  const chart = data.chart || null;
                  const suggestedActions = data.suggested_actions || [];
                  setMessages((prev) =>
                     prev.map((m) =>
                        m.id === streamMsgId
                           ? { ...m, content: draft, charts, chart, suggestedActions }
                           : m,
                     ),
                  );
                  const codes = data.adm_codes || [];
                  const atype = data.analysis_type || "";
                  if (codes.length > 0 && onHighlightArea) {
                     onHighlightArea(codes);
                  } else if (atype === "compare" && onHighlightArea) {
                     onHighlightArea([]);
                  }
                  const foundArea = AREA_KEYWORDS.find((kw) =>
                     question.includes(kw),
                  );
                  if (foundArea) lastLocationRef.current = foundArea;
                  const BIZ_LIST = [
                     "카페",
                     "한식",
                     "중식",
                     "일식",
                     "양식",
                     "치킨",
                     "분식",
                     "호프",
                     "술집",
                     "베이커리",
                     "패스트푸드",
                     "미용실",
                     "네일",
                     "노래방",
                     "편의점",
                     "커피",
                  ];
                  const foundBiz = BIZ_LIST.find((b) => question.includes(b));
                  if (foundBiz) lastBusinessRef.current = foundBiz;
               } else if (eventName === "error" || eventName === "rejected") {
                  setActiveEvents([]);
                  const msg =
                     data.message || data.reason || "오류가 발생했습니다.";
                  setMessages((prev) =>
                     prev.map((m) =>
                        m.id === streamMsgId ? { ...m, content: msg } : m,
                     ),
                  );
               }
            });
         } catch (err) {
            setActiveEvents([]);
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
      },
      [input, loading, sessionId, mapContext, geocodeAndNavigate, onSearchArea],
   );
   handleSendRef.current = handleSend;

   const handleKeyDown = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
         e.preventDefault();
         handleSend();
      }
   };

   const contextLabel = mapContext?.guName
      ? `${mapContext.guName} ${mapContext.dongName || ""}`.trim()
      : mapContext?.dongName || "";
   const placeholder = contextLabel
      ? `${contextLabel} 지역에 대해 질문하세요 (예: 카페 창업 분석)`
      : "상권 분석 질문을 입력하세요 (예: 홍대 카페 상권 분석)";

   // 응답 텍스트 지역명 → 클릭 가능한 span (클릭 시 동 폴리곤 하이라이트 + 지도 이동)
   const markdownComponents = useMemo(
      () => ({
         p: ({ children }) => {
            const toArr = Array.isArray(children) ? children : [children];
            const processed = toArr.flatMap((child, i) =>
               typeof child === "string"
                  ? renderWithAreaLinks(
                       child,
                       onFindAndHighlightByName,
                       i * 1000,
                    )
                  : [child],
            );
            return <p>{processed}</p>;
         },
         li: ({ children }) => {
            const toArr = Array.isArray(children) ? children : [children];
            const processed = toArr.flatMap((child, i) =>
               typeof child === "string"
                  ? renderWithAreaLinks(
                       child,
                       onFindAndHighlightByName,
                       i * 1000 + 500,
                    )
                  : [child],
            );
            return <li>{processed}</li>;
         },
         strong: ({ children }) => {
            const toArr = Array.isArray(children) ? children : [children];
            const processed = toArr.flatMap((child, i) =>
               typeof child === "string"
                  ? renderWithAreaLinks(
                       child,
                       onFindAndHighlightByName,
                       `strong-${i}`,
                    )
                  : [child],
            );
            return <strong>{processed}</strong>;
         },
      }),
      [onFindAndHighlightByName],
   );

   // 빠른 쿼리 칩
   const areaLabel = mapContext?.dongName
      ? mapContext.dongName.replace(/동$/, "")
      : mapContext?.guName?.replace(/구$/, "") || "";
   const quickChips = mapContext?.dongName
      ? [
           `${areaLabel} 카페 창업 가능성 분석`,
           `${areaLabel} 한식 경쟁 분석`,
           `${areaLabel} 매출 추이 분석`,
           `${areaLabel} 인근 지역 비교`,
        ]
      : [
           "홍대 카페 상권 분석",
           "강남 한식 경쟁 분석",
           "잠실 상권 현황",
           "명동 관광 업종 분석",
           "여의도 음식점 창업 전망",
        ];

   return (
      <>
         {/* 토글 버튼 */}
         <AnimatePresence>
            {!isOpen && (
               <motion.button
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="mv-chat-toggle"
                  onClick={onToggle}
                  title="에이전트와 대화"
               >
                  <div className="mv-chat-toggle__logo">
                     <img src="/sohobi_logo_48w.png" alt="소호비 로고" />
                  </div>
                  <span className="mv-chat-toggle__label">에이전트와 대화</span>
               </motion.button>
            )}
         </AnimatePresence>

         {/* 패널 */}
         <div
            className={`mv-chat-panel ${isOpen ? "" : "mv-chat-panel--closed"} ${dongPanelOpen ? "mv-chat-panel--dong-open" : ""}`}
         >
            {/* 헤더 */}
            <div className="mv-chat-header">
               <div className="mv-chat-header__left">
                  <MessageSquare size={18} />
                  <span>상권분석 AI</span>
               </div>
               <button
                  className="mv-chat-header__close"
                  onClick={onToggle}
                  title="패널 닫기"
               >
                  <X size={18} />
               </button>
            </div>

            {/* 지역 컨텍스트 */}
            {mapContext?.dongName && (
               <div className="mv-chat-context">
                  <span className="mv-chat-context__label">
                     <MapPin size={13} className="mv-chat-context__icon" />
                     {mapContext.guName ? `${mapContext.guName} ` : ""}
                     {mapContext.dongName}
                  </span>
                  <button
                     className="mv-chat-context__clear"
                     onClick={() => onClearContext?.()}
                     title="선택 해제 (다른 지역 자유 입력)"
                  >
                     <X size={12} />
                  </button>
               </div>
            )}

            {/* 메시지 영역 */}
            <div className="mv-chat-messages">
               {messages.length === 0 && (
                  <div className="mv-chat-empty">
                     <div className="mv-chat-empty__icon">
                        <MessageSquare size={28} />
                     </div>
                     <p className="mv-chat-empty__title">
                        상권 분석을 시작하세요
                     </p>
                     <p className="mv-chat-empty__desc">
                        지역과 업종을 입력하면 상권을 분석해드립니다.
                        <br />
                        다른 지역명을 직접 입력하면 해당 지역으로 분석됩니다.
                     </p>
                  </div>
               )}

               {messages.map((msg) => (
                  <div
                     key={msg.id}
                     className={`mv-chat-msg mv-chat-msg--${msg.role}`}
                  >
                     {msg.role === "assistant" ? (
                        <>
                           <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={markdownComponents}
                           >
                              {msg.content}
                           </ReactMarkdown>
                           {msg.suggestedActions?.length > 0 && (
                              <ActionButtons
                                 actions={msg.suggestedActions}
                                 onAction={handleSend}
                                 disabled={loading}
                              />
                           )}
                        </>
                     ) : (
                        msg.content
                     )}
                     {msg.charts && msg.charts.length > 0 && (
                        <div className="mv-chat-charts">
                           {msg.charts.map((b64, idx) => (
                              <img
                                 key={idx}
                                 src={`data:image/png;base64,${b64}`}
                                 alt={`상권 분석 차트 ${idx + 1}`}
                                 className="mv-chat-chart-img"
                                 onClick={() => setEnlargedChart(b64)}
                              />
                           ))}
                        </div>
                     )}
                     {msg.chart && typeof msg.chart === "object" && (
                        <SimulationChart chartData={msg.chart} />
                     )}
                  </div>
               ))}

               {loading && (
                  <div className="mv-chat-loading">
                     {activeEvents.length > 0 ? (
                        <ProgressPanel events={activeEvents} detailed={false} />
                     ) : (
                        <>
                           <div className="mv-chat-dots">
                              <span />
                              <span />
                              <span />
                           </div>
                           <span>분석 준비 중... ({elapsed}초)</span>
                        </>
                     )}
                  </div>
               )}

               <div ref={messagesEndRef} />
            </div>

            {/* 빠른 쿼리 칩 */}
            {!loading && (
               <div
                  className="mv-chat-chips"
                  ref={chipsRef}
                  onMouseDown={(e) => {
                     chipsDragRef.current = {
                        dragging: true,
                        moved: false,
                        startX: e.pageX,
                        scrollLeft: chipsRef.current.scrollLeft,
                     };
                  }}
                  onMouseMove={(e) => {
                     if (!chipsDragRef.current.dragging) return;
                     const dx = e.pageX - chipsDragRef.current.startX;
                     if (Math.abs(dx) > 4) chipsDragRef.current.moved = true;
                     chipsRef.current.scrollLeft =
                        chipsDragRef.current.scrollLeft - dx;
                  }}
                  onMouseUp={() => {
                     chipsDragRef.current.dragging = false;
                  }}
                  onMouseLeave={() => {
                     chipsDragRef.current.dragging = false;
                  }}
               >
                  {quickChips.map((chip) => (
                     <button
                        key={chip}
                        className="mv-chat-chip"
                        onClick={() => {
                           if (!chipsDragRef.current.moved) handleSend(chip);
                           chipsDragRef.current.moved = false;
                        }}
                        disabled={loading}
                     >
                        {chip}
                     </button>
                  ))}
               </div>
            )}

            {/* 입력 영역 */}
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
               <motion.button
                  className="mv-chat-send"
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  whileHover={{ scale: 1.08 }}
                  whileTap={{ scale: 0.92 }}
               >
                  <Send size={18} />
               </motion.button>
            </div>
         </div>

         {/* 차트 확대 오버레이 */}
         <AnimatePresence>
            {enlargedChart && (
               <motion.div
                  className="mv-chat-overlay"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setEnlargedChart(null)}
               >
                  <motion.img
                     src={`data:image/png;base64,${enlargedChart}`}
                     alt="차트 확대"
                     className="mv-chat-overlay__img"
                     initial={{ scale: 0.9 }}
                     animate={{ scale: 1 }}
                     exit={{ scale: 0.9 }}
                  />
               </motion.div>
            )}
         </AnimatePresence>
      </>
   );
}
