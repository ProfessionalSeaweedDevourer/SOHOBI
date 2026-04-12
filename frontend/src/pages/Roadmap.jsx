import { useState, useEffect } from "react";
import { toast } from "sonner";
import { ThemeToggle } from "../components/ThemeToggle";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { GlowCTA } from "../components/GlowCTA";
import { motion } from "motion/react";
import {
  ArrowLeft,
  MessageSquare,
  Vote,
  Zap,
  CheckCircle2,
  ArrowRight,
  ArrowUp,
  ListChecks,
  Hammer,
} from "lucide-react";
import {
  ROADMAP_ICON_MAP,
  ROADMAP_ICON_FALLBACK,
  ROADMAP_COLOR_MAP,
} from "../constants/roadmapIcons";

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

  const sessionId = typeof window !== "undefined" ? localStorage.getItem(SESSION_KEY) || "" : "";

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const res = await fetch(
          `${BASE_URL}/api/roadmap/votes?session_id=${encodeURIComponent(sessionId)}`,
          { headers: _HEADERS, signal: controller.signal },
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
        .sort((a, b) => b.vote_count - a.vote_count),
    );

    try {
      const res = await fetch(`${BASE_URL}/api/roadmap/vote`, {
        method: "POST",
        headers: _HEADERS,
        body: JSON.stringify({ feature_id: featureId, session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFeatures((prev) =>
        [...prev]
          .map((f) =>
            f.feature_id === featureId
              ? { ...f, user_voted: data.voted, vote_count: data.vote_count }
              : f,
          )
          .sort((a, b) => b.vote_count - a.vote_count),
      );
    } catch {
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
          .sort((a, b) => b.vote_count - a.vote_count),
      );
      toast.error("투표에 실패했습니다. 잠시 후 다시 시도해 주세요.");
    }
  }

  const inProgress = features.filter((f) => f.status === "in_progress");
  const voting = features.filter((f) => f.status !== "in_progress");
  const totalVotes = voting.reduce((sum, f) => sum + (f.vote_count ?? 0), 0);

  const stats = [
    {
      Icon: ListChecks,
      label: "전체 피처",
      value: features.length,
      unit: "개",
      color: "var(--brand-blue)",
    },
    {
      Icon: ArrowUp,
      label: "총 투표 수",
      value: totalVotes,
      unit: "표",
      color: "var(--brand-teal)",
    },
    {
      Icon: Hammer,
      label: "개발 중",
      value: inProgress.length,
      unit: "개",
      color: "var(--brand-orange)",
    },
  ];

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
            <Vote size={14} className="text-[var(--brand-blue)]" />
            <span className="text-muted-foreground">커뮤니티 투표</span>
          </motion.div>

          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="text-3xl font-bold gradient-text"
          >
            다음 기능, 여러분이 결정합니다
          </motion.h1>

          <motion.p
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="text-sm"
            style={{ color: "var(--muted-foreground)" }}
          >
            원하는 기능에 투표해 주세요. 투표 결과가 개발 우선순위에 반영됩니다.
          </motion.p>
        </div>

        {/* 통계 배너 */}
        {!loading && features.length > 0 && (
          <div className="grid grid-cols-3 gap-4">
            {stats.map((stat, idx) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 + idx * 0.08 }}
                whileHover={{ y: -4 }}
                className="group"
              >
                <div className="glass rounded-2xl p-4 shadow-elevated transition-glow hover-lift relative overflow-hidden text-center flex flex-col items-center gap-1.5">
                  <div
                    className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 rounded-2xl"
                    style={{ backgroundColor: stat.color }}
                  />
                  <stat.Icon size={20} className="relative z-10" style={{ color: stat.color }} />
                  <span
                    className="text-xl font-bold tabular-nums relative z-10"
                    style={{ color: stat.color }}
                  >
                    {stat.value}
                    <span
                      className="text-xs font-normal ml-0.5"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      {stat.unit}
                    </span>
                  </span>
                  <span
                    className="text-xs relative z-10"
                    style={{ color: "var(--muted-foreground)" }}
                  >
                    {stat.label}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* 미로그인 안내 */}
        {!sessionId && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <GlowCTA orbSize="w-32 h-32" className="p-10 text-center shadow-elevated-lg">
              <div className="flex flex-col items-center gap-4">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                  style={{ backgroundColor: "rgba(8,145,178,0.15)" }}
                >
                  <span className="text-2xl">🗳️</span>
                </div>
                <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  투표하려면 먼저 AI 에이전트와 대화를 시작해 보세요
                </p>
                <a
                  href="/user"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-lg transition-transform hover:scale-105"
                  style={{
                    background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))",
                  }}
                >
                  AI 에이전트와 대화하기
                  <ArrowRight size={14} />
                </a>
              </div>
            </GlowCTA>
          </motion.div>
        )}

        {/* 로딩 */}
        {loading && (
          <div className="text-sm text-center py-12" style={{ color: "var(--muted-foreground)" }}>
            불러오는 중...
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
            {error}
          </div>
        )}

        {/* 피처 목록 */}
        {!loading && !error && features.length > 0 && (
          <div className="flex flex-col gap-8">
            {/* 개발 중 섹션 */}
            {inProgress.length > 0 && (
              <section className="flex flex-col gap-4">
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4 }}
                  className="inline-flex items-center gap-2 glass px-3.5 py-1.5 rounded-full text-xs font-semibold self-start shadow-elevated"
                  style={{ color: "var(--brand-teal)" }}
                >
                  <CheckCircle2 size={13} />
                  지금 만들고 있어요
                </motion.div>

                <div className="flex flex-col gap-3">
                  {inProgress.map((feat, idx) => {
                    const Icon = ROADMAP_ICON_MAP[feat.icon_name] ?? ROADMAP_ICON_FALLBACK;
                    const tone = ROADMAP_COLOR_MAP[feat.color] ?? "var(--brand-teal)";
                    return (
                      <motion.div
                        key={feat.feature_id}
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: idx * 0.07 }}
                        className="group"
                      >
                        <div
                          className="glass rounded-2xl px-5 py-4 shadow-elevated flex items-start gap-3 relative overflow-hidden"
                          style={{ borderLeft: "4px solid var(--brand-teal)" }}
                        >
                          <div
                            className="absolute inset-0 opacity-0 group-hover:opacity-[0.04] transition-opacity duration-300"
                            style={{ backgroundColor: tone }}
                          />
                          <div
                            className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 relative z-10"
                            style={{ backgroundColor: "rgba(20,184,166,0.14)" }}
                          >
                            <Icon size={20} style={{ color: tone }} />
                          </div>
                          <div className="flex-1 min-w-0 relative z-10 flex flex-col gap-1">
                            <span
                              className="text-sm font-semibold"
                              style={{ color: "var(--foreground)" }}
                            >
                              {feat.label}
                            </span>
                            {feat.description && (
                              <span
                                className="text-xs leading-relaxed"
                                style={{ color: "var(--muted-foreground)" }}
                              >
                                {feat.description}
                              </span>
                            )}
                          </div>
                          <motion.span
                            animate={{ opacity: [1, 0.5, 1] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            className="text-xs font-semibold px-3 py-1.5 rounded-xl relative z-10 shrink-0 self-start"
                            style={{
                              background: "rgba(20,184,166,0.15)",
                              color: "var(--brand-teal)",
                            }}
                          >
                            개발 중
                          </motion.span>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* 투표 중 섹션 */}
            {voting.length > 0 && (
              <section className="flex flex-col gap-4">
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4 }}
                  className="inline-flex items-center gap-2 glass px-3.5 py-1.5 rounded-full text-xs font-semibold self-start shadow-elevated"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  <Zap size={13} />
                  투표로 우선순위를 정해요
                </motion.div>

                <div className="flex flex-col gap-3">
                  {voting.map((feat, idx) => {
                    const Icon = ROADMAP_ICON_MAP[feat.icon_name] ?? ROADMAP_ICON_FALLBACK;
                    const tone = ROADMAP_COLOR_MAP[feat.color] ?? "var(--brand-blue)";
                    return (
                      <motion.div
                        key={feat.feature_id}
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: idx * 0.05 }}
                        className="group"
                      >
                        <div className="glass rounded-2xl px-5 py-4 shadow-elevated flex items-start gap-3 relative overflow-hidden transition-glow hover-lift">
                          <div
                            className="absolute inset-0 opacity-0 group-hover:opacity-[0.04] transition-opacity duration-300"
                            style={{ backgroundColor: tone }}
                          />
                          <div
                            className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 relative z-10"
                            style={{
                              backgroundColor: `color-mix(in srgb, ${tone} 12%, transparent)`,
                            }}
                          >
                            <Icon size={20} style={{ color: tone }} />
                          </div>
                          <div className="flex-1 min-w-0 relative z-10 flex flex-col gap-1">
                            <span
                              className="text-sm font-semibold"
                              style={{ color: "var(--foreground)" }}
                            >
                              {feat.label}
                            </span>
                            {feat.description && (
                              <span
                                className="text-xs leading-relaxed"
                                style={{ color: "var(--muted-foreground)" }}
                              >
                                {feat.description}
                              </span>
                            )}
                          </div>

                          <motion.button
                            onClick={() => handleVote(feat.feature_id)}
                            disabled={!sessionId}
                            whileHover={sessionId ? { scale: 1.05 } : {}}
                            whileTap={sessionId ? { scale: 0.95 } : {}}
                            className="flex items-center gap-1 px-3.5 py-2 rounded-xl text-sm font-semibold border transition-all relative z-10 shrink-0 self-start tabular-nums"
                            style={{
                              background: feat.user_voted
                                ? "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))"
                                : "transparent",
                              color: feat.user_voted ? "#fff" : "var(--brand-blue)",
                              borderColor: feat.user_voted ? "transparent" : "var(--brand-blue)",
                              cursor: sessionId ? "pointer" : "default",
                              opacity: sessionId ? 1 : 0.5,
                              boxShadow: feat.user_voted ? "0 0 16px rgba(8,145,178,0.35)" : "none",
                            }}
                          >
                            <ArrowUp size={14} strokeWidth={2.5} />
                            {feat.vote_count}
                          </motion.button>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
