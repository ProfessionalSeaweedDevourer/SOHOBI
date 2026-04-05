import { useEffect, useRef } from "react";
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
  finance: "재무",
  legal: "법률·세무",
  location: "상권",
  admin: "행정",
  chat: "일반",
  unknown: "기타",
};

const AGENT_COLORS = {
  finance: "rgba(139,92,246,0.75)",
  legal: "rgba(8,145,178,0.75)",
  location: "rgba(20,184,166,0.75)",
  admin: "rgba(234,179,8,0.75)",
  chat: "rgba(100,116,139,0.75)",
  unknown: "rgba(203,213,225,0.75)",
};

/**
 * 에이전트별 이용 횟수 막대 차트
 *
 * @param {object} props
 * @param {object} props.agentUsage - {finance: 5, legal: 3, ...}
 */
export default function AgentUsageChart({ agentUsage }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

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
            callbacks: {
              label: (ctx) => ` ${ctx.parsed.y}회`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 12 } },
          },
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
              font: { size: 11 },
            },
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

  const isEmpty = !agentUsage || Object.keys(agentUsage).length === 0;

  return (
    <div
      className="rounded-2xl border p-4"
      style={{
        background: "var(--card)",
        borderColor: "var(--border)",
        boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
      }}
    >
      <div className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
        에이전트별 이용 현황
      </div>
      {isEmpty ? (
        <div
          className="h-32 flex items-center justify-center text-sm"
          style={{ color: "var(--muted-foreground)" }}
        >
          이용 기록이 없습니다
        </div>
      ) : (
        <div style={{ height: 180 }}>
          <canvas ref={canvasRef} />
        </div>
      )}
    </div>
  );
}
