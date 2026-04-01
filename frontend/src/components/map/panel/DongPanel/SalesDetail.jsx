import { formatAmt } from "./formatHelpers";
import { GenderDonut } from "./GenderDonut";
import { BarRow } from "./BarRow";

// ── 성별/연령대/주중주말 (하단) ───────────────────────────────
export function SalesDetail({ d }) {
   return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
         {/* 성별 도넛 */}
         {(d.sales_male || d.sales_female) && (
            <div
               style={{ background: "#f8fafc", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#475569",
                     marginBottom: 10,
                  }}
               >
                  👤 성별 매출
               </div>
               <GenderDonut male={d.sales_male} female={d.sales_female} />
            </div>
         )}
         {/* 연령대 */}
         {(d.age20 || d.age30 || d.age40 || d.age50) && (
            <div
               style={{ background: "#f8fafc", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#475569",
                     marginBottom: 8,
                  }}
               >
                  🎂 연령대 매출
               </div>
               {[
                  ["20대", d.age20, "#6366f1"],
                  ["30대", d.age30, "#0ea5e9"],
                  ["40대", d.age40, "#10b981"],
                  ["50대", d.age50, "#f59e0b"],
               ].map(([label, val, col]) => {
                  const pct =
                     d.sales > 0 ? Math.round(((val || 0) / d.sales) * 100) : 0;
                  return (
                     <div key={label} style={{ marginBottom: 6 }}>
                        <div
                           style={{
                              display: "flex",
                              justifyContent: "space-between",
                              fontSize: 12,
                              marginBottom: 2,
                           }}
                        >
                           <span>{label}</span>
                           <span style={{ fontWeight: 700 }}>
                              {formatAmt(val)} ({pct}%)
                           </span>
                        </div>
                        <div
                           style={{
                              height: 5,
                              background: "#e2e8f0",
                              borderRadius: 3,
                              overflow: "hidden",
                           }}
                        >
                           <div
                              style={{
                                 width: `${pct}%`,
                                 height: "100%",
                                 background: col,
                                 borderRadius: 3,
                              }}
                           />
                        </div>
                     </div>
                  );
               })}
            </div>
         )}
         {/* 주중/주말 */}
         <div style={{ background: "#f8fafc", borderRadius: 12, padding: 14 }}>
            <div
               style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#475569",
                  marginBottom: 8,
               }}
            >
               📅 주중/주말
            </div>
            <BarRow
               label="주중"
               val={d.sales_mdwk}
               total={d.sales}
               color="#3b82f6"
            />
            <BarRow
               label="주말"
               val={d.sales_wkend}
               total={d.sales}
               color="#8b5cf6"
            />
         </div>
      </div>
   );
}
