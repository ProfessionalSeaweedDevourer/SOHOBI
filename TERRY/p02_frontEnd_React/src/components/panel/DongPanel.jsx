import { SvcPanel } from "./DongPanel/SvcPanel";
import { SVC_LABEL } from "./DongPanel/constants";
import { StorePanel } from "./DongPanel/StorePanel";
import { RealEstatePanel } from "./DongPanel/RealEstatePanel";
import { SalesSummary } from "./DongPanel/SalesSummary";
import { SalesDetail } from "./DongPanel/SalesDetail";

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

         {/* 년도/분기 선택 - 매출 모드만, DB에 있는 데이터만 표시 */}
         {quarters.length > 0 && !isRE && !isStore && (
            <div
               style={{
                  padding: "8px 12px",
                  background: "#f8fafc",
                  borderBottom: "1px solid #e5e7eb",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
               }}
            >
               <span style={{ fontSize: 11, color: "#666", flexShrink: 0 }}>
                  📅
               </span>
               {/* 년도 선택 */}
               <select
                  value={
                     selectedQuarter ? String(selectedQuarter).slice(0, 4) : ""
                  }
                  onChange={(e) => {
                     const yr = e.target.value;
                     // 해당 년도의 첫 번째 분기 자동 선택
                     const first = quarters.find((q) =>
                        String(q).startsWith(yr),
                     );
                     if (first) onQuarterChange(first);
                  }}
                  style={{
                     fontSize: 12,
                     padding: "3px 6px",
                     borderRadius: 6,
                     border: "1px solid #d1d5db",
                     background: "#fff",
                  }}
               >
                  {[...new Set(quarters.map((q) => String(q).slice(0, 4)))]
                     .sort()
                     .reverse()
                     .map((yr) => (
                        <option key={yr} value={yr}>
                           {yr}년
                        </option>
                     ))}
               </select>
               {/* 분기 선택 */}
               <select
                  value={selectedQuarter || ""}
                  onChange={(e) => onQuarterChange(e.target.value)}
                  style={{
                     fontSize: 12,
                     padding: "3px 6px",
                     borderRadius: 6,
                     border: "1px solid #d1d5db",
                     background: "#fff",
                  }}
               >
                  {quarters
                     .filter((q) =>
                        String(q).startsWith(
                           selectedQuarter
                              ? String(selectedQuarter).slice(0, 4)
                              : String(quarters[quarters.length - 1]).slice(
                                   0,
                                   4,
                                ),
                        ),
                     )
                     .map((q) => (
                        <option key={q} value={q}>
                           {String(q).slice(4)}분기
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
