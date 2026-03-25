// components/StorePopup.jsx

// ── 업종 색상 헬퍼 ─────────────────────────────────────────────
// CAT_CD(I2,G2...) 기반 색상
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

// ── 메인 컴포넌트: 소상공인 마커 클릭 팝업 (카카오 연동) ───────
export default function StorePopup({
   popup,
   kakaoDetail,
   loadingDetail,
   onClose,
}) {
   if (!popup) return null;
   const cat = getCatStyle(popup.CAT_CD);

   return (
      <div
         style={{
            position: "absolute",
            bottom: 50,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 300,
            width: 320,
            background: "#fff",
            borderRadius: 16,
            boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
            overflow: "hidden",
         }}
      >
         <div style={{ height: 4, background: cat.color }} />
         <div style={{ padding: "12px 16px 16px" }}>
            {/* 헤더 */}
            <div
               style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
               }}
            >
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
                  {cat.label || popup.CAT_NM}
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
            <div
               style={{ height: 1, background: "#f0f0f0", margin: "10px 0" }}
            />

            {/* DB 데이터 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
               {popup.ROAD_ADDR && (
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
               <div
                  style={{ display: "flex", alignItems: "flex-start", gap: 7 }}
               >
                  <span style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}>
                     🏙️
                  </span>
                  <span
                     style={{ fontSize: 13, color: "#444", lineHeight: 1.4 }}
                  >
                     {popup.SIDO_NM} {popup.SGG_NM} {popup.ADM_NM}
                  </span>
               </div>
            </div>

            {/* 카카오 상세 */}
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
                              style={{
                                 fontSize: 13,
                                 flexShrink: 0,
                                 marginTop: 1,
                              }}
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
                              style={{
                                 fontSize: 13,
                                 flexShrink: 0,
                                 marginTop: 1,
                              }}
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
                  <a
                     href={kakaoDetail.place_url}
                     target="_blank"
                     rel="noreferrer"
                     style={{
                        marginTop: 12,
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        background: "#fee500",
                        borderRadius: 10,
                        padding: "9px",
                        fontSize: 13,
                        fontWeight: 700,
                        color: "#111",
                        textDecoration: "none",
                     }}
                  >
                     카카오맵에서 보기 →
                  </a>
               </>
            )}
            {!loadingDetail && !kakaoDetail && (
               <div
                  style={{
                     marginTop: 10,
                     fontSize: 11,
                     color: "#bbb",
                     textAlign: "center",
                  }}
               >
                  카카오맵 정보를 찾을 수 없습니다
               </div>
            )}
         </div>
      </div>
   );
}
