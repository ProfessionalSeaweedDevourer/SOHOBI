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
  { label: "30d", hours: 720 },
  { label: "90d", hours: 2160 },
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

const GRADE_COLORS = { A: "#10b981", B: "#eab308", C: "#ef4444" };
const STATUS_COLORS = {
  approved: "rgba(20,184,166,0.75)", pending: "rgba(234,179,8,0.75)",
  rejected: "rgba(239,68,68,0.75)", unknown: "rgba(148,163,184,0.75)",
};

function ms2s(ms) { return ((ms ?? 0) / 1000).toFixed(1) + "s"; }

function SummaryCard({ label, value, sub }) {
  return (
    <div className="glass rounded-xl p-4 flex-1 min-w-[120px]">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-bold text-foreground">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}

function BarChart({ byDomain }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !byDomain) return;
    chartRef.current?.destroy();

    const entries = Object.entries(byDomain)
      .filter(([, v]) => v.n > 0)
      .sort((a, b) => b[1].avg_ms - a[1].avg_ms);
    if (entries.length === 0) return;

    chartRef.current = new Chart(canvasRef.current, {
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

    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, [byDomain]);

  const domainCount = byDomain ? Object.keys(byDomain).length : 0;
  return (
    <div className="glass rounded-xl p-5">
      <div className="text-sm font-semibold text-foreground mb-3">에이전트별 평균 응답 시간</div>
      <div style={{ height: Math.max(160, domainCount * 50) }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}

function DoughnutChart({ title, dataMap, colorMap }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !dataMap || Object.keys(dataMap).length === 0) return;
    chartRef.current?.destroy();

    const entries = Object.entries(dataMap).sort(([a], [b]) => a.localeCompare(b));

    chartRef.current = new Chart(canvasRef.current, {
      type: "doughnut",
      data: {
        labels: entries.map(([k]) => k),
        datasets: [{
          data: entries.map(([, v]) => v),
          backgroundColor: entries.map(([k]) => colorMap[k] ?? "rgba(148,163,184,0.75)"),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: { legend: { position: "bottom", labels: { font: { size: 11 }, padding: 12 } } },
      },
    });

    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, [dataMap, colorMap]);

  return (
    <div className="glass rounded-xl p-5">
      <div className="text-sm font-semibold text-foreground mb-3">{title}</div>
      <div style={{ height: 220 }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}

const GRADE_LABEL_MAP = { A: "등급 A", B: "등급 B", C: "등급 C" };

export default function StatsPage() {
  const navigate = useNavigate();
  const [hours, setHours] = useState(24);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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

  const gradeLabeled = data?.by_grade
    ? Object.fromEntries(Object.entries(data.by_grade).map(([k, v]) => [GRADE_LABEL_MAP[k] ?? k, v]))
    : null;
  const gradeLabeledColors = Object.fromEntries(
    Object.entries(GRADE_COLORS).map(([k, v]) => [GRADE_LABEL_MAP[k] ?? k, v])
  );

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
      <div className="glass border-b border-[var(--border)] px-4 py-2 flex gap-2" role="group" aria-label="조회 기간">
        {PERIODS.map((p) => (
          <button
            key={p.hours}
            onClick={() => setHours(p.hours)}
            aria-pressed={hours === p.hours}
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
              <SummaryCard label="평균 응답" value={ms2s(data.overall?.avg_ms)} sub={`n=${data.overall?.n ?? 0}`} />
              <SummaryCard label="P90" value={ms2s(data.overall?.p90_ms)} />
              <SummaryCard label="에러율" value={`${(Math.min(data.error_rate ?? 0, 1) * 100).toFixed(1)}%`} sub={`${data.error_count}건`} />
            </div>

            <BarChart byDomain={data.by_domain} />

            {/* 도넛 차트 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <DoughnutChart title="등급 분포" dataMap={gradeLabeled} colorMap={gradeLabeledColors} />
              <DoughnutChart title="상태 분포" dataMap={data.by_status} colorMap={STATUS_COLORS} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
