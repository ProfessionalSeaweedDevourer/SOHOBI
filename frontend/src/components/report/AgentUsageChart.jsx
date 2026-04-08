import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { BarChart2 } from "lucide-react";
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const AGENT_LABELS = {
  finance:  "재무",
  legal:    "법률·세무",
  location: "상권",
  admin:    "행정",
  chat:     "일반",
  unknown:  "기타",
};

const AGENT_COLORS = {
  finance:  "rgba(139,92,246,0.75)",
  legal:    "rgba(8,145,178,0.75)",
  location: "rgba(20,184,166,0.75)",
  admin:    "rgba(234,179,8,0.75)",
  chat:     "rgba(100,116,139,0.75)",
  unknown:  "rgba(203,213,225,0.75)",
};

const AGENT_SOLID = {
  finance:  "#8b5cf6",
  legal:    "#0891b2",
  location: "#14b8a6",
  admin:    "#eab308",
  chat:     "#64748b",
  unknown:  "#cbd5e1",
};

export default function AgentUsageChart({ agentUsage }) {
  const canvasRef = useRef(null);
  const chartRef  = useRef(null);

  useEffect(() => {
    if (!agentUsage || !canvasRef.current) return;

    const entries = Object.entries(agentUsage).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) return;

    if (chartRef.current) {
      chartRef.current.destroy();
      chartRef.current = null;
    }

    const labels = entries.map(([k]) => AGENT_LABELS[k] ?? k);
    const data   = entries.map(([, v]) => v);
    const colors = entries.map(([k]) => AGENT_COLORS[k] ?? "rgba(148,163,184,0.75)");

    chartRef.current = new Chart(canvasRef.current, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "이용 횟수",
            data,
            backgroundColor: colors,
            borderRadius: 6,
            maxBarThickness: 48,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (ctx) => ` ${ctx.parsed.y}회` },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 12 } },
          },
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1, font: { size: 11 } },
            grid: { color: "rgba(148,163,184,0.15)" },
          },
        },
      },
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [agentUsage]);

  const entries = agentUsage ? Object.entries(agentUsage).sort((a, b) => b[1] - a[1]) : [];
  const isEmpty  = entries.length === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className="glass rounded-2xl shadow-elevated overflow-hidden"
    >
      {/* 섹션 헤더 */}
      <div className="px-5 pt-5 pb-4 flex items-center gap-2 border-b" style={{ borderColor: "var(--border)" }}>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: "rgba(8,145,178,0.12)" }}
        >
          <BarChart2 size={15} style={{ color: "var(--brand-blue)" }} />
        </div>
        <span className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
          에이전트별 이용 현황
        </span>
      </div>

      <div className="px-5 pb-5 pt-4">
        {isEmpty ? (
          <div className="h-32 flex items-center justify-center text-sm" style={{ color: "var(--muted-foreground)" }}>
            이용 기록이 없습니다
          </div>
        ) : (
          <>
            {/* 컬러 범례 */}
            <div className="flex flex-wrap gap-2 mb-4">
              {entries.map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{
                    backgroundColor: `${AGENT_SOLID[k] ?? "#94a3b8"}18`,
                    color: AGENT_SOLID[k] ?? "#94a3b8",
                  }}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: AGENT_SOLID[k] ?? "#94a3b8" }}
                  />
                  {AGENT_LABELS[k] ?? k}
                  <span className="opacity-70">{v}회</span>
                </span>
              ))}
            </div>

            {/* 차트 */}
            <div style={{ height: 180 }}>
              <canvas ref={canvasRef} />
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
