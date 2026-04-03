import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { streamQuery } from "../api";
import { interpretError } from "../utils/errorInterpreter";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";
import ProgressPanel from "../components/ProgressPanel";
import { ThemeToggle } from "../components/ThemeToggle";

const DOMAIN_CARDS = [
  {
    id: "admin",
    icon: "📋",
    label: "행정 절차",
    desc: "영업신고·위생교육·사업자등록",
    color: "var(--brand-blue)",
    colorBg: "rgba(8,145,178,0.08)",
    borderColor: "rgba(8,145,178,0.25)",
    questions: [
      "카페 창업 시 영업신고 절차와 필요 서류를 처음부터 알려줘",
      "일반음식점과 휴게음식점의 차이와 신고 방법은?",
    ],
  },
  {
    id: "finance",
    icon: "📊",
    label: "재무 시뮬레이션",
    desc: "수익성·손익분기·투자회수 분석",
    color: "var(--brand-orange)",
    colorBg: "rgba(249,115,22,0.08)",
    borderColor: "rgba(249,115,22,0.25)",
    questions: [
      "월매출 700만원, 재료비 200만원, 직원 1명으로 분식집 창업 시 수익성은?",
      "보증금 5천만원 월세 180만원 카페, 손익분기점 계산해 줘",
    ],
  },
  {
    id: "legal",
    icon: "⚖️",
    label: "법무 정보",
    desc: "임대차·권리금·상가임대차보호법",
    color: "#8b5cf6",
    colorBg: "rgba(139,92,246,0.08)",
    borderColor: "rgba(139,92,246,0.25)",
    questions: [
      "임대차 계약 시 권리금 보호 규정이 있나요?",
      "임대차 3년 후 건물주가 갱신을 거절할 수 있는 경우는?",
    ],
  },
  {
    id: "location",
    icon: "📍",
    label: "상권 분석",
    desc: "서울 2024 Q4 데이터 기반 분석",
    color: "var(--brand-teal)",
    colorBg: "rgba(20,184,166,0.08)",
    borderColor: "rgba(20,184,166,0.25)",
    questions: [
      "홍대 카페 상권 분석해 줘",
      "마포구 치킨집 월평균 매출과 경쟁 현황 알려줘",
    ],
  },
  {
    id: "gov",
    icon: "🎁",
    label: "정부 지원",
    desc: "보조금·창업패키지·대출·신용보증",
    color: "#ec4899",
    colorBg: "rgba(236,72,153,0.08)",
    borderColor: "rgba(236,72,153,0.25)",
    questions: [
      "청년 창업자가 신청할 수 있는 정부 지원금 종류 알려줘",
      "소상공인 정책자금 대출 조건과 금리가 어떻게 되나요?",
    ],
  },
];

const PLACEHOLDER_QUESTIONS = [
  "강남역 근처 카페 창업, 보증금 5천만원 월세 200만원일 때 수익성은?",
  "홍대 분식집 상권 유동인구와 경쟁 현황 분석해 줘",
  "카페 창업 영업신고 절차와 필요 서류를 처음부터 알려줘",
  "임대차 3년 후 갱신 거절당했을 때 권리금 받을 수 있나요?",
  "청년 창업자 정부 지원금 종류와 신청 방법 알려줘",
  "월매출 800만원, 재료비 250만원, 직원 1명인 카페 손익분기점은?",
  "마포구 치킨집 상권, 경쟁업체 현황 포함해서 분석해 줘",
  "사업자등록증 발급 절차와 필요 서류가 뭔가요?",
  "소상공인 정책자금 대출 조건과 금리 알려줘",
  "강남구 한식당 창업 상권 분석, 월매출 예상치 포함해서",
  "식품위생법상 일반음식점 영업신고 요건이 어떻게 되나요?",
  "월세 150만원 분식집, 직원 없이 운영할 때 손실 확률은?",
];

