import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import {
  GitCommit,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { ThemeToggle } from "../components/ThemeToggle";

// ── 상수 ──────────────────────────────────────────────────────────────
const CACHE_TTL_MS = 60 * 60 * 1000;

const TYPE_MAP = {
  feat:     { label: "새 기능",   color: "#0891b2" },
  fix:      { label: "버그 수정", color: "#ef4444" },
  docs:     { label: "문서",      color: "#8b5cf6" },
  chore:    { label: "유지보수",  color: "#717182" },
  refactor: { label: "리팩토링", color: "#f97316" },
  perf:     { label: "성능",      color: "#14b8a6" },
  test:     { label: "테스트",    color: "#eab308" },
  ci:       { label: "CI/CD",     color: "#6366f1" },
  security: { label: "보안",      color: "#ec4899" },
  debug:    { label: "디버그",    color: "#a3a3a3" },
};

function isNotMerge(raw) {
  const msg = raw.commit.message;
  return !msg.startsWith("Merge pull request") && !msg.startsWith("Merge branch");
}

// ── 유틸 함수 ────────────────────────────────────────────────────────
async function fetchCommits(page = 1) {
  const cacheKey = `sohobi_changelog_cache_p${page}`;
  try {
    const raw = localStorage.getItem(cacheKey);
    if (raw) {
      const { fetchedAt, commits } = JSON.parse(raw);
      if (Date.now() - new Date(fetchedAt).getTime() < CACHE_TTL_MS)
        return commits;
    }
  } catch (_) {}
  const url = `https://api.github.com/repos/ProfessionalSeaweedDevourer/SOHOBI/commits?per_page=100&page=${page}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GitHub API ${res.status}`);
  const commits = await res.json();
  localStorage.setItem(
    cacheKey,
    JSON.stringify({ fetchedAt: new Date().toISOString(), commits })
  );
  return commits;
}

function parseCommit(raw) {
  const firstLine = raw.commit.message.split("\n")[0].trim();
  const match = firstLine.match(/^(\w+)(?:\([^)]+\))?:\s*(.+)$/);
  const type = match ? match[1].toLowerCase() : "other";
  return {
    sha: raw.sha,
    shortSha: raw.sha.slice(0, 7),
    type,
    message: match ? match[2] : firstLine,
    date: raw.commit.author.date,
    author: raw.commit.author.name,
    url: raw.html_url,
    typeMeta: TYPE_MAP[type] ?? { label: type, color: "#717182" },
  };
}

function groupByDate(commits) {
  const map = new Map();
  for (const c of commits) {
    const key = c.date.slice(0, 10);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(c);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([key, commits]) => ({
      dateKey: key,
      dateLabel: (() => {
        try {
          return new Date(key + "T00:00:00").toLocaleDateString("ko-KR", {
            year: "numeric",
            month: "long",
            day: "numeric",
            weekday: "short",
          });
        } catch (_) {
          return key;
        }
      })(),
      commits,
    }));
}

function formatCommitDate(isoDate) {
  const d = new Date(isoDate);
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString("ko-KR", {
    ...(sameYear ? {} : { year: "numeric" }),
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── 서브 컴포넌트 ────────────────────────────────────────────────────
function TypeBadge({ typeMeta }) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold shrink-0"
      style={{
        backgroundColor: typeMeta.color + "22",
        color: typeMeta.color,
        border: `1px solid ${typeMeta.color}44`,
      }}
    >
      {typeMeta.label}
    </span>
  );
}

function CommitCard({ commit, idx }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, delay: Math.min(idx * 0.02, 0.4) }}
      className="glass rounded-xl px-4 py-3 shadow-elevated flex flex-col sm:flex-row sm:items-center gap-2"
    >
      <TypeBadge typeMeta={commit.typeMeta} />
      <span className="flex-1 text-sm text-foreground/90 min-w-0 break-words">
        {commit.message}
      </span>
      <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0 flex-wrap">
        <span>{commit.author}</span>
        <span>{formatCommitDate(commit.date)}</span>
        <a
          href={commit.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono hover:text-[var(--brand-blue)] transition-colors flex items-center gap-0.5"
        >
          {commit.shortSha}
          <ExternalLink size={10} />
        </a>
      </div>
    </motion.div>
  );
}

