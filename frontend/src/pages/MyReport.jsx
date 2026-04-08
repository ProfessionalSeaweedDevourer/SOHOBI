import { useState, useEffect } from "react";
import { trackEvent } from "../utils/trackEvent";
import { ThemeToggle } from "../components/ThemeToggle";
import ReportSummary from "../components/report/ReportSummary";
import AgentUsageChart from "../components/report/AgentUsageChart";
import Recommendations from "../components/report/Recommendations";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowCTA } from "../components/GlowCTA";
import { motion } from "motion/react";
import { ArrowLeft, MessageSquare, BarChart2, ArrowRight } from "lucide-react";

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
      <main className="relative z-10 flex-1 max-w-2xl w-full mx-auto px-4 py-10 flex flex-col gap-8">

        {/* 히어로 */}
        <div className="flex flex-col items-center text-center gap-4">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm shadow-elevated"
          >
            <BarChart2 size={14} className="text-[var(--brand-blue)]" />
            <span className="text-muted-foreground">세션 리포트</span>
          </motion.div>

          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="text-3xl font-bold gradient-text"
          >
            나의 창업 준비 현황
          </motion.h1>

          <motion.p
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="text-sm"
            style={{ color: "var(--muted-foreground)" }}
          >
            이번 세션의 창업 준비 현황을 요약합니다
          </motion.p>
        </div>

        {/* 로딩 */}
        {loading && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            리포트를 불러오는 중...
          </div>
        )}

        {/* 에러 */}
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

        {/* 빈 상태 */}
        {!loading && !error && !report && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <GlowCTA orbSize="w-40 h-40" className="p-12 text-center shadow-elevated-lg">
              <div className="flex flex-col items-center gap-4">
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg"
                  style={{ backgroundColor: "rgba(8,145,178,0.15)" }}
                >
                  <span className="text-3xl">📊</span>
                </div>
                <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  아직 대화 기록이 없습니다.
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
        )}

        {/* 리포트 콘텐츠 */}
        {!loading && !error && report && (
          <>
            <ReportSummary
              totalQueries={report.total_queries}
              mostUsedAgent={report.most_used_agent}
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

        {/* 로드맵 CTA */}
        {!loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <a
              href="/roadmap"
              className="group block glass rounded-2xl px-6 py-5 shadow-elevated relative overflow-hidden transition-all hover:shadow-elevated-lg"
              style={{ textDecoration: "none" }}
            >
              <div
                className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 rounded-2xl"
                style={{ backgroundColor: "var(--brand-blue)" }}
              />
              <div className="relative z-10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{ backgroundColor: "rgba(8,145,178,0.12)" }}
                  >
                    <span className="text-lg">🗳️</span>
                  </div>
                  <div>
                    <p className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                      다음 기능 투표하기
                    </p>
                    <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                      원하는 기능에 투표해 개발 우선순위를 결정하세요
                    </p>
                  </div>
                </div>
                <ArrowRight
                  size={16}
                  className="shrink-0 opacity-40 group-hover:opacity-80 transition-opacity"
                  style={{ color: "var(--brand-blue)" }}
                />
              </div>
            </a>
          </motion.div>
        )}
      </main>
    </div>
  );
}
