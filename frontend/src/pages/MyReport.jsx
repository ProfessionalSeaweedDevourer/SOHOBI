import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { trackEvent } from "../utils/trackEvent";
import ReportSummary from "../components/report/ReportSummary";
import AgentUsageChart from "../components/report/AgentUsageChart";
import Recommendations from "../components/report/Recommendations";
import MyPageLayout from "../components/layout/MyPageLayout";
import EmptyStateCTA from "../components/layout/EmptyStateCTA";
import { motion } from "motion/react";
import { BarChart2, ArrowRight, ClipboardList } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _HEADERS = {
  "Content-Type": "application/json",
  ...(_API_KEY ? { "X-API-Key": _API_KEY } : {}),
};

const SESSION_KEY = "sohobi_session_id";

export default function MyReport() {
  const { user, loading: authLoading } = useAuth();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const sessionId = typeof window !== "undefined" ? localStorage.getItem(SESSION_KEY) : null;

  useEffect(() => {
    if (authLoading) return;

    let url, headers;
    if (user?.token) {
      url = `${BASE_URL}/api/report/me`;
      headers = { ..._HEADERS, Authorization: `Bearer ${user.token}` };
    } else if (sessionId) {
      url = `${BASE_URL}/api/report/${sessionId}`;
      headers = _HEADERS;
    } else {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    fetch(url, { headers, signal: controller.signal })
      .then((res) => {
        if (res.status === 403) return null;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setReport(data);
        trackEvent("report_view", { session_id: sessionId });
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [user?.token, sessionId, authLoading]);

  const heroExtra = user && (
    <a
      href="/logs"
      className="text-xs inline-flex items-center gap-1 hover:opacity-80 transition-opacity"
      style={{ color: "var(--brand-blue)", textDecoration: "none" }}
    >
      <ClipboardList size={12} />
      상담 기록 보기
      <ArrowRight size={12} />
    </a>
  );

  return (
    <MyPageLayout
      heroBadge={{ icon: BarChart2, label: "세션 리포트" }}
      heroTitle="나의 창업 준비 현황"
      heroSubtitle={
        user ? "나의 전체 창업 준비 현황을 요약합니다" : "이번 세션의 창업 준비 현황을 요약합니다"
      }
      heroExtra={heroExtra}
    >
      {loading && (
        <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
          리포트를 불러오는 중...
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

      {!loading && !error && !report && (
        <EmptyStateCTA
          icon="📊"
          message="아직 대화 기록이 없습니다."
          actionLabel="AI 에이전트와 대화하기"
          actionHref="/user"
        />
      )}

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
    </MyPageLayout>
  );
}