// ── 메인 페이지 ──────────────────────────────────────────────────────
export default function Changelog() {
  const [commits, setCommits] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [activeFilter, setActiveFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchCommits(1);
        if (!cancelled) {
          setCommits(data.filter(isNotMerge).map(parseCommit));
          setHasMore(data.length === 100);
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function loadMore() {
    const nextPage = currentPage + 1;
    setIsLoading(true);
    try {
      const data = await fetchCommits(nextPage);
      setCommits((prev) => [...prev, ...data.filter(isNotMerge).map(parseCommit)]);
      setCurrentPage(nextPage);
      setHasMore(data.length === 100);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }

  const groups = useMemo(() => groupByDate(commits), [commits]);

  const filteredGroups = useMemo(() => {
    if (activeFilter === "all") return groups;
    return groups
      .map((g) => ({
        ...g,
        commits: g.commits.filter((c) => c.type === activeFilter),
      }))
      .filter((g) => g.commits.length > 0);
  }, [groups, activeFilter]);

  const availableTypes = useMemo(() => {
    const seen = new Set(groups.flatMap((g) => g.commits.map((c) => c.type)));
    return ["all", ...Object.keys(TYPE_MAP).filter((t) => seen.has(t))];
  }, [groups]);

  return (
    <div className="min-h-screen relative bg-background">
      <AnimatedBackground />

      {/* 헤더 */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="sticky top-0 z-50 glass border-b border-white/20 backdrop-blur-xl"
      >
        <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft size={16} />
            홈
          </Link>

          <div className="flex items-center gap-2">
            <GitCommit size={18} className="text-[var(--brand-blue)]" />
            <span className="font-semibold text-sm">업데이트 로그</span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/user"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              AI 상담 →
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </motion.header>

      {/* 히어로 */}
      <section className="container mx-auto px-4 pt-16 pb-10 text-center">
        <motion.div
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="inline-flex items-center gap-2 glass px-5 py-2.5 rounded-full text-sm mb-8 shadow-elevated"
        >
          <GitCommit size={15} className="text-[var(--brand-blue)]" />
          <span className="gradient-text font-semibold">개발 히스토리</span>
        </motion.div>

        <motion.h1
          initial={{ y: 18, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="text-4xl md:text-5xl font-bold mb-4 leading-tight tracking-tight"
        >
          업데이트{" "}
          <span className="gradient-text">로그</span>
        </motion.h1>

        <motion.p
          initial={{ y: 12, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="text-muted-foreground max-w-lg mx-auto text-sm"
        >
          SOHOBI의 실시간 개발 현황입니다.
          {commits.length > 0 && (
            <span className="ml-1 text-[var(--brand-blue)] font-medium">
              최근 {commits.length}개 커밋 표시 중
            </span>
          )}
        </motion.p>
      </section>

      {/* 필터 바 */}
      {availableTypes.length > 1 && (
        <div className="container mx-auto px-4 mb-8">
          <div className="overflow-x-auto">
            <div className="flex gap-2 pb-2 min-w-max">
              {availableTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => setActiveFilter(type)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all shrink-0 ${
                    activeFilter === type
                      ? "bg-[var(--brand-blue)] text-white shadow-lg"
                      : "glass text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {type === "all" ? "전체" : TYPE_MAP[type]?.label ?? type}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 타임라인 */}
      <section className="container mx-auto px-4 pb-16 max-w-3xl">
        {/* 로딩 (첫 로드) */}
        {isLoading && commits.length === 0 && (
          <div className="flex items-center justify-center py-20 gap-3 text-muted-foreground">
            <RefreshCw size={18} className="animate-spin" />
            <span>커밋 기록 불러오는 중...</span>
          </div>
        )}

        {/* 에러 */}
        {error && commits.length === 0 && (
          <div className="glass rounded-xl p-8 text-center text-sm text-muted-foreground">
            <AlertCircle size={20} className="mx-auto mb-3 text-destructive" />
            <p className="font-medium mb-1">데이터를 불러올 수 없습니다.</p>
            <p className="text-xs opacity-60">{error}</p>
          </div>
        )}

        {/* 날짜별 그룹 */}
        {filteredGroups.map((group) => (
          <div key={group.dateKey} className="mb-8">
            <p className="text-xs text-muted-foreground mb-3 pl-1 font-medium tracking-wide uppercase">
              {group.dateLabel}
            </p>
            <div className="flex flex-col gap-2">
              {group.commits.map((commit, idx) => (
                <CommitCard key={commit.sha} commit={commit} idx={idx} />
              ))}
            </div>
          </div>
        ))}

        {/* 필터 결과 없음 */}
        {!isLoading && filteredGroups.length === 0 && commits.length > 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            해당 타입의 커밋이 없습니다.
          </div>
        )}

        {/* 더 보기 버튼 */}
        {hasMore && !isLoading && commits.length > 0 && (
          <div className="text-center mt-6">
            <button
              onClick={loadMore}
              className="glass px-6 py-2.5 rounded-lg text-sm font-medium hover:text-[var(--brand-blue)] transition-colors"
            >
              더 보기
            </button>
          </div>
        )}

        {/* 추가 로딩 스피너 */}
        {isLoading && commits.length > 0 && (
          <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground text-sm">
            <RefreshCw size={14} className="animate-spin" />
            <span>불러오는 중...</span>
          </div>
        )}

        {/* 에러 (더 보기 실패) */}
        {error && commits.length > 0 && (
          <div className="text-center py-4 text-xs text-muted-foreground">
            <AlertCircle size={14} className="inline mr-1" />
            {error}
          </div>
        )}
      </section>

      {/* 푸터 */}
      <footer className="glass border-t border-white/20 py-10 backdrop-blur-xl">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p className="mb-2">© 2026 SOHOBI.</p>
          <p className="mb-3">소상공인을 위한 AI 컨설팅 플랫폼</p>
          <Link
            to="/privacy"
            className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2"
          >
            개인정보처리방침
          </Link>
        </div>
      </footer>
    </div>
  );
}
