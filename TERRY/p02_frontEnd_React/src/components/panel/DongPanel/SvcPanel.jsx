import { formatAmt } from "./formatHelpers";
import { SVC_COLOR, SVC_LABEL } from "./constants";
import { BarRow } from "./BarRow";

// ── 업종별 매출 패널 ──────────────────────────────────────────

// SvcPanel: SANGKWON_SALES JOIN SVC_INDUTY_MAP → SVC_CD(대분류) 기준 매출 합산
// svcData: [{ svc_cd, svc_nm, tot_sales_amt, ... }]
export function SvcPanel({ svcData }) {
   if (!svcData || svcData.length === 0) return null;
   const total = svcData.reduce(
      (s, r) => s + (Number(r.tot_sales_amt) || 0),
      0,
   );
   if (total === 0) return null;
   return (
      <div style={{ background: "#f8fafc", borderRadius: 12, padding: 14 }}>
         <div
            style={{
               fontSize: 11,
               fontWeight: 700,
               color: "#475569",
               marginBottom: 10,
            }}
         >
            🏪 업종별 매출
         </div>
         {svcData.map((r) => {
            const amt = Number(r.tot_sales_amt) || 0;
            const pct = Math.round((amt / total) * 100);
            const col = SVC_COLOR[r.svc_cd] || "#888";
            const lbl = SVC_LABEL[r.svc_cd] || r.svc_nm;
            return (
               <div key={r.svc_cd} style={{ marginBottom: 9 }}>
                  <div
                     style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: 12,
                        marginBottom: 3,
                     }}
                  >
                     <span style={{ fontWeight: 600 }}>{lbl}</span>
                     <span style={{ color: col, fontWeight: 700 }}>
                        {formatAmt(amt)} ({pct}%)
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
                           background: col,
                           borderRadius: 3,
                        }}
                     />
                  </div>
               </div>
            );
         })}
      </div>
   );
}

// StorePanel: SANGKWON_STORE 기준 업종별 점포수/개폐업률
// d: { data: [{ svc_cd, svc_nm, stor_co, frc_stor_co, opbiz_rt, clsbiz_rt }] }
