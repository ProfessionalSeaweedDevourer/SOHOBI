import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { trackEvent } from "../utils/trackEvent";
import ChatInput from "../components/ChatInput";
import LoginNudgeCard from "../components/LoginNudgeCard";
import ResponseCard from "../components/ResponseCard";
import ProgressPanel from "../components/ProgressPanel";
import { ThemeToggle } from "../components/ThemeToggle";
import StartupChecklist from "../components/checklist/StartupChecklist";
import ChecklistProgress from "../components/checklist/ChecklistProgress";
import ChecklistDrawer from "../components/checklist/ChecklistDrawer";
import { useChecklistState } from "../components/checklist/useChecklistState";
import { useChatMessages } from "../hooks/chat/useChatMessages";
import { useStreamQuery } from "../hooks/chat/useStreamQuery";
import { BASE_URL } from "../api";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, MessageSquare, Menu, X } from "lucide-react";

const DOMAIN_CARDS = [
  {
    id: "admin",
    icon: "📋",
    label: "행정 절차",
    desc: "영업신고·위생교육·사업자등록",
    color: "var(--brand-blue)",
    colorHex: "#0891b2",
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
    colorHex: "#f97316",
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
    colorHex: "#8b5cf6",
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
    desc: "서울 2025 Q4 데이터 기반 분석",
    color: "var(--brand-teal)",
    colorHex: "#14b8a6",
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
    colorHex: "#ec4899",
    colorBg: "rgba(236,72,153,0.08)",
    borderColor: "rgba(236,72,153,0.25)",
    questions: [
      "청년 창업자가 신청할 수 있는 정부 지원금 종류 알려줘",
      "소상공인 정책자금 대출 조건과 금리가 어떻게 되나요?",
    ],
  },
];

const PLACEHOLDER_QUESTIONS = [
  "카페 창업 전 구청에 가기 전에 미리 확인해야 할 행정 절차가 뭔가요?",
  "사업자등록증 발급, 어디서 어떻게 신청하나요?",
  "월매출 700만원, 재료비 200만원, 직원 1명 월급 250만원으로 분식집 수익성은?",
  "보증금 5천만원 월세 180만원 카페, 손익분기점이 어떻게 되나요?",
  "임대차 계약 시 권리금 보호 규정이 어떻게 되나요?",
  "건물주가 3년 계약 만료 후 갱신을 거절할 수 있는 경우가 있나요?",
  "홍대 카페 상권 분석해 줘, 유동인구랑 경쟁 현황 포함해서",
  "청년 창업자가 신청할 수 있는 정부 지원금과 대출 종류를 알려줘",
  "소상공인 정책자금 대출 신청 조건과 현재 금리가 어떻게 되나요?",
  "강남역 vs 신촌, 분식집 창업 입지로 어디가 더 유리한가요?",
];

function getSlowMessage(elapsed) {
  if (elapsed >= 30) return "거의 다 됐어요, 조금만 더 기다려 주세요 🙏";
  if (elapsed >= 20) return "복잡한 내용을 꼼꼼히 검토하고 있어요…";
  if (elapsed >= 10) return "더 좋은 답변을 위해 조금 더 생각하는 중이에요…";
  return null;
}

