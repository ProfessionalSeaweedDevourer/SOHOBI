import { useState, useEffect } from "react";
import { ThemeToggle } from "../components/ThemeToggle";
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

export default function Roadmap() {
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const sessionId =
    typeof window !== "undefined" ? localStorage.getItem(SESSION_KEY) || "" : "";

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const res = await fetch(
          `${BASE_URL}/api/roadmap/votes?session_id=${encodeURIComponent(sessionId)}`,
          { headers: _HEADERS, signal: controller.signal }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setFeatures(data.features || []);
      } catch (e) {
        if (e.name !== "AbortError") setError("투표 현황을 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [sessionId]);

  async function handleVote(featureId) {
    if (!sessionId) return;

    // 옵티미스틱 업데이트
    setFeatures((prev) =>
      [...prev]
        .map((f) => {
          if (f.feature_id !== featureId) return f;
          const nowVoted = !f.user_voted;
          return {
            ...f,
            user_voted: nowVoted,
            vote_count: nowVoted ? f.vote_count + 1 : Math.max(0, f.vote_count - 1),
          };
        })
        .sort((a, b) => b.vote_count - a.vote_count)
    );

    try {
      const res = await fetch(`${BASE_URL}/api/roadmap/vote`, {
        method: "POST",
        headers: _HEADERS,
        body: JSON.stringify({ feature_id: featureId, session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // 서버 실제 값으로 동기화
      setFeatures((prev) =>
        [...prev]
          .map((f) =>
            f.feature_id === featureId
              ? { ...f, user_voted: data.voted, vote_count: data.vote_count }
              : f
          )
          .sort((a, b) => b.vote_count - a.vote_count)
      );
    } catch {
      // 실패 시 옵티미스틱 업데이트 롤백
      setFeatures((prev) =>
        [...prev]
          .map((f) => {
            if (f.feature_id !== featureId) return f;
            const revert = !f.user_voted;
            return {
              ...f,
              user_voted: revert,
              vote_count: revert ? f.vote_count + 1 : Math.max(0, f.vote_count - 1),
            };
          })
          .sort((a, b) => b.vote_count - a.vote_count)
      );
    }
  }

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
          {/* Left: 뒤로 */}
          <a
            href="/user"
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
            style={{ textDecoration: "none" }}
          >
            <ArrowLeft size={16} />
            <span className="text-sm">상담으로</span>
          </a>

          {/* Center: 로고 */}
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

          {/* Right */}
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
      </motion.header>

      {/* 본문 */}
      <main className="relative z-10 flex-1 max-w-2xl w-full mx-auto px-4 py-8 flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>
            🗳️ 다음에 추가되었으면 하는 기능
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>
            원하는 기능에 투표해 주세요. 투표 결과가 개발 우선순위에 반영됩니다.
          </p>
        </div>

        {!sessionId && (
          <div
            className="rounded-2xl border p-6 text-center"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="text-2xl mb-3">🗳️</div>
            <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
              투표하려면 먼저{" "}
              <a href="/user" style={{ color: "var(--brand-blue, #0891b2)" }}>
                AI 에이전트
              </a>
              와 대화를 시작해 보세요.
            </p>
          </div>
        )}

        {loading && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            불러오는 중...
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
            {error}
          </div>
        )}

        {!loading && !error && features.length > 0 && (() => {
          const inProgress = features.filter(f => f.status === "in_progress");
          const voting = features.filter(f => f.status !== "in_progress");

          const FeatureRow = ({ feat }) => (
            <div
              key={feat.feature_id}
              className="flex items-center justify-between rounded-2xl border px-4 py-3"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{feat.icon}</span>
                <span className="text-sm font-medium">{feat.label}</span>
              </div>
              {feat.status === "in_progress" ? (
                <span
                  className="text-xs font-semibold px-3 py-1.5 rounded-xl"
                  style={{ background: "var(--brand-teal, #14b8a6)", color: "#fff" }}
                >
                  개발 중
                </span>
              ) : (
                <button
                  onClick={() => handleVote(feat.feature_id)}
                  disabled={!sessionId}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold border transition-colors"
                  style={{
                    background: feat.user_voted ? "var(--primary)" : "transparent",
                    color: feat.user_voted ? "#fff" : "var(--primary)",
                    borderColor: "var(--primary)",
                    cursor: sessionId ? "pointer" : "default",
                    opacity: sessionId ? 1 : 0.5,
                  }}
                >
                  ▲ {feat.vote_count}
                </button>
              )}
            </div>
          );

          return (
            <div className="flex flex-col gap-6">
              {inProgress.length > 0 && (
                <div className="flex flex-col gap-3">
                  <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--brand-teal, #14b8a6)" }}>
                    개발 중
                  </p>
                  {inProgress.map(feat => <FeatureRow key={feat.feature_id} feat={feat} />)}
                </div>
              )}
              {voting.length > 0 && (
                <div className="flex flex-col gap-3">
                  <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                    투표 중 — 높은 순으로 개발 반영
                  </p>
                  {voting.map(feat => <FeatureRow key={feat.feature_id} feat={feat} />)}
                </div>
              )}
            </div>
          );
        })()}
      </main>
    </div>
  );
}
