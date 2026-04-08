import { useState, useEffect } from "react";
import { trackEvent } from "../utils/trackEvent";
import { ThemeToggle } from "../components/ThemeToggle";
import ReportSummary from "../components/report/ReportSummary";
import AgentUsageChart from "../components/report/AgentUsageChart";
import Recommendations from "../components/report/Recommendations";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { motion } from "motion/react";
import { ArrowLeft, MessageSquare } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _HEADERS = {
  "Content-Type": "application/json",
  ...(_API_KEY ? { "X-API-Key": _API_KEY } : {}),
};

const SESSION_KEY = "sohobi_session_id";


export default function MyReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const sessionId =
    typeof window !== "undefined"
      ? localStorage.getItem(SESSION_KEY)
      : null;

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    fetch(`${BASE_URL}/api/report/${sessionId}`, { headers: _HEADERS, signal: controller.signal })
      .then((res) => {
        if (res.status === 403) return null;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setReport(data);
        trackEvent("report_view", { session_id: sessionId });
      })
      .catch((e) => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [sessionId]);

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

      {/* 본문 */}
      <main className="relative z-10 flex-1 max-w-2xl w-full mx-auto px-4 py-8 flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>
            사용 리포트
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>
            이번 세션의 창업 준비 현황을 요약합니다
          </p>
        </div>

        {loading && (
          <div
            className="text-sm text-center py-12"
            style={{ color: "var(--muted-foreground)" }}
          >
            리포트를 불러오는 중...
          </div>
        )}

        {!loading && !error && !report && (
          <div
            className="rounded-2xl border p-6 text-center"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="text-2xl mb-3">📊</div>
            <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
              아직 대화 기록이 없습니다.{" "}
              <a href="/user" style={{ color: "var(--brand-blue, #0891b2)" }}>
                AI 에이전트
              </a>
              와 대화를 시작해 보세요.
            </p>
          </div>
        )}

        {!loading && error && (
          <div
            className="rounded-2xl border p-4 text-sm"
            style={{
              background: "rgba(239,68,68,0.06)",
              borderColor: "rgba(239,68,68,0.25)",
              color: "var(--foreground)",
            }}
          >
            리포트를 불러오지 못했습니다: {error}
          </div>
        )}

        {!loading && !error && report && (
          <>
            <ReportSummary
              totalQueries={report.total_queries}
              mostUsedAgent={report.most_used_agent}
              feedback={report.feedback}
              checklist={report.checklist}
              firstActive={report.first_active}
              lastActive={report.last_active}
            />
            <AgentUsageChart agentUsage={report.agent_usage} />
            <Recommendations
              incompleteItems={report.checklist?.incomplete_items}
              sessionId={sessionId}
            />
          </>
        )}

        {!loading && (
          <p className="text-xs text-center mt-2" style={{ color: "var(--muted-foreground)" }}>
            <a href="/roadmap" style={{ color: "var(--brand-blue, #0891b2)" }}>
              🗳️ 다음에 추가할 기능 투표하기
            </a>
          </p>
        )}
      </main>
    </div>
  );
}
