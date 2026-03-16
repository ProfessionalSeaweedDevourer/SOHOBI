// components/MapControls.jsx


// ── 메인 컴포넌트: 상단 컨트롤 바 + 동 모드 버튼 ────────────
export default function MapControls({
   clickMode, setClickMode,
   nearbyCount, loading,
   onClear,
   dongMode, onDongMode, dongLoading,
   currentGuNm,
}) {
   return (
      <>
         {
// ── 상단 컨트롤 바 ─────────────────────────────────────────────
/* 상단 컨트롤 바 */}
         <div className="mv-ctrl-bar">
            <button
               className={`mv-ctrl-btn ${clickMode ? "mv-ctrl-btn--on" : "mv-ctrl-btn--off"}`}
               onClick={() => setClickMode((v) => !v)}
            >
               {clickMode ? "📍 반경분석 ON" : "📍 반경분석 OFF"}
            </button>
            {nearbyCount !== null && (
               <span className="mv-ctrl-badge">반경 500m · {nearbyCount}건</span>
            )}
            {loading && (
               <span className="mv-ctrl-loading">DB 조회 중...</span>
            )}
            {nearbyCount !== null && (
               <button className="mv-ctrl-clear" onClick={onClear}>✕ 초기화</button>
            )}
         </div>

         {
// ── 동 모드 버튼 (왼쪽 하단) ──────────────────────────────────
/* 동 모드 버튼 (왼쪽 하단) */}
         <div style={{
            position: "absolute", bottom: 50, left: 16,
            zIndex: 200, display: "flex", flexDirection: "column", gap: 6,
         }}>
            {currentGuNm && dongMode !== "none" && (
               <div style={{
                  background: "rgba(255,255,255,0.95)", borderRadius: 8,
                  padding: "4px 10px", fontSize: 11, color: "#555",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.12)", textAlign: "center",
               }}>
                  📍 {currentGuNm}
               </div>
            )}
            {!currentGuNm && dongMode !== "none" && (
               <div style={{
                  background: "#fffbeb", border: "1px solid #fbbf24",
                  borderRadius: 8, padding: "5px 10px", fontSize: 11, color: "#92400e",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
               }}>
                  ⚠️ 지적도를 먼저 클릭하세요
               </div>
            )}
            {dongLoading && (
               <div style={{
                  background: "rgba(255,255,255,0.95)", borderRadius: 8,
                  padding: "5px 12px", fontSize: 11, color: "#555",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
               }}>
                  ⏳ 동 데이터 로딩 중...
               </div>
            )}
            {[
               { mode: "realestate", label: "🏢 실거래가", activeColor: "#2563EB" },
               { mode: "sales",      label: "📊 매출",     activeColor: "#059669" },
            ].map(({ mode, label, activeColor }) => {
               const isActive = dongMode === mode;
               return (
                  <button
                     key={mode}
                     onClick={() => onDongMode(mode)}
                     style={{
                        border:       `2px solid ${isActive ? activeColor : "#e5e7eb"}`,
                        borderRadius: 10,
                        padding:      "7px 14px",
                        fontSize:     12,
                        fontWeight:   700,
                        cursor:       "pointer",
                        background:   isActive ? activeColor : "#fff",
                        color:        isActive ? "#fff" : "#555",
                        boxShadow:    "0 2px 8px rgba(0,0,0,0.1)",
                        transition:   "all 0.18s",
                        whiteSpace:   "nowrap",
                     }}
                  >
                     {label}{isActive ? " ✓" : ""}
                  </button>
               );
            })}
         </div>
      </>
   );
}