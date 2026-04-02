// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\popup\StorePopup.jsx
// 공식 프론트 위치: frontend\src\components\map\popup\StorePopup.jsx
import { useState } from "react";

const CAT_STYLE = {
   I2: { color: "#FF6B6B", bg: "#FFF0F0", label: "음식" },
   G2: { color: "#FF9800", bg: "#FFF8F0", label: "소매" },
   S2: { color: "#4ecdc4", bg: "#F0FAFA", label: "수리·개인" },
   L1: { color: "#2196F3", bg: "#F0F4FF", label: "부동산" },
   I1: { color: "#9C27B0", bg: "#F8F0FF", label: "숙박" },
   P1: { color: "#F59E0B", bg: "#FFFDF0", label: "교육" },
   Q1: { color: "#E03131", bg: "#FFF0F0", label: "의료" },
   R1: { color: "#2F9E44", bg: "#F0FFF4", label: "스포츠" },
   M1: { color: "#1971C2", bg: "#F0F4FF", label: "전문·기술" },
   N1: { color: "#607D8B", bg: "#F0F4F4", label: "시설관리" },
};

function getCatStyle(catCd) {
   return CAT_STYLE[catCd] || { color: "#555", bg: "#F5F5F5", label: "기타" };
}

// ── 클러스터 목록 뷰 ────────────────────────────────────────────
function ClusterListView({ stores, onSelect, onClose }) {
   const [filter, setFilter] = useState("");
   const filtered = filter
      ? stores.filter(
           (s) => s.STORE_NM?.includes(filter) || s.CAT_NM?.includes(filter),
        )
      : stores;

   return (
      <div style={{ padding: "12px 16px 16px" }}>
         <div
            style={{
               display: "flex",
               justifyContent: "space-between",
               alignItems: "center",
               marginBottom: 10,
            }}
         >
            <span style={{ fontSize: 14, fontWeight: 700, color: "#111" }}>
               🏪 상가 {stores.length}개
            </span>
            <button
               onClick={onClose}
               style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#bbb",
                  fontSize: 16,
               }}
            >
               ✕
            </button>
         </div>
         <input
            type="text"
            placeholder="상호명·업종 검색..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
               width: "100%",
               padding: "6px 10px",
               borderRadius: 8,
               border: "1px solid #e5e7eb",
               fontSize: 12,
               marginBottom: 8,
               boxSizing: "border-box",
               outline: "none",
            }}
         />
         <div style={{ overflowY: "auto", maxHeight: 320 }}>
            {filtered.map((s, i) => {
               const c = getCatStyle(s.CAT_CD);
               return (
                  <div
                     key={`${s.STORE_ID || "x"}-${i}`}
                     onClick={() => onSelect(s)}
                     style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 4px",
                        cursor: "pointer",
                        borderBottom: "1px solid #f5f5f5",
                     }}
                  >
                     <div
                        style={{
                           width: 8,
                           height: 8,
                           borderRadius: "50%",
                           background: c.color,
                           flexShrink: 0,
                        }}
                     />
                     <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 600,
                              color: "#222",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                           }}
                        >
                           {s.STORE_NM}
                        </div>
                        <div style={{ fontSize: 10, color: "#aaa" }}>
                           {c.label} · {s.ADM_NM}
                        </div>
                     </div>
                  </div>
               );
            })}
            {filtered.length === 0 && (
               <div
                  style={{
                     textAlign: "center",
                     color: "#bbb",
                     fontSize: 12,
                     padding: 16,
                  }}
               >
                  검색 결과 없음
               </div>
            )}
         </div>
      </div>
   );
}