export default function UserChat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [latestParams, setLatestParams] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeEvents, setActiveEvents] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [showBanner, setShowBanner] = useState(() => !localStorage.getItem("sohobi_tip_dismissed"));
  const [placeholder] = useState(
    () => PLACEHOLDER_QUESTIONS[Math.floor(Math.random() * PLACEHOLDER_QUESTIONS.length)]
  );
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function dismissBanner() {
    localStorage.setItem("sohobi_tip_dismissed", "1");
    setShowBanner(false);
  }

  async function handleSubmit(question) {
    setPendingQuestion(question);
    setLoading(true);
    setActiveEvents([]);

    let finalResult = null;

    try {
      await streamQuery(question, 3, sessionId, (eventName, data) => {
        if (eventName === "error") {
          setPendingQuestion(null);
          setMessages(prev => [
            ...prev,
            { question, status: "error", draft: interpretError(data.message || data.error || "") },
          ]);
          return;
        }
        setActiveEvents(prev => [...prev, { event: eventName, ...data }]);
        if (eventName === "domain_classified" && data.session_id) {
          setSessionId(data.session_id);
        }
        if (eventName === "complete") {
          finalResult = data;
        }
      }, latestParams);
    } catch (e) {
      setPendingQuestion(null);
      setMessages(prev => [
        ...prev,
        { question, status: "error", draft: interpretError(e.message) },
      ]);
      setActiveEvents([]);
      setLoading(false);
      inputRef.current?.clear();
      return;
    }

    setPendingQuestion(null);

    if (finalResult) {
      setMessages(prev => [
        ...prev,
        {
          question,
          domain:         finalResult.domain,
          status:         finalResult.status,
          grade:          finalResult.grade,
          confidenceNote: finalResult.confidence_note,
          draft:          finalResult.draft,
          retryCount:     finalResult.retry_count,
          chart:          finalResult.chart || null,
        },
      ]);
      if (finalResult.updated_params) setLatestParams(finalResult.updated_params);
    }

    setActiveEvents([]);
    setLoading(false);
    inputRef.current?.clear();
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 glass border-b border-[var(--border)] px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="text-muted-foreground hover:text-foreground text-sm transition-colors"
        >
          ← 홈
        </button>
        <span className="font-semibold text-foreground">SOHOBI 상담</span>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: "rgba(8,145,178,0.15)", color: "var(--brand-blue)" }}
        >
          사용자
        </span>
        <ThemeToggle />
      </header>

      {/* 대화 영역 */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 && !loading && !pendingQuestion && (
          <div className="mt-6">
            {/* 첫 방문 팁 배너 */}
            {showBanner && (
              <div
                className="mb-6 rounded-2xl px-5 py-4 border text-sm"
                style={{ background: "rgba(8,145,178,0.07)", borderColor: "rgba(8,145,178,0.2)" }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-foreground mb-1">💡 이렇게 질문하면 더 정확해요</div>
                    <p className="text-muted-foreground leading-relaxed">
                      업종·지역·수치를 함께 적어주실수록 정확한 분석을 드립니다.
                      재무 질문은 매출·비용·인건비를, 상권 질문은 동네 이름과 업종을 포함해 보세요.
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground italic">
                      예: "강남 카페, 보증금 5천만원 월세 200만원, 직원 1명일 때 수익성과 손익분기점 알려줘"
                    </p>
                    <button
                      onClick={() => navigate("/features")}
                      className="mt-3 text-xs font-medium underline underline-offset-2"
                      style={{ color: "var(--brand-blue)" }}
                    >
                      SOHOBI 기능 전체 안내 →
                    </button>
                  </div>
                  <button
                    onClick={dismissBanner}
                    className="shrink-0 text-muted-foreground hover:text-foreground text-lg leading-none mt-0.5 transition-colors"
                    aria-label="닫기"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}

            {/* 도메인 카드 그리드 */}
            <div className="text-center mb-5">
              <div className="text-3xl mb-2">💬</div>
              <p className="text-sm text-muted-foreground">무엇이 궁금하신가요? 아래 영역에서 예시 질문을 골라보세요.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {DOMAIN_CARDS.map(card => (
                <div
                  key={card.id}
                  className="rounded-2xl p-4 border"
                  style={{ background: card.colorBg, borderColor: card.borderColor }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xl">{card.icon}</span>
                    <div>
                      <div className="font-semibold text-sm text-foreground">{card.label}</div>
                      <div className="text-xs text-muted-foreground">{card.desc}</div>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {card.questions.map(q => (
                      <button
                        key={q}
                        onClick={() => handleSubmit(q)}
                        className="text-left text-xs px-3 py-2 rounded-xl transition-opacity hover:opacity-70 leading-relaxed"
                        style={{ background: "rgba(255,255,255,0.08)", color: "var(--foreground)" }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {messages.map((msg, i) => (
            <ResponseCard
              key={i}
              question={msg.question}
              domain={msg.domain}
              status={msg.status}
              grade={msg.grade}
              confidenceNote={msg.confidenceNote}
              draft={msg.draft}
              retryCount={msg.retryCount}
              chart={msg.chart}
              displayMode="grade"
            />
          ))}

          {pendingQuestion && (
            <div
              className="self-end max-w-[80%] text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed"
              style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
            >
              {pendingQuestion}
            </div>
          )}

          {loading && (
            <div className="self-start glass rounded-xl px-4 py-3 text-sm w-full max-w-md shadow-elevated">
              <ProgressPanel events={activeEvents} detailed={false} />
              {activeEvents.length === 0 && (
                <div className="flex items-center gap-2 text-muted-foreground text-xs">
                  <span className="inline-block w-3 h-3 border-2 border-[var(--border)] border-t-[var(--brand-blue)] rounded-full animate-spin" />
                  분석 준비 중…
                </div>
              )}
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </main>

      {/* 입력창 */}
      <footer className="sticky bottom-0 bg-background border-t border-[var(--border)] px-4 py-3 max-w-3xl mx-auto w-full">
        <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} placeholder={placeholder} />
      </footer>
    </div>
  );
}
