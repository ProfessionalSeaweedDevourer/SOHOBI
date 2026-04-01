import { SVC_COLOR, SVC_LABEL } from "./constants";

export function StorePanel({ d }) {
   const rows = d?.data || [];
   if (!rows.length)
      return (
         <div
            style={{
               color: "#bbb",
               fontSize: 13,
               textAlign: "center",
               marginTop: 40,
            }}
         >
            점포수 데이터 없음
         </div>
      );
   const total = rows.reduce((s, r) => s + (Number(r.stor_co) || 0), 0);
   const SVC_COLOR_STORE = {
      I2: "#FF6B6B",
      G2: "#FF9800",
      S2: "#4ecdc4",
      L1: "#2196F3",
      I1: "#9C27B0",
      P1: "#F59E0B",
      Q1: "#E03131",
      R1: "#2F9E44",
      M1: "#1971C2",
      N1: "#607D8B",
   };
   return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
         {/* 총 점포수 */}
         <div style={{ background: "#f5f3ff", borderRadius: 12, padding: 14 }}>
            <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>
               총 점포수
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, color: "#7C3AED" }}>
               {Math.round(total)}개
            </div>
         </div>
         {/* 업종별 점포수 */}
         <div style={{ background: "#f8fafc", borderRadius: 12, padding: 14 }}>
            <div
               style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#475569",
                  marginBottom: 10,
               }}
            >
               🏪 업종별 점포수
            </div>
            {rows.map((r) => {
               const cnt = Number(r.stor_co) || 0;
               const pct = total > 0 ? Math.round((cnt / total) * 100) : 0;
               const col = SVC_COLOR_STORE[r.svc_cd] || "#888";
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
                           {Math.round(cnt)}개 ({pct}%)
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
                     {/* 개업률/폐업률 */}
                     <div
                        style={{
                           display: "flex",
                           gap: 10,
                           marginTop: 3,
                           fontSize: 10,
                           color: "#94a3b8",
                        }}
                     >
                        <span>
                           개업률{" "}
                           <span style={{ color: "#059669", fontWeight: 700 }}>
                              {r.opbiz_rt}%
                           </span>
                        </span>
                        <span>
                           폐업률{" "}
                           <span style={{ color: "#dc2626", fontWeight: 700 }}>
                              {r.clsbiz_rt}%
                           </span>
                        </span>
                        {r.frc_stor_co > 0 && (
                           <span>
                              프랜차이즈{" "}
                              <span
                                 style={{ color: "#7C3AED", fontWeight: 700 }}
                              >
                                 {Math.round(r.frc_stor_co)}개
                              </span>
                           </span>
                        )}
                     </div>
                  </div>
               );
            })}
         </div>
         <div style={{ fontSize: 9, color: "#94a3b8", textAlign: "center" }}>
            ※ 출처: 소상공인시장진흥공단 골목상권 점포수
         </div>
      </div>
   );
}