// ── 단일 상가 상세 뷰 ──────────────────────────────────────────
function StoreDetailView({
   popup,
   kakaoDetail,
   loadingDetail,
   onClose,
   nearbyStores,
   onStoreSelect,
   onBack,
   onLandValue,
}) {
   const cat = getCatStyle(popup.CAT_CD);
   return (
      <div style={{ padding: "12px 16px 16px" }}>
         <div
            style={{
               display: "flex",
               justifyContent: "space-between",
               alignItems: "center",
               marginBottom: 8,
            }}
         >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
               {onBack && (
                  <button
                     onClick={onBack}
                     style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        fontSize: 16,
                        color: "#888",
                        padding: 0,
                     }}
                  >
                     ←
                  </button>
               )}
               <div
                  style={{
                     borderRadius: 20,
                     padding: "3px 10px",
                     fontSize: 11,
                     fontWeight: 700,
                     background: cat.bg,
                     color: cat.color,
                     border: `1px solid ${cat.color}`,
                  }}
               >
                  {popup.MID_CAT_NM || cat.label || popup.CAT_NM}
               </div>
            </div>
            <button
               onClick={onClose}
               style={{
                  background: "transparent",
                  border: "none",
                  color: "#bbb",
                  cursor: "pointer",
                  fontSize: 16,
               }}
            >
               ✕
            </button>
         </div>

         <div
            style={{
               fontSize: 17,
               fontWeight: 700,
               color: "#111",
               marginBottom: 4,
            }}
         >
            {popup.STORE_NM}
         </div>
         {popup.SUB_CAT_NM && (
            <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>
               {popup.MID_CAT_NM} · {popup.SUB_CAT_NM}
            </div>
         )}
         <div style={{ height: 1, background: "#f0f0f0", margin: "10px 0" }} />

         <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {popup.ROAD_ADDR && (
               <div
                  style={{ display: "flex", alignItems: "flex-start", gap: 7 }}
               >
                  <span style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}>
                     📍
                  </span>
                  <span
                     style={{ fontSize: 13, color: "#444", lineHeight: 1.4 }}
                  >
                     {popup.ROAD_ADDR}
                     {popup.FLOOR_INFO && ` ${popup.FLOOR_INFO}층`}
                     {popup.UNIT_INFO && ` ${popup.UNIT_INFO}호`}
                  </span>
               </div>
            )}
            <div style={{ display: "flex", alignItems: "flex-start", gap: 7 }}>
               <span style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}>
                  🏙️
               </span>
               <span style={{ fontSize: 13, color: "#444", lineHeight: 1.4 }}>
                  {popup.SIDO_NM} {popup.SGG_NM} {popup.ADM_NM}
               </span>
            </div>
         </div>

         {loadingDetail && (
            <div
               style={{
                  marginTop: 10,
                  fontSize: 12,
                  color: "#999",
                  textAlign: "center",
                  padding: "8px 0",
               }}
            >
               📱 카카오맵 상세정보 조회 중...
            </div>
         )}
         {!loadingDetail && kakaoDetail && (
            <>
               <div
                  style={{
                     marginTop: 10,
                     padding: "10px 12px",
                     background: "#fffde7",
                     borderRadius: 10,
                     display: "flex",
                     flexDirection: "column",
                     gap: 6,
                  }}
               >
                  <div
                     style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#b8860b",
                        marginBottom: 2,
                     }}
                  >
                     📱 카카오맵 추가정보
                  </div>
                  {kakaoDetail.phone && (
                     <div
                        style={{
                           display: "flex",
                           alignItems: "flex-start",
                           gap: 7,
                        }}
                     >
                        <span
                           style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}
                        >
                           📞
                        </span>
                        <a
                           href={`tel:${kakaoDetail.phone}`}
                           style={{
                              fontSize: 13,
                              color: "#2563eb",
                              textDecoration: "none",
                           }}
                        >
                           {kakaoDetail.phone}
                        </a>
                     </div>
                  )}
                  {kakaoDetail.category_name && (
                     <div
                        style={{
                           display: "flex",
                           alignItems: "flex-start",
                           gap: 7,
                        }}
                     >
                        <span
                           style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}
                        >
                           🏷️
                        </span>
                        <span
                           style={{
                              fontSize: 13,
                              color: "#444",
                              lineHeight: 1.4,
                           }}
                        >
                           {kakaoDetail.category_name}
                        </span>
                     </div>
                  )}
               </div>
               <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <a
                     href={kakaoDetail.place_url}
                     target="_blank"
                     rel="noreferrer"
                     style={{
                        display: "inline-flex",
                        alignItems: "center",
                        background: "#fee500",
                        borderRadius: 10,
                        padding: "7px 14px",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#111",
                        textDecoration: "none",
                     }}
                  >
                     카카오맵 →
                  </a>
                  {onLandValue && (
                     <button
                        onClick={onLandValue}
                        style={{
                           display: "inline-flex",
                           alignItems: "center",
                           background: "#f0fdf4",
                           border: "1px solid #86efac",
                           borderRadius: 10,
                           padding: "7px 14px",
                           fontSize: 12,
                           fontWeight: 700,
                           color: "#166534",
                           cursor: "pointer",
                        }}
                     >
                        🏷️ 공시지가
                     </button>
                  )}
               </div>
            </>
         )}
         {!loadingDetail && !kakaoDetail && (
            <div
               style={{
                  marginTop: 10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
               }}
            >
               <span style={{ fontSize: 11, color: "#bbb" }}>
                  카카오맵 정보 없음
               </span>
               {onLandValue && (
                  <button
                     onClick={onLandValue}
                     style={{
                        background: "#f0fdf4",
                        border: "1px solid #86efac",
                        borderRadius: 10,
                        padding: "6px 12px",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#166534",
                        cursor: "pointer",
                     }}
                  >
                     🏷️ 공시지가
                  </button>
               )}
            </div>
         )}

         {nearbyStores.length > 0 && (
            <>
               <div
                  style={{
                     height: 1,
                     background: "#f0f0f0",
                     margin: "12px 0 8px",
                  }}
               />
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#aaa",
                     marginBottom: 6,
                  }}
               >
                  같은 건물 상가 ({nearbyStores.length}건)
               </div>
               <div style={{ maxHeight: 160, overflowY: "auto" }}>
                  {nearbyStores.slice(0, 20).map((s, i) => {
                     const c = getCatStyle(s.CAT_CD);
                     return (
                        <div
                           key={`${s.STORE_ID || "x"}-${i}`}
                           onClick={() => onStoreSelect?.(s)}
                           style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                              padding: "6px 4px",
                              cursor: "pointer",
                              borderRadius: 6,
                              borderBottom: "1px solid #f5f5f5",
                           }}
                        >
                           <div
                              style={{
                                 width: 8,
                                 height: 8,
                                 borderRadius: "50%",
                                 background: c.color,
                                 flexShrink: 0,
                              }}
                           />
                           <div style={{ flex: 1, minWidth: 0 }}>
                              <div
                                 style={{
                                    fontSize: 12,
                                    fontWeight: 600,
                                    color: "#222",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                 }}
                              >
                                 {s.STORE_NM}
                              </div>
                              <div style={{ fontSize: 10, color: "#aaa" }}>
                                 {c.label}
                              </div>
                           </div>
                        </div>
                     );
                  })}
               </div>
            </>
         )}
      </div>
   );
}

