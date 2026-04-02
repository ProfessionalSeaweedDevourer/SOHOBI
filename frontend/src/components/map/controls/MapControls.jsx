// 공식 프론트 위치: frontend\src\components\map\controls\MapControls.jsx

export default function MapControls({
   dongMode,
   onDongMode,
   dongLoading,
   currentGuNm,
   nearbyCount,
   loading,
   storeSearchOn,
   onStoreSearchToggle,
   onStoreSearch,
}) {
   return (
      <div
         style={{
            position: "absolute",
            bottom: 50,
            left: 16,
            zIndex: 200,
            display: "flex",
            flexDirection: "column",
            gap: 6,
         }}
      >
         {/* 현재 구 이름 */}
         {currentGuNm && (
            <div
               style={{
                  background: "rgba(255,255,255,0.95)",
                  borderRadius: 8,
                  padding: "4px 10px",
                  fontSize: 11,
                  color: "#555",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                  textAlign: "center",
               }}
            >
               📍 {currentGuNm}
               {nearbyCount !== null &&
                  ` · ${nearbyCount.toLocaleString()}개 상가`}
            </div>
         )}

         {/* 로딩 */}
         {(dongLoading || loading) && (
            <div
               style={{
                  background: "rgba(255,255,255,0.95)",
                  borderRadius: 8,
                  padding: "5px 12px",
                  fontSize: 11,
                  color: "#555",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
               }}
            >
               ⏳ {dongLoading ? "동 데이터 로딩 중..." : "상가 조회 중..."}
            </div>
         )}

         {/* 점포수 / 매출 / 부동산 버튼 */}
         <div style={{ display: "flex", flexDirection: "row", gap: 6 }}>
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
                     style={{
                        border: `2px solid ${isActive ? activeColor : "#e5e7eb"}`,
                        borderRadius: 10,
                        padding: "7px 12px",
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                        background: isActive ? activeColor : "#fff",
                        color: isActive ? "#fff" : "#555",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                        transition: "all 0.18s",
                        whiteSpace: "nowrap",
                     }}
                  >
                     {label}
                     {isActive ? " ✓" : ""}
                  </button>
               );
            })}
         </div>

         {/* 상가 전체 검색 ON/OFF 토글 */}
         <div style={{ display: "flex", gap: 6 }}>
            <button
               onClick={onStoreSearchToggle}
               style={{
                  border: `2px solid ${storeSearchOn ? "#0891B2" : "#e5e7eb"}`,
                  borderRadius: 10,
                  padding: "7px 12px",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  background: storeSearchOn ? "#0891B2" : "#fff",
                  color: storeSearchOn ? "#fff" : "#555",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                  whiteSpace: "nowrap",
                  flex: 1,
               }}
            >
               🏪 상가 검색 {storeSearchOn ? "ON ✓" : "OFF"}
            </button>
            {storeSearchOn && (
               <button
                  onClick={onStoreSearch}
                  style={{
                     border: "2px solid #0891B2",
                     borderRadius: 10,
                     padding: "7px 10px",
                     fontSize: 12,
                     fontWeight: 700,
                     cursor: "pointer",
                     background: "#fff",
                     color: "#0891B2",
                     boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                     whiteSpace: "nowrap",
                  }}
               >
                  🔄
               </button>
            )}
         </div>
      </div>
   );
}
