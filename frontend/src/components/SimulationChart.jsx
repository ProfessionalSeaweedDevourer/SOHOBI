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

function binColor(type) {
  if (type === "loss") return "rgba(239,68,68,0.7)";
  if (type === "p20") return "rgba(234,179,8,0.7)";
  return "rgba(20,184,166,0.7)";
}

function fmt(v) {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}백만`;
  if (Math.abs(v) >= 10_000) return `${Math.round(v / 10_000)}만`;
  return String(v);
}

export default function SimulationChart({ chartData }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartData?.bins?.length || !canvasRef.current) return;

    if (chartRef.current) {
      chartRef.current.destroy();
      chartRef.current = null;
    }

    const bins = chartData.bins;
    const labels = bins.map((b) => fmt(b.left));
    const data = bins.map((b) => b.count);
    const colors = bins.map((b) => binColor(b.type));

    chartRef.current = new Chart(canvasRef.current, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "시뮬레이션 빈도",
            data,
            backgroundColor: colors,
            borderRadius: 3,
            borderSkipped: false,
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
              label: (ctx) => `${ctx.parsed.y}회`,
              title: (items) => {
                const b = bins[items[0].dataIndex];
                return `${fmt(b.left)} ~ ${fmt(b.right)}`;
              },
            },
          },
        },
        scales: {
          x: {
            ticks: {
              color: "var(--muted-foreground)",
              font: { size: 10 },
              maxRotation: 45,
              autoSkip: true,
              maxTicksLimit: 10,
            },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
          y: {
            ticks: { color: "var(--muted-foreground)", font: { size: 10 } },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
        },
      },
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [chartData]);

  if (!chartData?.bins?.length) return null;

  return (
    <div className="glass rounded-2xl p-4 mt-3">
      <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground flex-wrap">
        <span>
          평균 <strong className="text-foreground">{fmt(chartData.avg)}원</strong>
        </span>
        <span>
          하위20% <strong style={{ color: "var(--grade-b)" }}>{fmt(chartData.p20)}원</strong>
        </span>
        <span>
          범위 <strong className="text-foreground">{fmt(chartData.min)} ~ {fmt(chartData.max)}원</strong>
        </span>
        <span className="ml-auto flex items-center gap-2">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: "rgba(239,68,68,0.7)" }} /> 손실
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: "rgba(234,179,8,0.7)" }} /> 하위20%
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: "rgba(20,184,166,0.7)" }} /> 수익
        </span>
      </div>
      <div style={{ height: 200 }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
