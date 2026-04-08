import { useState, useEffect, memo } from "react";
import { ThemeToggle } from "../components/ThemeToggle";
import { useAuth } from "../contexts/AuthContext";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, MessageSquare, ClipboardList, ChevronDown, ArrowRight } from "lucide-react";
import { GlowCTA } from "../components/GlowCTA";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function formatDate(isoString) {
  if (!isoString) return "-";
  const d = new Date(isoString);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

const SessionCard = memo(function SessionCard({ session, token, index }) {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadHistory() {
    if (history !== null) {
      setOpen((v) => !v);
      return;
    }
    setLoading(true);
    try {
      const r = await fetch(
        `${BASE_URL}/api/my/sessions/${session.session_id}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setHistory(await r.json());
      setOpen(true);
    } catch {
      setHistory([]);
      setOpen(true);
    } finally {
      setLoading(false);
    }
  }

  const ctx = session.context || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.05, 0.3) }}
      className="group"
    >
      <div className="glass rounded-2xl shadow-elevated overflow-hidden">
        {/* 카드 헤더 (클릭 영역) */}
        <button
          onClick={loadHistory}
          className="w-full text-left px-5 py-4 flex items-center gap-3 hover:bg-white/5 transition-colors relative"
        >
          <div className="flex-1 min-w-0">
            {/* 배지 row */}
            <div className="flex items-center gap-2 flex-wrap mb-2">
              {ctx.business_type && (
                <span
                  className="text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{ background: "rgba(8,145,178,0.12)", color: "var(--brand-blue)" }}
                >
                  {ctx.business_type}
                </span>
              )}
              {ctx.location_name && (
                <span
                  className="text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{ background: "rgba(20,184,166,0.12)", color: "var(--brand-teal)" }}
                >
                  {ctx.location_name}
                </span>
              )}
              {!ctx.business_type && !ctx.location_name && (
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  업종·지역 미입력
                </span>
              )}
            </div>

            {/* 메타 정보 row */}
            <div className="flex items-center gap-3">
              <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                {formatDate(session.created_at)}
              </span>
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: "rgba(8,145,178,0.08)", color: "var(--brand-blue)" }}
              >
                질문 {session.query_count}건
              </span>
            </div>
          </div>

          {/* 열기/닫기 아이콘 */}
          <motion.div
            animate={{ rotate: open ? 180 : 0 }}
            transition={{ duration: 0.25 }}
            className="shrink-0"
          >
            {loading
              ? <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>...</span>
              : <ChevronDown size={16} style={{ color: "var(--muted-foreground)" }} />
            }
          </motion.div>
        </button>

        {/* 대화 내역 */}
        <AnimatePresence>
          {open && history !== null && (
            <motion.div
              key="session-history"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div
                className="border-t px-5 py-4 flex flex-col gap-3"
                style={{ borderColor: "var(--border)" }}
              >
                {history.length === 0 ? (
                  <div className="flex flex-col items-center py-6 gap-2">
                    <span className="text-2xl">📭</span>
                    <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                      대화 내역이 없습니다.
                    </p>
                  </div>
                ) : (
                  history.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap"
                        style={
                          msg.role === "user"
                            ? {
                                background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))",
                                color: "#fff",
                              }
                            : {
                                background: "var(--muted)",
                                color: "var(--foreground)",
                                border: "1px solid var(--border)",
                              }
                        }
                      >
                        {msg.content}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
});

export default function MyLogs() {
  const { user, login, loading: authLoading } = useAuth();
  const [sessions, setSessions] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user) return;
    setFetching(true);
    fetch(`${BASE_URL}/api/my/sessions`, {
      headers: { Authorization: `Bearer ${user.token}` },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
      .then(setSessions)
      .catch((e) => setError(String(e)))
      .finally(() => setFetching(false));
  }, [user]);

  return (
    <div className="min-h-screen flex flex-col relative">
      <AnimatedBackground />

      {/* 헤더 */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <a
            href="/user"
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
            style={{ textDecoration: "none" }}
          >
            <ArrowLeft size={16} />
            <span className="text-sm">상담으로</span>
          </a>
          <div className="flex items-center gap-2">
            <motion.div
              className="w-8 h-8 bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] rounded-lg flex items-center justify-center shadow-lg"
              whileHover={{ scale: 1.1, rotate: 360 }}
              transition={{ duration: 0.6 }}
            >
              <MessageSquare size={16} className="text-white" />
            </motion.div>
            <span className="gradient-text font-semibold">SOHOBI</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
      </motion.header>

      <main className="relative z-10 flex-1 max-w-2xl w-full mx-auto px-4 py-10 flex flex-col gap-10">

        {/* 히어로 */}
        <div className="flex flex-col items-center text-center gap-4">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm shadow-elevated"
          >
            <ClipboardList size={14} className="text-[var(--brand-blue)]" />
            <span className="text-muted-foreground">질의응답 로그</span>
          </motion.div>

          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="text-3xl font-bold gradient-text"
          >
            상담 기록
          </motion.h1>

          <motion.p
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="text-sm"
            style={{ color: "var(--muted-foreground)" }}
          >
            로그인 후 진행한 창업 상담 기록을 확인합니다
          </motion.p>
        </div>

        {/* 인증 로딩 */}
        {authLoading && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            로딩 중...
          </div>
        )}

        {/* 미로그인 CTA */}
        {!authLoading && !user && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <GlowCTA orbSize="w-40 h-40" className="p-12 text-center shadow-elevated-lg">
              <div className="flex flex-col items-center gap-5">
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg"
                  style={{ backgroundColor: "rgba(8,145,178,0.15)" }}
                >
                  <span className="text-3xl">🔐</span>
                </div>
                <div>
                  <p className="font-semibold mb-1" style={{ color: "var(--foreground)" }}>
                    로그인이 필요합니다
                  </p>
                  <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                    질의응답 로그는 로그인 후 이용할 수 있습니다
                  </p>
                </div>
                <motion.button
                  onClick={login}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-lg hover-glow-blue transition-glow"
                  style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
                >
                  Google로 로그인
                  <ArrowRight size={14} />
                </motion.button>
              </div>
            </GlowCTA>
          </motion.div>
        )}

        {/* 데이터 로딩 */}
        {!authLoading && user && fetching && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            기록을 불러오는 중...
          </div>
        )}

        {/* 에러 */}
        {!authLoading && user && !fetching && error && (
          <div
            className="rounded-2xl border p-4 text-sm"
            style={{
              background: "rgba(239,68,68,0.06)",
              borderColor: "rgba(239,68,68,0.25)",
              color: "var(--foreground)",
            }}
          >
            기록을 불러오지 못했습니다: {error}
          </div>
        )}

        {/* 세션 목록 */}
        {!authLoading && user && !fetching && !error && sessions !== null && (
          sessions.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
            >
              <GlowCTA orbSize="w-32 h-32" className="p-12 text-center shadow-elevated-lg">
                <div className="flex flex-col items-center gap-4">
                  <div
                    className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                    style={{ backgroundColor: "rgba(8,145,178,0.15)" }}
                  >
                    <span className="text-2xl">📭</span>
                  </div>
                  <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                    아직 로그인 상태에서 진행한 상담이 없습니다
                  </p>
                  <a
                    href="/user"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-lg transition-transform hover:scale-105"
                    style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
                  >
                    AI 에이전트와 대화하기
                    <ArrowRight size={14} />
                  </a>
                </div>
              </GlowCTA>
            </motion.div>
          ) : (
            <div className="flex flex-col gap-3">
              {sessions.map((s, i) => (
                <SessionCard key={s.session_id} session={s} token={user.token} index={i} />
              ))}
            </div>
          )
        )}
      </main>
    </div>
  );
}
