import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchLogs } from "../api";
import LogTable from "../components/LogTable";

const TABS = [
  { key: "queries", label: "전체 요청" },
  { key: "rejections", label: "거부 이력" },
];

export default function LogViewer() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("queries");
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetched, setLastFetched] = useState(null);

  async function load(type) {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLogs(type, 100);
      setEntries(data.entries || []);
      setLastFetched(new Date().toLocaleTimeString("ko-KR"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(tab);
  }, [tab]);

  // 통계
  const total = entries.length;
  const approved = entries.filter((e) => e.status === "approved").length;
  const escalated = total - approved;
  const avgLatency =
    total > 0
      ? Math.round(entries.reduce((s, e) => s + (e.latency_ms || 0), 0) / total)
      : 0;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/dev")}
          className="text-slate-400 hover:text-slate-700 text-sm"
        >
          ← 개발자
        </button>
        <span className="font-semibold text-slate-800">로그 뷰어</span>
        <span className="ml-auto text-xs text-slate-400">
          {lastFetched ? `마지막 갱신: ${lastFetched}` : ""}
        </span>
        <button
          onClick={() => load(tab)}
          disabled={loading}
          className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-100 disabled:opacity-40 transition-colors"
        >
          새로고침
        </button>
      </header>

      {/* 통계 바 */}
      {total > 0 && (
        <div className="bg-white border-b border-slate-100 px-4 py-2 flex gap-6 text-xs text-slate-600 overflow-x-auto">
          <span>전체 <strong className="text-slate-800">{total}</strong>건</span>
          <span>
            ✅ approved <strong className="text-green-700">{approved}</strong>
            {total > 0 && <span className="text-slate-400"> ({Math.round((approved / total) * 100)}%)</span>}
          </span>
          <span>
            ❌ escalated <strong className="text-red-600">{escalated}</strong>
          </span>
          <span>평균 응답 <strong className="text-slate-800">{avgLatency.toLocaleString()}ms</strong></span>
        </div>
      )}

      {/* 탭 */}
      <div className="bg-white border-b border-slate-100 px-4 flex gap-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`
              px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
              ${tab === t.key
                ? "border-violet-500 text-violet-700"
                : "border-transparent text-slate-400 hover:text-slate-600"}
            `}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 컨텐츠 */}
      <main className="flex-1 overflow-hidden px-4 py-4 max-w-6xl mx-auto w-full">
        {error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 mt-4">
            {tab === "rejections" && error.includes("없거나")
              ? "거부 이력 로그 파일이 없습니다. 에이전트 테스트 후 재시도하세요."
              : `오류: ${error}`}
          </div>
        ) : (
          <div className="h-[calc(100vh-180px)]">
            <LogTable entries={entries} loading={loading} />
          </div>
        )}
      </main>
    </div>
  );
}
