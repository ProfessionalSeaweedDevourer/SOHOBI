// 공식 프론트 위치: frontend\src\components\map\controls\MapControls.jsx
import "./MapControls.css";

export default function MapControls({
   dongMode,
   onDongMode,
   dongLoading,
   loading,
   storeSearchOn,
   onStoreSearchToggle,
   onStoreSearch,
}) {
   return (
      <div className="mv-map-controls">
         {/* 로딩 */}
         {(dongLoading || loading) && (
            <div className="mv-map-controls__loading">
               ⏳ {dongLoading ? "동 데이터 로딩 중..." : "상가 조회 중..."}
            </div>
         )}

         {/* 점포수 / 매출 / 부동산 버튼 */}
         <div className="mv-map-controls__mode-row">
            {[
               { mode: "store", label: "점포수", activeColor: "#7C3AED" },
               { mode: "sales", label: "매출", activeColor: "#059669" },
               { mode: "realestate", label: "부동산", activeColor: "#2563EB" },
            ].map(({ mode, label, activeColor }) => {
               const isActive = dongMode === mode;
               return (
                  <button
                     key={mode}
                     onClick={() => onDongMode(mode)}
                     className="mv-mode-btn"
                     style={
                        isActive
                           ? {
                                background: activeColor,
                                borderColor: activeColor,
                                color: "#fff",
                             }
                           : {}
                     }
                  >
                     {label}
                     {isActive ? " ✓" : ""}
                  </button>
               );
            })}
         </div>

         {/* 상가 전체 검색 ON/OFF 토글 */}
         <div className="mv-map-controls__store-row">
            <button
               onClick={onStoreSearchToggle}
               className="mv-store-btn"
               style={
                  storeSearchOn
                     ? {
                          background: "#0891B2",
                          borderColor: "#0891B2",
                          color: "#fff",
                       }
                     : {}
               }
            >
               🏪 상가 검색 {storeSearchOn ? "ON ✓" : "OFF"}
            </button>
            {storeSearchOn && (
               <button
                  onClick={onStoreSearch}
                  className="mv-refresh-btn"
                  disabled={loading}
               >
                  {loading ? "⏳" : "🔄"}
               </button>
            )}
         </div>
      </div>
   );
}
