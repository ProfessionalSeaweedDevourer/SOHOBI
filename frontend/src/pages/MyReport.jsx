import { useState, useEffect } from "react";
import { ThemeToggle } from "../components/ThemeToggle";
import ReportSummary from "../components/report/ReportSummary";
import AgentUsageChart from "../components/report/AgentUsageChart";
import Recommendations from "../components/report/Recommendations";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _HEADERS = {
  "Content-Type": "application/json",
  ...(_API_KEY ? { "X-API-Key": _API_KEY } : {}),
};

const SESSION_KEY = "sohobi_session_id";

async function fetchReport(sessionId) {
  const res = await fetch(`${BASE_URL}/api/report/${sessionId}`, {
    headers: _HEADERS,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

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
    fetchReport(sessionId)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      {/* 헤더 */}
      <header
        className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3 border-b"
        style={{ background: "var(--card)", borderColor: "var(--border)" }}
      >
        <a href="/user" className="text-xl font-bold tracking-tight" style={{ color: "var(--foreground)", textDecoration: "none" }}>
          SOHOBI
        </a>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
          나의 리포트
        </span>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </header>

      {/* 본문 */}
      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-8 flex flex-col gap-6">
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

        {!loading && !sessionId && (
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
              feedback={report.feedback}
              checklist={report.checklist}
            />
            <AgentUsageChart agentUsage={report.agent_usage} />
            <Recommendations incompleteItems={report.checklist?.incomplete_items} />
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
