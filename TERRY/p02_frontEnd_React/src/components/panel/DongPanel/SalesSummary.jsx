import { formatAmt } from "./formatHelpers";

// ── 총매출 요약 (상단) ────────────────────────────────────────
export function SalesSummary({ d, panelColor, panelBg, avg }) {
   return (
      <div style={{ background: panelBg, borderRadius: 12, padding: 14 }}>
         <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>
            총 매출
         </div>
         <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: panelColor }}>
               {formatAmt(d.sales)}
            </div>
            {avg?.sales && (
               <div
                  style={{
                     fontSize: 11,
                     color: d.sales >= avg.sales ? "#059669" : "#dc2626",
                     fontWeight: 700,
                  }}
               >
                  {d.sales >= avg.sales ? "▲" : "▼"} 평균比{" "}
                  {Math.abs(Math.round((d.sales / avg.sales - 1) * 100))}%
               </div>
            )}
         </div>
         <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
            {d.quarter &&
               ` · ${String(d.quarter).replace(/(\d{4})(\d)/, "$1년 $2분기")}`}
         </div>
      </div>
   );
}