export default function UserChat() {
  const navigate = useNavigate();
  const { user, login, logout } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [showBanner, setShowBanner] = useState(() => !localStorage.getItem("sohobi_tip_dismissed"));
  const [showSamples, setShowSamples] = useState(false);
  const [showLoginNudge, setShowLoginNudge] = useState(
    () => !user && !localStorage.getItem("sohobi_login_nudge_dismissed")
  );
  const [placeholder] = useState(
    () => PLACEHOLDER_QUESTIONS[Math.floor(Math.random() * PLACEHOLDER_QUESTIONS.length)]
  );
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);
  const [loadingElapsed, setLoadingElapsed] = useState(0);
  const [checklistDrawerOpen, setChecklistDrawerOpen] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const userMenuRef = useRef(null);
  const navRef = useRef(null);

  const {
    messages, sessionId, setSessionId, latestParams, setLatestParams,
    addMessage, updateAt, restoreFromApi,
  } = useChatMessages();
  const layer2Fetched = useRef(false);

  const { items: checklistItems, progress: checklistProgress, toggleItem, syncFromDraft } = useChecklistState(sessionId, messages.length > 0);

  const handleSessionId = useCallback((id) => {
    setSessionId(id);
    localStorage.setItem("sohobi_session_id", id);
  }, [setSessionId]);

  const { loading, activeEvents, pendingQuestion, submit, regenerate } = useStreamQuery({
    sessionId,
    latestParams,
    onMessage: addMessage,
    onUpdateAt: updateAt,
    onSessionId: handleSessionId,
    onParams: setLatestParams,
    onCheckedItems: syncFromDraft,
  });

  useEffect(() => {
    if (!userMenuOpen && !navOpen) return;
    function handleClickOutside(e) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
      if (navRef.current && !navRef.current.contains(e.target)) {
        setNavOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [userMenuOpen, navOpen]);

  useEffect(() => {
    if (!loading) { setLoadingElapsed(0); return; }
    const interval = setInterval(() => setLoadingElapsed(s => s + 1), 1000);
    return () => clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    trackEvent("feature_discovery", { page: "user_chat" });
  }, []);

  // Layer 2: 백엔드에서 메시지 복원 (로그인 사용자, sessionStorage 비어있을 때)
  useEffect(() => {
    if (messages.length > 0 || !user || !sessionId) return;
    if (layer2Fetched.current) return;
    const token = localStorage.getItem("sohobi_jwt");
    if (!token) return;

    layer2Fetched.current = true;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${BASE_URL}/api/my/sessions/${sessionId}/history?include_messages=true`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (!cancelled && data.messages?.length) {
          restoreFromApi(data.messages);
        }
      } catch {
        // 네트워크 오류 — 빈 상태로 fallback
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, sessionId]);  // user 비동기 로드 완료 시 재평가

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function handleSubmit(question) {
    trackEvent("agent_query", { session_id: sessionId, page: "user_chat" });
    submit(question, inputRef);
  }

  function handleRegenerate(index) {
    if (loading) return;
    setRegeneratingIndex(index);
    regenerate(index, messages[index].question).finally(() => setRegeneratingIndex(null));
  }

  function handleSuggestedAction(value, messageIndex) {
    updateAt(messageIndex, { suggestedActions: [], isPartial: false });
    handleSubmit(value);
  }

  const slowMsg = getSlowMessage(loadingElapsed);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* 헤더 */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          {/* Left: 홈 + 로고 */}
          <div className="flex items-center gap-2">
            <motion.button
              onClick={() => navigate("/")}
              whileHover={{ x: -2 }}
              className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft size={16} />
              <span className="text-sm">홈</span>
            </motion.button>
            <div className="w-px h-4 mx-1" style={{ background: "var(--border)" }} />
            <div className="flex items-center gap-2">
              <motion.div
                className="w-8 h-8 bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] rounded-lg flex items-center justify-center shadow-lg"
                whileHover={{ scale: 1.1, rotate: 360 }}
                transition={{ duration: 0.6 }}
              >
                <MessageSquare size={16} className="text-white" />
              </motion.div>
              <span className="gradient-text font-semibold text-sm">SOHOBI 상담</span>
            </div>
          </div>

          {/* Right: 액션 */}
          <div className="flex items-center gap-2">
            <ThemeToggle />

            {/* 유저 아바타 / 로그인 버튼 */}
            {user ? (
              <div className="relative" ref={userMenuRef}>
                <motion.button
                  onClick={() => setUserMenuOpen((v) => !v)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] flex items-center justify-center text-white text-xs font-bold shadow-lg"
                  title={user.email}
                >
                  {(user.name || user.email || "?")[0].toUpperCase()}
                </motion.button>
                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-2 rounded-2xl border shadow-elevated z-50 overflow-hidden min-w-[9rem]" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                    <div className="px-3 py-2 text-xs border-b truncate" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>{user.email}</div>
                    <button onClick={() => { setUserMenuOpen(false); logout(); }} className="w-full text-left px-3 py-2 text-xs transition-colors hover:bg-[var(--muted)]" style={{ color: "var(--foreground)" }}>로그아웃</button>
                  </div>
                )}
              </div>
            ) : (
              <motion.button
                onClick={login}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors px-1"
              >
                로그인
              </motion.button>
            )}

            {/* 햄버거 메뉴 */}
            <div className="relative" ref={navRef}>
              <motion.button
                onClick={() => setNavOpen((v) => !v)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-9 h-9 flex items-center justify-center rounded-lg glass hover:bg-white/10 transition-all"
                aria-label="메뉴"
              >
                {navOpen ? <X size={18} /> : <Menu size={18} />}
              </motion.button>
              {navOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-full mt-2 rounded-2xl border shadow-elevated z-50 overflow-hidden min-w-[11rem]"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  {[
                    { href: "/map", icon: "🗺️", label: "지도·상권분석" },
                    { href: "/features", icon: "✨", label: "기능 안내" },
                    { href: "/my-report", icon: "📊", label: "내 리포트" },
                    { href: "/roadmap", icon: "🗳️", label: "로드맵" },
                    ...(user ? [{ href: "/my-logs", icon: "📋", label: "내 로그" }] : []),
                  ].map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      onClick={() => setNavOpen(false)}
                      className="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors hover:bg-[var(--muted)]"
                      style={{ color: "var(--foreground)", textDecoration: "none" }}
                    >
                      <span>{item.icon}</span>
                      {item.label}
                    </a>
                  ))}
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </motion.header>

      {/* 대화 영역 + 사이드패널 */}
      <div className="flex-1 flex overflow-hidden max-w-5xl mx-auto w-full">
        <main className="flex-1 overflow-y-auto px-4 py-6 min-w-0">

          {/* 빈 상태: 온보딩 */}
          {messages.length === 0 && !loading && !pendingQuestion && (
            <div className="mt-6">
              {showBanner && (
                <div className="mb-6 rounded-2xl px-5 py-4 border text-sm" style={{ background: "rgba(8,145,178,0.07)", borderColor: "rgba(8,145,178,0.2)" }}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-foreground mb-1">💡 이렇게 질문하면 더 정확해요</div>
                      <p className="text-muted-foreground leading-relaxed">업종·지역·수치를 함께 적어주실수록 정확한 분석을 드립니다. 재무 질문은 매출·비용·인건비를, 상권 질문은 동네 이름과 업종을 포함해 보세요.</p>
                      <p className="mt-2 text-xs text-muted-foreground italic">예: "강남 카페, 보증금 5천만원 월세 200만원, 직원 1명일 때 수익성과 손익분기점 알려줘"</p>
                      <button onClick={() => navigate("/features")} className="mt-3 text-xs font-medium underline underline-offset-2" style={{ color: "var(--brand-blue)" }}>SOHOBI 기능 전체 안내 →</button>
                    </div>
                    <button onClick={() => { localStorage.setItem("sohobi_tip_dismissed", "1"); setShowBanner(false); }} className="shrink-0 text-muted-foreground hover:text-foreground text-lg leading-none mt-0.5 transition-colors" aria-label="닫기">✕</button>
                  </div>
                </div>
              )}
              <div className="text-center mb-5">
                <div className="text-3xl mb-2">💬</div>
                <p className="text-sm text-muted-foreground">무엇이 궁금하신가요? 아래 영역에서 예시 질문을 골라보세요.</p>
              </div>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 sm:grid-cols-2 gap-3"
              >
                {DOMAIN_CARDS.map((card, idx) => (
                  <motion.div
                    key={card.id}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: idx * 0.08 }}
                    whileHover={{ y: -4, boxShadow: `0 0 24px ${card.colorHex}50` }}
                    className="group glass-card rounded-2xl p-5 shadow-elevated transition-glow relative overflow-hidden"
                  >
                    {/* Gradient overlay on hover */}
                    <div
                      className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-2xl pointer-events-none"
                      style={{ background: `linear-gradient(135deg, ${card.colorHex}40, transparent)` }}
                    />
                    <div className="relative z-10">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="relative w-10 h-10 flex items-center justify-center shrink-0">
                          <div className="absolute inset-0 rounded-xl blur-lg opacity-25" style={{ backgroundColor: card.colorHex }} />
                          <span className="text-xl relative z-10">{card.icon}</span>
                        </div>
                        <div>
                          <div className="font-semibold text-sm text-foreground">{card.label}</div>
                          <div className="text-xs text-muted-foreground">{card.desc}</div>
                        </div>
                      </div>
                      <div className="flex flex-col gap-1.5">
                        {card.questions.map(q => (
                          <motion.button
                            key={q}
                            onClick={() => handleSubmit(q)}
                            whileHover={{ scale: 1.01, x: 3 }}
                            whileTap={{ scale: 0.98 }}
                            className="text-left text-xs px-3 py-2 rounded-xl leading-relaxed border-l-2 border-transparent transition-colors duration-200 hover:shadow-sm"
                            style={{ background: "var(--glass-bg)", color: "var(--foreground)", borderLeftColor: "transparent" }}
                            onMouseEnter={(e) => { e.currentTarget.style.borderLeftColor = card.colorHex; e.currentTarget.style.background = `${card.colorHex}12`; }}
                            onMouseLeave={(e) => { e.currentTarget.style.borderLeftColor = "transparent"; e.currentTarget.style.background = "var(--glass-bg)"; }}
                          >
                            {q}
                          </motion.button>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          )}

          {/* 메시지 목록 */}
          <div className="flex flex-col gap-6">
            {messages.map((msg, i) => (
              <div key={i} className="flex flex-col gap-4">
                <ResponseCard
                  question={msg.question}
                  domain={msg.domain}
                  status={msg.status}
                  grade={msg.grade}
                  confidenceNote={msg.confidenceNote}
                  draft={msg.draft}
                  retryCount={msg.retryCount}
                  chart={msg.chart}
                  charts={msg.charts || []}
                  displayMode="full"
                  sessionId={msg.sessionId}
                  messageId={msg.requestId}
                  onRegenerate={() => handleRegenerate(i)}
                  regenerated={!!msg.regenerated}
                  isLoading={loading}
                  suggestedActions={msg.suggestedActions || []}
                  onSuggestedAction={(value) => handleSuggestedAction(value, i)}
                  actionsDisabled={loading}
                />

                {/* 로그인 넛지 */}
                {i === 0 && !user && showLoginNudge && (
                  <LoginNudgeCard
                    onLogin={login}
                    onDismiss={() => {
                      localStorage.setItem("sohobi_login_nudge_dismissed", "1");
                      setShowLoginNudge(false);
                    }}
                  />
                )}
              </div>
            ))}

            {pendingQuestion && (
              <div className="self-end max-w-[80%] text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed" style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}>
                {pendingQuestion}
              </div>
            )}

            {loading && (
              <div className="glass rounded-xl px-4 py-3 shadow-elevated self-start max-w-md">
                <ProgressPanel events={activeEvents} />
                {activeEvents.length === 0 && (
                  <div className="flex items-center gap-2 text-muted-foreground text-xs">
                    <span className="inline-block w-3 h-3 border-2 border-[var(--border)] border-t-[var(--brand-blue)] rounded-full animate-spin" />
                    분석 준비 중…
                  </div>
                )}
                {slowMsg && (
                  <motion.div
                    key={slowMsg}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-2 text-xs text-muted-foreground italic"
                  >
                    {slowMsg}
                  </motion.div>
                )}
              </div>
            )}
          </div>

          <div ref={bottomRef} />
        </main>

        {/* 체크리스트 사이드패널 (데스크톱 전용) */}
        <aside className="hidden lg:block w-64 shrink-0 border-l border-[var(--border)] px-3 py-4 overflow-y-auto">
          <StartupChecklist items={checklistItems} progress={checklistProgress} onToggle={toggleItem} onAskQuestion={handleSubmit} />
        </aside>
      </div>

      {/* 입력창 */}
      <footer className="sticky bottom-0 bg-background border-t border-[var(--border)] max-w-5xl mx-auto w-full">
        <div className="lg:hidden border-b border-[var(--border)] px-4 py-2">
          <ChecklistProgress progress={checklistProgress} total={8} onClick={() => setChecklistDrawerOpen(true)} />
        </div>

        <AnimatePresence>
          {checklistDrawerOpen && (
            <ChecklistDrawer
              items={checklistItems}
              progress={checklistProgress}
              onToggle={toggleItem}
              onAskQuestion={(q) => { setChecklistDrawerOpen(false); handleSubmit(q); }}
              onClose={() => setChecklistDrawerOpen(false)}
            />
          )}
        </AnimatePresence>

        {showSamples && (
          <div className="border-b border-[var(--border)] px-4 py-3 max-h-72 overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DOMAIN_CARDS.map((card, idx) => (
                <motion.div
                  key={card.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: idx * 0.05 }}
                  whileHover={{ y: -2, boxShadow: `0 0 16px ${card.colorHex}40` }}
                  className="group glass-card rounded-xl p-3 shadow-elevated transition-glow relative overflow-hidden"
                >
                  <div
                    className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-xl pointer-events-none"
                    style={{ background: `linear-gradient(135deg, ${card.colorHex}40, transparent)` }}
                  />
                  <div className="relative z-10">
                    <div className="flex items-center gap-1.5 mb-2">
                      <span className="text-base">{card.icon}</span>
                      <span className="font-semibold text-xs text-foreground">{card.label}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      {card.questions.map(q => (
                        <motion.button
                          key={q}
                          onClick={() => { setShowSamples(false); handleSubmit(q); }}
                          whileHover={{ scale: 1.01, x: 2 }}
                          whileTap={{ scale: 0.98 }}
                          className="text-left text-xs px-2.5 py-1.5 rounded-lg leading-relaxed border-l-2 border-transparent transition-colors duration-200"
                          style={{ background: "var(--glass-bg)", color: "var(--foreground)", borderLeftColor: "transparent" }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderLeftColor = card.colorHex; e.currentTarget.style.background = `${card.colorHex}12`; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderLeftColor = "transparent"; e.currentTarget.style.background = "var(--glass-bg)"; }}
                        >
                          {q}
                        </motion.button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        <div className="px-4 py-3 flex flex-col gap-2">
          <button
            onClick={() => setShowSamples(v => !v)}
            className="self-start text-xs px-3 py-1.5 rounded-full border transition-colors"
            style={{
              borderColor: showSamples ? "var(--brand-blue)" : "var(--border)",
              color: showSamples ? "var(--brand-blue)" : "var(--muted-foreground)",
              background: showSamples ? "rgba(8,145,178,0.08)" : "transparent",
            }}
          >
            {showSamples ? "▲ 샘플 질문 닫기" : "💬 샘플 질문 보기"}
          </button>
          <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} defaultValue={placeholder} />
        </div>
      </footer>
    </div>
  );
}
