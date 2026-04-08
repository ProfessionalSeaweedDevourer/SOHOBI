import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchStats } from "../api";
import { ThemeToggle } from "../components/ThemeToggle";
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  DoughnutController,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";

Chart.register(
  BarController, BarElement, CategoryScale, LinearScale,
  DoughnutController, ArcElement, Tooltip, Legend,
);

const PERIODS = [
  { label: "6h",  hours: 6 },
  { label: "24h", hours: 24 },
  { label: "48h", hours: 48 },
  { label: "7d",  hours: 168 },
];

const AGENT_LABELS = {
  finance: "재무", legal: "법률·세무", location: "상권",
  admin: "행정", chat: "일반", unknown: "기타",
};
const AGENT_COLORS = {
  finance: "rgba(139,92,246,0.75)", legal: "rgba(8,145,178,0.75)",
  location: "rgba(20,184,166,0.75)", admin: "rgba(234,179,8,0.75)",
  chat: "rgba(100,116,139,0.75)", unknown: "rgba(203,213,225,0.75)",
};

const GRADE_COLORS = { A: "var(--grade-a)", B: "var(--grade-b)", C: "var(--grade-c)" };
const STATUS_COLORS = {
  approved: "rgba(20,184,166,0.75)", pending: "rgba(234,179,8,0.75)",
  rejected: "rgba(239,68,68,0.75)", unknown: "rgba(148,163,184,0.75)",
};

function ms2s(ms) { return (ms / 1000).toFixed(1) + "s"; }

function SummaryCard({ label, value, sub }) {
  return (
    <div className="glass rounded-xl p-4 flex-1 min-w-[120px]">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-bold text-foreground">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}

function useChart(canvasRef, chartRef, builder, deps) {
  useEffect(() => {
    if (!canvasRef.current) return;
    chartRef.current?.destroy();
    chartRef.current = builder(canvasRef.current);
    return () => { chartRef.current?.destroy(); chartRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

export default function StatsPage() {
  const navigate = useNavigate();
  const [hours, setHours] = useState(24);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const barCanvasRef = useRef(null);
  const barChartRef  = useRef(null);
  const gradeCanvasRef = useRef(null);
  const gradeChartRef  = useRef(null);
  const statusCanvasRef = useRef(null);
  const statusChartRef  = useRef(null);

  const load = useCallback(async (h) => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchStats(h));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(hours); }, [hours, load]);

  // 에이전트별 latency 막대 차트
  useChart(barCanvasRef, barChartRef, (canvas) => {
    if (!data?.by_domain) return null;
    const entries = Object.entries(data.by_domain)
      .filter(([, v]) => v.n > 0)
      .sort((a, b) => b[1].avg_ms - a[1].avg_ms);
    if (entries.length === 0) return null;
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: entries.map(([k]) => AGENT_LABELS[k] ?? k),
        datasets: [{
          label: "avg latency",
          data: entries.map(([, v]) => +(v.avg_ms / 1000).toFixed(2)),
          backgroundColor: entries.map(([k]) => AGENT_COLORS[k] ?? "rgba(148,163,184,0.75)"),
          borderRadius: 6,
          maxBarThickness: 48,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.parsed.x}s` } },
        },
        scales: {
          x: { beginAtZero: true, ticks: { callback: (v) => v + "s", font: { size: 11 } }, grid: { color: "rgba(148,163,184,0.15)" } },
          y: { grid: { display: false }, ticks: { font: { size: 12 } } },
        },
      },
    });
  }, [data]);

  // 등급 도넛
  useChart(gradeCanvasRef, gradeChartRef, (canvas) => {
    if (!data?.by_grade || Object.keys(data.by_grade).length === 0) return null;
    const entries = Object.entries(data.by_grade).sort(([a], [b]) => a.localeCompare(b));
    return new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: entries.map(([k]) => `등급 ${k}`),
        datasets: [{ data: entries.map(([, v]) => v), backgroundColor: entries.map(([k]) => GRADE_COLORS[k] ?? "rgba(148,163,184,0.75)"), borderWidth: 0 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: { legend: { position: "bottom", labels: { font: { size: 11 }, padding: 12 } } },
      },
    });
  }, [data]);

  // 상태 도넛
  useChart(statusCanvasRef, statusChartRef, (canvas) => {
    if (!data?.by_status || Object.keys(data.by_status).length === 0) return null;
    const entries = Object.entries(data.by_status);
    return new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: entries.map(([k]) => k),
        datasets: [{ data: entries.map(([, v]) => v), backgroundColor: entries.map(([k]) => STATUS_COLORS[k] ?? "rgba(148,163,184,0.75)"), borderWidth: 0 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: { legend: { position: "bottom", labels: { font: { size: 11 }, padding: 12 } } },
      },
    });
  }, [data]);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 glass border-b border-[var(--border)] px-4 py-3 flex items-center gap-3">
        <button onClick={() => navigate("/dev")} className="text-muted-foreground hover:text-foreground text-sm transition-colors">
          ← 개발자
        </button>
        <span className="font-semibold text-foreground">성능 통계</span>
        <span className="ml-auto" />
        <ThemeToggle />
        <button onClick={() => load(hours)} disabled={loading} className="text-xs glass rounded-lg px-3 py-1.5 hover:shadow-elevated transition-glow disabled:opacity-40 text-foreground">
          새로고침
        </button>
      </header>

      {/* 기간 선택 */}
      <div className="glass border-b border-[var(--border)] px-4 py-2 flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p.hours}
            onClick={() => setHours(p.hours)}
            className="px-3 py-1 rounded-lg text-sm font-medium transition-colors"
            style={hours === p.hours
              ? { background: "var(--brand-teal)", color: "#fff" }
              : { color: "var(--muted-foreground)" }
            }
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* 본문 */}
      <main className="flex-1 overflow-y-auto p-4 max-w-5xl mx-auto w-full">
        {error && (
          <div className="glass rounded-xl p-4 mb-4 text-sm" style={{ color: "var(--grade-c)" }}>
            오류: {error}
          </div>
        )}

        {loading && !data && (
          <div className="text-center text-muted-foreground py-16 text-sm">로딩 중...</div>
        )}

        {data && (
          <div className="flex flex-col gap-4">
            {/* 요약 카드 */}
            <div className="flex gap-3 flex-wrap">
              <SummaryCard label="총 요청" value={data.total} />
              <SummaryCard label="평균 응답" value={ms2s(data.overall.avg_ms)} sub={`n=${data.overall.n}`} />
              <SummaryCard label="P90" value={ms2s(data.overall.p90_ms)} />
              <SummaryCard label="에러율" value={`${(data.error_rate * 100).toFixed(1)}%`} sub={`${data.error_count}건`} />
            </div>

            {/* 에이전트별 latency */}
            <div className="glass rounded-xl p-5">
              <div className="text-sm font-semibold text-foreground mb-3">에이전트별 평균 응답 시간</div>
              <div style={{ height: Math.max(120, Object.keys(data.by_domain).length * 40) }}>
                <canvas ref={barCanvasRef} />
              </div>
            </div>

            {/* 도넛 차트 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass rounded-xl p-5">
                <div className="text-sm font-semibold text-foreground mb-3">등급 분포</div>
                <div style={{ height: 220 }}>
                  <canvas ref={gradeCanvasRef} />
                </div>
              </div>
              <div className="glass rounded-xl p-5">
                <div className="text-sm font-semibold text-foreground mb-3">상태 분포</div>
                <div style={{ height: 220 }}>
                  <canvas ref={statusCanvasRef} />
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
