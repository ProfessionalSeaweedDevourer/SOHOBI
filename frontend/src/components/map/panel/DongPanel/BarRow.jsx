import { formatAmt } from "./formatHelpers";

// ── 막대 차트 행 컴포넌트 ─────────────────────────────────────
export function BarRow({ label, val, total, color }) {
   const pct = total > 0 ? Math.round((val / total) * 100) : 0;
   return (
      <div style={{ marginBottom: 8 }}>
         <div
            style={{
               display: "flex",
               justifyContent: "space-between",
               fontSize: 12,
               marginBottom: 3,
            }}
         >
            <span>{label}</span>
            <span style={{ fontWeight: 700 }}>
               {formatAmt(val)} ({pct}%)
            </span>
         </div>
         <div
            style={{
               height: 6,
               background: "#e2e8f0",
               borderRadius: 3,
               overflow: "hidden",
            }}
         >
            <div
               style={{
                  width: `${pct}%`,
                  height: "100%",
                  background: color,
                  borderRadius: 3,
               }}
            />
         </div>
      </div>
   );
}
