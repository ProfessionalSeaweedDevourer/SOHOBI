import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { fetchStats } from "../api";
import { ThemeToggle } from "../components/ThemeToggle";
import { AnimatedBackground } from "../components/AnimatedBackground";
import {
  ArrowLeft, BarChart3, RefreshCw, Activity,
  Hash, Clock, Gauge, AlertTriangle, AlertCircle, PieChart,
} from "lucide-react";
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

const GRADE_COLORS = { A: "#10b981", B: "#eab308", C: "#ef4444" };
const STATUS_COLORS = {
  approved: "rgba(20,184,166,0.75)", pending: "rgba(234,179,8,0.75)",
  rejected: "rgba(239,68,68,0.75)", unknown: "rgba(148,163,184,0.75)",
};

function ms2s(ms) { return ((ms ?? 0) / 1000).toFixed(1) + "s"; }

function SummaryCard({ label, value, sub, icon: Icon, color }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className="glass rounded-2xl p-5 flex-1 min-w-[140px] shadow-elevated hover-lift transition-glow relative overflow-hidden group"
    >
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300"
        style={{ backgroundColor: color }}
      />
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${color}20` }}
        >
          <Icon size={16} style={{ color }} />
        </div>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </motion.div>
  );
}

function LatencyBarChart({ byDomain }) {
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
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="glass rounded-2xl p-6 shadow-elevated"
    >
      <div className="flex items-center gap-2 mb-4">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: "rgba(8,145,178,0.15)" }}
        >
          <BarChart3 size={16} className="text-[var(--brand-blue)]" />
        </div>
        <span className="text-sm font-semibold text-foreground">에이전트별 평균 응답 시간</span>
      </div>
      <div style={{ height: Math.max(160, domainCount * 50) }}>
        <canvas ref={canvasRef} />
      </div>
    </motion.div>
  );
}

function DoughnutChart({ title, dataMap, colorMap, icon: Icon, iconColor }) {
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
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="glass rounded-2xl p-6 shadow-elevated"
    >
      <div className="flex items-center gap-2 mb-4">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${iconColor}20` }}
        >
          <Icon size={16} style={{ color: iconColor }} />
        </div>
        <span className="text-sm font-semibold text-foreground">{title}</span>
      </div>
      <div style={{ height: 220 }}>
        <canvas ref={canvasRef} />
      </div>
    </motion.div>
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
    <div className="min-h-screen relative">
      <AnimatedBackground />

      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
          <Link
            to="/dev"
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            개발자 도구
          </Link>

          <div className="flex items-center gap-2">
            <motion.div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: "rgba(20,184,166,0.15)" }}
              whileHover={{ scale: 1.1, rotate: 360 }}
              transition={{ duration: 0.6 }}
            >
              <Activity size={18} className="text-[var(--brand-teal)]" />
            </motion.div>
            <span className="font-semibold gradient-text">성능 통계</span>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <motion.button
              onClick={() => load(hours)}
              disabled={loading}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center gap-1.5 glass px-3 py-1.5 rounded-lg text-sm font-medium hover:text-foreground transition-colors disabled:opacity-40 text-muted-foreground"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              새로고침
            </motion.button>
          </div>
        </div>
      </motion.header>

      {/* Hero */}
      <section className="container mx-auto px-4 pt-12 pb-6 text-center">
        <motion.div
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 glass px-5 py-2.5 rounded-full text-sm mb-5 shadow-elevated"
        >
          <Activity size={15} className="text-[var(--brand-teal)]" />
          <span className="gradient-text font-semibold">시스템 모니터링</span>
        </motion.div>

        <motion.h1
          initial={{ y: 18, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-3xl md:text-4xl font-bold mb-3 leading-tight tracking-tight"
        >
          성능 <span className="gradient-text">통계</span>
        </motion.h1>

        <motion.p
          initial={{ y: 12, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="text-muted-foreground max-w-lg mx-auto text-sm"
        >
          에이전트별 응답 시간, 등급 분포, 상태 현황을 모니터링합니다.
        </motion.p>
      </section>

      {/* Period Selector */}
      <div className="container mx-auto px-4 mb-8">
        <div className="flex gap-2 justify-center flex-wrap">
          {PERIODS.map((p) => (
            <motion.button
              key={p.hours}
              onClick={() => setHours(p.hours)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                hours === p.hours
                  ? "bg-[var(--brand-teal)] text-white shadow-lg"
                  : "glass text-muted-foreground hover:text-foreground"
              }`}
            >
              {p.label}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="container mx-auto px-4 pb-16 max-w-5xl">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-2xl p-6 mb-6 shadow-elevated flex items-center gap-3"
          >
            <AlertCircle size={18} style={{ color: "var(--grade-c)" }} />
            <span className="text-sm" style={{ color: "var(--grade-c)" }}>
              오류: {error}
            </span>
          </motion.div>
        )}

        {loading && !data && (
          <div className="text-center text-muted-foreground py-20 text-sm flex flex-col items-center gap-3">
            <RefreshCw size={18} className="animate-spin" />
            로딩 중...
          </div>
        )}

        {data && (
          <div className="flex flex-col gap-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SummaryCard label="총 요청" value={data.total} icon={Hash} color="var(--brand-blue)" />
              <SummaryCard label="평균 응답" value={ms2s(data.overall?.avg_ms)} sub={`n=${data.overall?.n ?? 0}`} icon={Clock} color="var(--brand-teal)" />
              <SummaryCard label="P90" value={ms2s(data.overall?.p90_ms)} icon={Gauge} color="var(--brand-orange)" />
              <SummaryCard label="에러율" value={`${(Math.min(data.error_rate ?? 0, 1) * 100).toFixed(1)}%`} sub={`${data.error_count}건`} icon={AlertTriangle} color="var(--grade-c)" />
            </div>

            <LatencyBarChart byDomain={data.by_domain} />

            {/* Doughnut Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <DoughnutChart title="등급 분포" dataMap={gradeLabeled} colorMap={gradeLabeledColors} icon={PieChart} iconColor="var(--brand-teal)" />
              <DoughnutChart title="상태 분포" dataMap={data.by_status} colorMap={STATUS_COLORS} icon={Activity} iconColor="var(--brand-blue)" />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="glass border-t border-white/20 py-8 backdrop-blur-xl">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>SOHOBI 개발자 도구</p>
        </div>
      </footer>
    </div>
  );
}
