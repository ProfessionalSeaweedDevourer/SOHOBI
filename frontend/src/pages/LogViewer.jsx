import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { fetchLogs, fetchFeedback, fetchRoadmapVotes, fetchLogUsers } from "../api";
import LogTable from "../components/LogTable";
import ErrorTable from "../components/ErrorTable";
import { ThemeToggle } from "../components/ThemeToggle";

const TABS = [
  { key: "queries", label: "전체 요청" },
  { key: "rejections", label: "거부 이력" },
  { key: "errors", label: "응답 오류" },
  { key: "roadmap", label: "투표 집계" },
];

function resolveGrade(entry) {
  if (entry.grade && ["A", "B", "C"].includes(entry.grade)) return entry.grade;
  return entry.status === "approved" ? "A" : "C";
}

export default function LogViewer() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("queries");
  const [entries, setEntries] = useState([]);
  const [feedbackMap, setFeedbackMap] = useState(new Map());
  const [roadmapFeatures, setRoadmapFeatures] = useState([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetched, setLastFetched] = useState(null);
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [sessionFilter, setSessionFilter] = useState("");
  const feedbackCacheRef = useRef(null);

  async function load(type, userFilter) {
    setLoading(true);
    setError(null);
    try {
      const fbPromise = feedbackCacheRef.current
        ? Promise.resolve(feedbackCacheRef.current)
        : fetchFeedback().then((r) => {
            feedbackCacheRef.current = r;
            return r;
          });
      const [data, fb] = await Promise.allSettled([
        fetchLogs(type, 500, userFilter ?? selectedUser),
        fbPromise,
      ]);
      setEntries(data.status === "fulfilled" ? data.value.entries || [] : []);
      if (data.status === "rejected") throw new Error(data.reason?.message);
      if (fb.status === "fulfilled") {
        setFeedbackMap(new Map((fb.value.items || []).map((f) => [f.message_id, f])));
      }
      setLastFetched(new Date().toLocaleTimeString("ko-KR"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadRoadmap() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRoadmapVotes();
      setRoadmapFeatures(data.features || []);
      setLastFetched(new Date().toLocaleTimeString("ko-KR"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload() {
    setDownloading(true);
    try {
      const data = await fetchLogs(tab, 0);
      const blob = new Blob([JSON.stringify(data.entries, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sohobi-logs-${tab}-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`다운로드 실패: ${e.message}`);
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    fetchLogUsers()
      .then((data) => setUsers(data.users || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "roadmap") {
      loadRoadmap();
    } else {
      load(tab);
    }
  }, [tab, selectedUser]);

  const isRoadmapTab = tab === "roadmap";
  const isErrorTab = tab === "errors";

  const displayEntries = entries.filter(
    (e) => !sessionFilter || e.session_id?.includes(sessionFilter),
  );

  const total = displayEntries.length;
  const gradeA = displayEntries.filter((e) => resolveGrade(e) === "A").length;
  const gradeB = displayEntries.filter((e) => resolveGrade(e) === "B").length;
  const gradeC = displayEntries.filter((e) => resolveGrade(e) === "C").length;
  const avgLatency =
    total > 0 ? Math.round(displayEntries.reduce((s, e) => s + (e.latency_ms || 0), 0) / total) : 0;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 glass border-b border-[var(--border)] px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/dev")}
          className="text-muted-foreground hover:text-foreground text-sm transition-colors"
        >
          ← 개발자
        </button>
        <span className="font-semibold text-foreground">로그 뷰어</span>
        <span className="ml-auto text-xs text-muted-foreground">
          {lastFetched ? `마지막 갱신: ${lastFetched}` : ""}
        </span>
        <ThemeToggle />
        {!isRoadmapTab && (
          <button
            onClick={handleDownload}
            disabled={downloading || loading}
            className="text-xs glass rounded-lg px-3 py-1.5 hover:shadow-elevated transition-glow disabled:opacity-40 text-foreground"
          >
            {downloading ? "다운로드 중…" : "전체 다운로드"}
          </button>
        )}
        <button
          onClick={() => (isRoadmapTab ? loadRoadmap() : load(tab))}
          disabled={loading}
          className="text-xs glass rounded-lg px-3 py-1.5 hover:shadow-elevated transition-glow disabled:opacity-40 text-foreground"
        >
          새로고침
        </button>
      </header>

      {/* 통계 바 */}
      {total > 0 && !isRoadmapTab && (
        <div className="glass border-b border-[var(--border)] px-4 py-2 flex gap-6 text-xs text-muted-foreground overflow-x-auto">
          <span>
            전체 <strong className="text-foreground">{total}</strong>건
          </span>
          {isErrorTab ? (
            <span style={{ color: "var(--grade-c)" }}>
              오류 <strong>{total}</strong>건
            </span>
          ) : (
            <>
              <span style={{ color: "var(--grade-a)" }}>
                A 통과 <strong>{gradeA}</strong>
                <span className="text-muted-foreground">
                  {" "}
                  ({Math.round((gradeA / total) * 100)}%)
                </span>
              </span>
              <span style={{ color: "var(--grade-b)" }}>
                B 경고 <strong>{gradeB}</strong>
                {gradeB > 0 && (
                  <span className="text-muted-foreground">
                    {" "}
                    ({Math.round((gradeB / total) * 100)}%)
                  </span>
                )}
              </span>
              <span style={{ color: "var(--grade-c)" }}>
                C 반려 <strong>{gradeC}</strong>
                {gradeC > 0 && (
                  <span className="text-muted-foreground">
                    {" "}
                    ({Math.round((gradeC / total) * 100)}%)
                  </span>
                )}
              </span>
              <span>
                평균 응답{" "}
                <strong className="text-foreground">{avgLatency.toLocaleString()}ms</strong>
              </span>
            </>
          )}
        </div>
      )}

      {/* 탭 */}
      <div className="bg-card border-b border-[var(--border)] px-4 flex gap-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
            style={
              tab === t.key
                ? { borderColor: "var(--brand-teal)", color: "var(--brand-teal)" }
                : { borderColor: "transparent", color: "var(--muted-foreground)" }
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 응답자 필터 */}
      {!isRoadmapTab && (
        <div className="glass border-b border-[var(--border)] px-4 py-2 flex items-center gap-3">
          <span className="text-xs text-muted-foreground whitespace-nowrap">응답자 필터:</span>
          <select
            value={selectedUser}
            onChange={(e) => setSelectedUser(e.target.value)}
            className="text-xs rounded-lg px-2 py-1 text-foreground border border-[var(--border)] bg-[var(--card)]"
          >
            <option value="">전체 응답자</option>
            {users.map((u) => (
              <option key={u.user_id} value={u.user_id}>
                {u.name || u.email || u.user_id}
              </option>
            ))}
          </select>
          {selectedUser && (
            <button
              onClick={() => setSelectedUser("")}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              초기화
            </button>
          )}
          <span className="text-xs text-muted-foreground whitespace-nowrap ml-4">세션:</span>
          <input
            type="text"
            placeholder="세션 ID 검색..."
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="text-xs rounded-lg px-2 py-1 border border-[var(--border)] bg-[var(--card)] text-foreground w-40"
          />
          {sessionFilter && (
            <button
              onClick={() => setSessionFilter("")}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              초기화
            </button>
          )}
        </div>
      )}

      {/* 컨텐츠 */}
      <main className="flex-1 overflow-hidden px-4 py-4 max-w-6xl mx-auto w-full">
        {error ? (
          <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-xl px-4 py-3 mt-4">
            {tab === "rejections" && error.includes("없거나")
              ? "거부 이력 로그 파일이 없습니다. 에이전트 테스트 후 재시도하세요."
              : `오류: ${error}`}
          </div>
        ) : isRoadmapTab ? (
          <div className="flex flex-col gap-3 pt-2 max-w-2xl">
            {loading && (
              <div className="text-sm text-center py-12 text-muted-foreground">불러오는 중...</div>
            )}
            {!loading &&
              roadmapFeatures.map((feat) => (
                <div
                  key={feat.feature_id}
                  className="flex items-center justify-between rounded-xl border px-4 py-3"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{feat.icon}</span>
                    <span className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
                      {feat.label}
                    </span>
                  </div>
                  <span
                    className="text-sm font-semibold px-3 py-1 rounded-lg"
                    style={{ background: "var(--muted)", color: "var(--foreground)" }}
                  >
                    ▲ {feat.vote_count}
                  </span>
                </div>
              ))}
          </div>
        ) : (
          <div className="h-[calc(100vh-180px)]">
            {isErrorTab ? (
              <ErrorTable entries={entries} loading={loading} />
            ) : (
              <LogTable entries={displayEntries} loading={loading} feedbackMap={feedbackMap} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
