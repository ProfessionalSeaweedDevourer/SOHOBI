import { useEffect, useRef } from "react";
import { Chart } from "chart.js/auto";

export default function SimulationChart({ chartData }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);
    
    useEffect(() => {
        if (!chartData || !canvasRef.current) return;

        if (chartRef.current) chartRef.current.destroy();
        
        const labels = chartData.bins.map(b => 
            `${Math.round(b.left / 10000)}만`
        );
        const data = chartData.bins.map(b => b.count);
    const colors = chartData.bins.map(b =>
        b.type === "loss"   ? "#E24B4A" :
        b.type === "p20"    ? "#EF9F27" : "#378ADD"
    );
    
    chartRef.current = new Chart(canvasRef.current, {
        type: "bar",
      data: {
          labels,
          datasets: [{
              data,
              backgroundColor: colors,
              borderWidth: 0,
              barPercentage: 1.0,
              categoryPercentage: 1.0,
            }]
        },
      options: {
          responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    title: (items) => items[0].label + "원 구간",
                    label: (item) => "빈도: " + item.raw + "회",
                }
            }
        },
        scales: {
            x: { ticks: { maxTicksLimit: 8 }, grid: { display: false } },
            y: { ticks: { maxTicksLimit: 5 } }
        }
      }
    });

    return () => chartRef.current?.destroy();
  }, [chartData]);

  if (!chartData) return null;
  if (!chartData.bins) return null;
  
  return (
    <div className="mt-4">
      <div className="flex gap-4 text-xs text-slate-400 mb-2">
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-[#E24B4A] mr-1"/>손실</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-[#EF9F27] mr-1"/>하위 20%</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-[#378ADD] mr-1"/>수익</span>
      </div>
      <div style={{ position: "relative", height: "200px" }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}