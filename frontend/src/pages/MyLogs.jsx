import { useState, useEffect } from "react";
import { ThemeToggle } from "../components/ThemeToggle";
import { useAuth } from "../contexts/AuthContext";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function formatDate(isoString) {
  if (!isoString) return "-";
  const d = new Date(isoString);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

function SessionCard({ session, token }) {
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
    <div
      className="rounded-2xl border overflow-hidden"
      style={{ background: "var(--card)", borderColor: "var(--border)" }}
    >
      <button
        onClick={loadHistory}
        className="w-full text-left px-5 py-4 flex items-center gap-3 hover:bg-[var(--muted)] transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {ctx.business_type && (
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: "rgba(8,145,178,0.12)", color: "var(--brand-blue)" }}
              >
                {ctx.business_type}
              </span>
            )}
            {ctx.location_name && (
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium"
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
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {formatDate(session.created_at)}
            </span>
            <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              질문 {session.query_count}건
            </span>
          </div>
        </div>
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          {loading ? "..." : open ? "▲" : "▼"}
        </span>
      </button>

      {open && history !== null && (
        <div
          className="border-t px-5 py-4 flex flex-col gap-4"
          style={{ borderColor: "var(--border)" }}
        >
          {history.length === 0 && (
            <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
              대화 내역이 없습니다.
            </p>
          )}
          {history.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className="max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
                style={
                  msg.role === "user"
                    ? { background: "rgba(8,145,178,0.12)", color: "var(--foreground)" }
                    : { background: "var(--muted)", color: "var(--foreground)" }
                }
              >
                {msg.content}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      <header
        className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3 border-b"
        style={{ background: "var(--card)", borderColor: "var(--border)" }}
      >
        <a
          href="/user"
          className="text-xl font-bold tracking-tight"
          style={{ color: "var(--foreground)", textDecoration: "none" }}
        >
          SOHOBI
        </a>
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
        >
          내 질의응답 로그
        </span>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-8 flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>
            질의응답 로그
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>
            로그인 후 진행한 창업 상담 기록을 확인합니다
          </p>
        </div>

        {authLoading && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            로딩 중...
          </div>
        )}

        {!authLoading && !user && (
          <div
            className="rounded-2xl border p-8 text-center flex flex-col items-center gap-4"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="text-3xl">🔐</div>
            <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
              질의응답 로그는 로그인 후 이용할 수 있습니다.
            </p>
            <button
              onClick={login}
              className="text-sm px-4 py-2 rounded-xl font-medium transition-colors"
              style={{
                background: "var(--brand-blue, #0891b2)",
                color: "#fff",
              }}
            >
              Google로 로그인
            </button>
          </div>
        )}

        {!authLoading && user && fetching && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            기록을 불러오는 중...
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

        {!authLoading && user && !fetching && !error && sessions !== null && (
          sessions.length === 0 ? (
            <div
              className="rounded-2xl border p-6 text-center"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="text-2xl mb-3">📭</div>
              <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                아직 로그인 상태에서 진행한 상담이 없습니다.{" "}
                <a href="/user" style={{ color: "var(--brand-blue, #0891b2)" }}>
                  AI 에이전트
                </a>
                와 대화를 시작해 보세요.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {sessions.map((s) => (
                <SessionCard key={s.session_id} session={s} token={user.token} />
              ))}
            </div>
          )
        )}
      </main>
    </div>
  );
}
