// components/DongPanel.jsx

// ── 금액 포맷 헬퍼 ─────────────────────────────────────────────
function formatAmt(v) {
   if (!v || v === 0) return "-";
   if (v >= 1e8) return `${(v / 1e8).toFixed(1)}억`;
   if (v >= 1e4) return `${Math.round(v / 1e4)}만`;
   return `${v}`;
}

// ── 막대 차트 행 컴포넌트 ─────────────────────────────────────
function BarRow({ label, val, total, color }) {
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

// ── 업종별 매출 패널 ──────────────────────────────────────────
const SVC_COLOR = {
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
const SVC_LABEL = {
   I2: "음식",
   G2: "소매",
   S2: "수리·개인",
   L1: "부동산",
   I1: "숙박",
   P1: "교육",
   Q1: "의료",
   R1: "스포츠",
   M1: "전문·기술",
   N1: "시설관리",
};

// SvcPanel: SANGKWON_SALES JOIN SVC_INDUTY_MAP → SVC_CD(대분류) 기준 매출 합산
// svcData: [{ svc_cd, svc_nm, tot_sales_amt, ... }]
function SvcPanel({ svcData }) {
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
function StorePanel({ d }) {
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

// ── 실거래가 패널 ─────────────────────────────────────────────
function RealEstatePanel({ d }) {
   return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
         {d?.매매?.건수 > 0 && (
            <div
               style={{ background: "#eff6ff", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#2563eb",
                     marginBottom: 8,
                  }}
               >
                  🏢 매매
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.매매.건수}건`],
                     ["평균", d.매매.평균가],
                     ["최저", d.매매.최저가],
                     ["최고", d.매매.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#1e40af",
                           }}
                        >
                           {v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
               {d.매매.목록?.slice(0, 3).map((item, i) => (
                  <div
                     key={i}
                     style={{
                        fontSize: 11,
                        color: "#475569",
                        marginTop: 6,
                        lineHeight: 1.5,
                        borderTop: i === 0 ? "1px solid #dbeafe" : "none",
                        paddingTop: i === 0 ? 6 : 0,
                     }}
                  >
                     <span style={{ color: "#94a3b8" }}>
                        {item.계약일?.slice(0, 6)}
                     </span>{" "}
                     <span style={{ fontWeight: 700, color: "#2563eb" }}>
                        {item.거래금액}만원
                     </span>
                     {item.건물명 && (
                        <span style={{ color: "#94a3b8" }}>
                           {" "}
                           · {item.건물명}
                        </span>
                     )}
                     {item.용도 && (
                        <span style={{ color: "#94a3b8", fontSize: 10 }}>
                           {" "}
                           ({item.용도})
                        </span>
                     )}
                  </div>
               ))}
            </div>
         )}
         {d?.전세?.건수 > 0 && (
            <div
               style={{ background: "#f0fdf4", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#059669",
                     marginBottom: 8,
                  }}
               >
                  🔑 전세
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.전세.건수}건`],
                     ["평균", d.전세.평균가],
                     ["최저", d.전세.최저가],
                     ["최고", d.전세.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#065f46",
                           }}
                        >
                           {v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         )}
         {d?.월세?.건수 > 0 && (
            <div
               style={{ background: "#fefce8", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#a16207",
                     marginBottom: 4,
                  }}
               >
                  💰 월세
               </div>
               <div style={{ fontSize: 12, color: "#854d0e" }}>
                  {d.월세.건수}건
               </div>
            </div>
         )}
         {d?.has_data === false && (
            <div
               style={{
                  color: "#bbb",
                  fontSize: 13,
                  textAlign: "center",
                  marginTop: 20,
               }}
            >
               최근 3년 실거래 데이터 없음
            </div>
         )}
      </div>
   );
}

// GenderDonut: SVG 도넛 차트 - 남성(#2563eb) / 여성(#ec4899)
// male/female: 원 금액 (만원 단위 아님, formatAmt으로 표시)
function GenderDonut({ male, female }) {
   const total = (male || 0) + (female || 0);
   if (!total) return null;
   const malePct = Math.round(((male || 0) / total) * 100);
   const femalePct = 100 - malePct;
   // SVG 도넛: cx=50 cy=50 r=36 (둘레 ≈ 226)
   const R = 36,
      CX = 50,
      CY = 50;
   const circ = 2 * Math.PI * R;
   const maleDash = (malePct / 100) * circ;
   const femaleDash = circ - maleDash;
   return (
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
         <svg width="90" height="90" viewBox="0 0 100 100">
            {/* 여성 (배경) */}
            <circle
               cx={CX}
               cy={CY}
               r={R}
               fill="none"
               stroke="#fce7f3"
               strokeWidth="14"
            />
            {/* 남성 */}
            <circle
               cx={CX}
               cy={CY}
               r={R}
               fill="none"
               stroke="#2563eb"
               strokeWidth="14"
               strokeDasharray={`${maleDash} ${femaleDash}`}
               strokeDashoffset={circ * 0.25}
               strokeLinecap="round"
            />
            {/* 여성 위에 덮기 */}
            <circle
               cx={CX}
               cy={CY}
               r={R}
               fill="none"
               stroke="#ec4899"
               strokeWidth="14"
               strokeDasharray={`${femaleDash} ${maleDash}`}
               strokeDashoffset={circ * 0.25 - maleDash}
               strokeLinecap="round"
            />
            <text
               x={CX}
               y={CY - 5}
               textAnchor="middle"
               fontSize="13"
               fontWeight="700"
               fill="#1e293b"
            >
               {malePct}%
            </text>
            <text
               x={CX}
               y={CY + 10}
               textAnchor="middle"
               fontSize="9"
               fill="#64748b"
            >
               남성
            </text>
         </svg>
         <div
            style={{
               display: "flex",
               flexDirection: "column",
               gap: 8,
               flex: 1,
            }}
         >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
               <div
                  style={{
                     width: 10,
                     height: 10,
                     borderRadius: "50%",
                     background: "#2563eb",
                     flexShrink: 0,
                  }}
               />
               <span style={{ fontSize: 12 }}>남성</span>
               <span
                  style={{
                     marginLeft: "auto",
                     fontWeight: 700,
                     fontSize: 12,
                     color: "#2563eb",
                  }}
               >
                  {malePct}% ({formatAmt(male)})
               </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
               <div
                  style={{
                     width: 10,
                     height: 10,
                     borderRadius: "50%",
                     background: "#ec4899",
                     flexShrink: 0,
                  }}
               />
               <span style={{ fontSize: 12 }}>여성</span>
               <span
                  style={{
                     marginLeft: "auto",
                     fontWeight: 700,
                     fontSize: 12,
                     color: "#ec4899",
                  }}
               >
                  {femalePct}% ({formatAmt(female)})
               </span>
            </div>
         </div>
      </div>
   );
}

// ── 총매출 요약 (상단) ────────────────────────────────────────
function SalesSummary({ d, panelColor, panelBg, avg }) {
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

// ── 성별/연령대/주중주말 (하단) ───────────────────────────────
function SalesDetail({ d }) {
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

// ── 메인 컴포넌트 ─────────────────────────────────────────────
export default function DongPanel({
   dongPanel,
   onClose,
   quarters = [],
   selectedQuarter,
   onQuarterChange,
   svcData,
   selectedSvc,
   onSvcChange,
}) {
   if (!dongPanel) return null;

   const d = dongPanel.apiData;
   const isRE = dongPanel.mode === "realestate";
   const isStore = dongPanel.mode === "store";
   const panelColor = isRE ? "#2563EB" : isStore ? "#7C3AED" : "#059669";
   const panelBg = isRE ? "#eff6ff" : isStore ? "#f5f3ff" : "#f0fdf4";

   return (
      <div className="mv-dong-panel">
         <div
            className="mv-dong-panel__header"
            style={{ background: panelColor }}
         >
            <div className="mv-dong-panel__header-row">
               <div>
                  <div className="mv-dong-panel__gu">{dongPanel.guNm}</div>
                  <div className="mv-dong-panel__name">
                     {dongPanel.dongNm || dongPanel.admNm}
                  </div>
               </div>
               <button onClick={onClose} className="mv-dong-panel__close">
                  ✕
               </button>
            </div>
            <div className="mv-dong-panel__mode-label">
               {isRE
                  ? "🏢 실거래가 분석"
                  : isStore
                    ? "🏪 점포수 분석"
                    : "📊 상권 매출 분석"}
            </div>
         </div>

         {/* 분기 선택 드롭다운 - 매출 모드만 */}
         {quarters.length > 0 && !isRE && !isStore && (
            <div
               style={{
                  padding: "8px 12px",
                  background: "#f8fafc",
                  borderBottom: "1px solid #e5e7eb",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
               }}
            >
               <span style={{ fontSize: 11, color: "#666", flexShrink: 0 }}>
                  📅 분기
               </span>
               <select
                  value={selectedQuarter || ""}
                  onChange={(e) => onQuarterChange(e.target.value)}
                  style={{
                     flex: 1,
                     fontSize: 12,
                     padding: "3px 6px",
                     borderRadius: 6,
                     border: "1px solid #d1d5db",
                     background: "#fff",
                  }}
               >
                  {quarters.map((q) => (
                     <option key={q} value={q}>
                        {String(q).replace(/(\d{4})(\d)/, "$1년 $2분기")}
                     </option>
                  ))}
               </select>
            </div>
         )}
         {/* 업종 필터 드롭다운 - 매출 모드만 */}
         {svcData && svcData.length > 0 && !isRE && !isStore && (
            <div
               style={{
                  padding: "6px 12px",
                  background: "#f8fafc",
                  borderBottom: "1px solid #e5e7eb",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
               }}
            >
               <span style={{ fontSize: 11, color: "#666", flexShrink: 0 }}>
                  🏪 업종
               </span>
               <select
                  value={selectedSvc || ""}
                  onChange={(e) => onSvcChange?.(e.target.value)}
                  style={{
                     flex: 1,
                     fontSize: 12,
                     padding: "3px 6px",
                     borderRadius: 6,
                     border: "1px solid #d1d5db",
                     background: "#fff",
                  }}
               >
                  <option value="">전체</option>
                  {svcData.map((r) => (
                     <option key={r.svc_cd} value={r.svc_cd}>
                        {SVC_LABEL[r.svc_cd] || r.svc_nm}
                     </option>
                  ))}
               </select>
            </div>
         )}

         <div className="mv-dong-panel__body">
            {!d ? (
               <div
                  style={{
                     color: "#bbb",
                     fontSize: 13,
                     textAlign: "center",
                     marginTop: 40,
                  }}
               >
                  데이터 없음
               </div>
            ) : isRE ? (
               <RealEstatePanel d={d} />
            ) : isStore ? (
               <StorePanel d={d} />
            ) : (
               <>
                  {/* ① 총매출 / 평균比 */}
                  <SalesSummary
                     d={d}
                     panelColor={panelColor}
                     panelBg={panelBg}
                     avg={dongPanel.avg}
                  />
                  {/* ② 업종별 매출 - SVC_CD 기준 SANGKWON_SALES JOIN SVC_INDUTY_MAP 합산 */}
                  {svcData && svcData.length > 0 && (
                     <>
                        <div
                           style={{
                              height: 1,
                              background: "#e5e7eb",
                              margin: "4px 0",
                           }}
                        />
                        <SvcPanel svcData={svcData} />
                        <div
                           style={{
                              height: 1,
                              background: "#e5e7eb",
                              margin: "4px 0",
                           }}
                        />
                     </>
                  )}
                  {/* ③ 성별 도넛 / 연령대 / 주중주말 - V_SANGKWON_LATEST 뷰 기반 */}
                  <SalesDetail d={d} />
                  {/* ※ 출처: 소상공인시장진흥공단 골목상권 매출 (분기별 행정동 집계) */}
               </>
            )}
         </div>
      </div>
   );
}
