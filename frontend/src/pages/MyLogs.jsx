import { useState, useEffect, memo } from "react";
import LoadingSpinner from "../components/LoadingSpinner";
import { useAuth } from "../contexts/AuthContext";
import MyPageLayout from "../components/layout/MyPageLayout";
import EmptyStateCTA from "../components/layout/EmptyStateCTA";
import { motion, AnimatePresence } from "motion/react";
import { ClipboardList, ChevronDown, ArrowRight, BarChart2 } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function formatDate(isoString) {
  if (!isoString) return "-";
  const d = new Date(isoString);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

const SessionCard = memo(function SessionCard({ session, token, index }) {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState(false);
  const [loading, setLoading] = useState(false);

  async function loadHistory() {
    if (history !== null || historyError) {
      setOpen((v) => !v);
      return;
    }
    setLoading(true);
    try {
      const r = await fetch(`${BASE_URL}/api/my/sessions/${session.session_id}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setHistory(await r.json());
      setOpen(true);
    } catch {
      setHistoryError(true);
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
        <button
          onClick={loadHistory}
          className="w-full text-left px-5 py-4 flex items-center gap-3 hover:bg-white/5 transition-colors relative"
        >
          <div className="flex-1 min-w-0">
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

          <motion.div
            animate={{ rotate: open ? 180 : 0 }}
            transition={{ duration: 0.25 }}
            className="shrink-0"
          >
            {loading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <ChevronDown size={16} style={{ color: "var(--muted-foreground)" }} />
            )}
          </motion.div>
        </button>

        <AnimatePresence>
          {open && (history !== null || historyError) && (
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
                {historyError ? (
                  <p
                    className="text-sm text-center py-4"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    기록을 불러오지 못했습니다.
                  </p>
                ) : history.length === 0 ? (
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
                                background:
                                  "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))",
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

  const heroExtra = user && (
    <a
      href="/report"
      className="text-xs inline-flex items-center gap-1 hover:opacity-80 transition-opacity"
      style={{ color: "var(--brand-blue)", textDecoration: "none" }}
    >
      <BarChart2 size={12} />
      요약 리포트 보기
      <ArrowRight size={12} />
    </a>
  );

  return (
    <MyPageLayout
      heroBadge={{ icon: ClipboardList, label: "질의응답 로그" }}
      heroTitle="상담 기록"
      heroSubtitle="로그인 후 진행한 창업 상담 기록을 확인합니다"
      heroExtra={heroExtra}
      mainGap="gap-10"
    >
      {authLoading && (
        <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
          로딩 중...
        </div>
      )}

      {!authLoading && !user && (
        <EmptyStateCTA
          icon="🔐"
          title="로그인이 필요합니다"
          message="질의응답 로그는 로그인 후 이용할 수 있습니다"
          actionLabel="Google로 로그인"
          onAction={login}
        />
      )}

      {!authLoading && user && fetching && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="md" />
        </div>
      )}

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

      {!authLoading &&
        user &&
        !fetching &&
        !error &&
        sessions !== null &&
        (sessions.length === 0 ? (
          <EmptyStateCTA
            icon="📭"
            message="아직 로그인 상태에서 진행한 상담이 없습니다"
            actionLabel="AI 에이전트와 대화하기"
            actionHref="/user"
            orbSize="w-32 h-32"
            iconSize="w-14 h-14"
            emojiSize="text-2xl"
          />
        ) : (
          <div className="flex flex-col gap-3">
            {sessions.map((s, i) => (
              <SessionCard key={s.session_id} session={s} token={user.token} index={i} />
            ))}
          </div>
        ))}
    </MyPageLayout>
  );
}