// ── 메인 컴포넌트 ───────────────────────────────────────────────
export default function StorePopup({
   popup,
   kakaoDetail,
   loadingDetail,
   onClose,
   nearbyStores = [],
   onStoreSelect,
   clusterStores = null,
   onClusterSelect,
   onLandValue,
   hasDongPanel = false,
}) {
   const [showList, setShowList] = useState(false);

   // 클러스터 목록 모드
   if (clusterStores && clusterStores.length > 0 && !popup) {
      return (
         <div
            style={{
               position: "absolute",
               bottom: 20,
               ...(hasDongPanel ? { left: 16 } : { right: 16 }),
               zIndex: 300,
               width: 300,
               background: "#fff",
               borderRadius: 16,
               boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
               overflow: "hidden",
            }}
         >
            <div style={{ height: 4, background: "#0891B2" }} />
            <ClusterListView
               stores={clusterStores}
               onSelect={onClusterSelect}
               onClose={onClose}
            />
         </div>
      );
   }

   if (!popup) return null;

   // 단일 상가 + 뒤로가기(클러스터에서 온 경우)
   if (showList && clusterStores?.length > 0) {
      return (
         <div
            style={{
               position: "absolute",
               bottom: 20,
               ...(hasDongPanel ? { left: 16 } : { right: 16 }),
               zIndex: 300,
               width: 300,
               background: "#fff",
               borderRadius: 16,
               boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
               overflow: "hidden",
            }}
         >
            <div style={{ height: 4, background: "#0891B2" }} />
            <ClusterListView
               stores={clusterStores}
               onSelect={(s) => {
                  setShowList(false);
                  onClusterSelect?.(s);
               }}
               onClose={onClose}
            />
         </div>
      );
   }

   const cat = getCatStyle(popup.CAT_CD);
   return (
      <div
         style={{
            position: "absolute",
            bottom: 20,
            ...(hasDongPanel ? { left: 16 } : { right: 16 }),
            zIndex: 300,
            width: 300,
            background: "#fff",
            borderRadius: 16,
            boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
            overflow: "hidden",
         }}
      >
         <div style={{ height: 4, background: cat.color }} />
         <StoreDetailView
            popup={popup}
            kakaoDetail={kakaoDetail}
            loadingDetail={loadingDetail}
            onClose={onClose}
            nearbyStores={nearbyStores}
            onStoreSelect={onStoreSelect}
            onBack={clusterStores?.length > 0 ? () => setShowList(true) : null}
            onLandValue={onLandValue}
         />
      </div>
   );
}
