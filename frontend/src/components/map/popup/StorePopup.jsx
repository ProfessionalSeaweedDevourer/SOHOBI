// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\popup\StorePopup.jsx
// 공식 프론트 위치: frontend\src\components\map\popup\StorePopup.jsx
import { useState } from "react";
import "./StorePopup.css";

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

// ── 상가 리스트 아이템 ──────────────────────────────────────────
function StoreItem({ store, onClick, variant = "nearby" }) {
   const c = getCatStyle(store.CAT_CD);
   return (
      <div
         onClick={() => onClick?.(store)}
         className={`sp-store-item${variant === "list" ? " sp-store-item--list" : ""}`}
      >
         <div className="sp-store-dot" style={{ background: c.color }} />
         <div className="sp-store-info">
            <div className="sp-store-name">{store.STORE_NM}</div>
            <div className="sp-store-meta">
               {c.label}{variant === "list" && store.ADM_NM ? ` · ${store.ADM_NM}` : ""}
            </div>
         </div>
      </div>
   );
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
      <div className="sp-body">
         <div className="sp-top">
            <span className="sp-header-title">🏪 상가 {stores.length}개</span>
            <button onClick={onClose} className="sp-close-btn">✕</button>
         </div>
         <input
            type="text"
            placeholder="상호명·업종 검색..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="sp-search"
         />
         <div className="sp-scroll">
            {filtered.map((s, i) => (
               <StoreItem
                  key={`${s.STORE_ID || "x"}-${i}`}
                  store={s}
                  onClick={onSelect}
                  variant="list"
               />
            ))}
            {filtered.length === 0 && (
               <div className="sp-empty">검색 결과 없음</div>
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
      <div className="sp-body">
         <div className="sp-top">
            <div className="sp-top-left">
               {onBack && (
                  <button onClick={onBack} className="sp-back-btn">←</button>
               )}
               <div
                  className="sp-tag"
                  style={{
                     background: cat.bg,
                     color: cat.color,
                     border: `1px solid ${cat.color}`,
                  }}
               >
                  {popup.MID_CAT_NM || cat.label || popup.CAT_NM}
               </div>
            </div>
            <button onClick={onClose} className="sp-close-btn">✕</button>
         </div>

         <div className="sp-title">{popup.STORE_NM}</div>
         {popup.SUB_CAT_NM && (
            <div className="sp-subtitle">
               {popup.MID_CAT_NM} · {popup.SUB_CAT_NM}
            </div>
         )}
         <div className="sp-divider" />

         <div className="sp-rows">
            {popup.ROAD_ADDR && (
               <div className="sp-row">
                  <span className="sp-row-icon">📍</span>
                  <span className="sp-row-text">
                     {popup.ROAD_ADDR}
                     {popup.FLOOR_INFO && ` ${popup.FLOOR_INFO}층`}
                     {popup.UNIT_INFO && ` ${popup.UNIT_INFO}호`}
                  </span>
               </div>
            )}
            <div className="sp-row">
               <span className="sp-row-icon">🏙️</span>
               <span className="sp-row-text">
                  {popup.SIDO_NM} {popup.SGG_NM} {popup.ADM_NM}
               </span>
            </div>
         </div>

         {loadingDetail && (
            <div className="sp-loading">📱 카카오맵 상세정보 조회 중...</div>
         )}
         {!loadingDetail && kakaoDetail && (
            <>
               <div className="sp-kakao-box">
                  <div className="sp-kakao-box-title">📱 카카오맵 추가정보</div>
                  {kakaoDetail.phone && (
                     <div className="sp-row">
                        <span className="sp-row-icon">📞</span>
                        <a href={`tel:${kakaoDetail.phone}`} className="sp-link">
                           {kakaoDetail.phone}
                        </a>
                     </div>
                  )}
                  {kakaoDetail.category_name && (
                     <div className="sp-row">
                        <span className="sp-row-icon">🏷️</span>
                        <span className="sp-row-text">
                           {kakaoDetail.category_name}
                        </span>
                     </div>
                  )}
               </div>
               <div className="sp-actions">
                  <a
                     href={kakaoDetail.place_url}
                     target="_blank"
                     rel="noreferrer"
                     className="sp-kakao-btn"
                  >
                     카카오맵 →
                  </a>
                  {onLandValue && (
                     <button onClick={onLandValue} className="sp-landval-btn">
                        🏷️ 공시지가
                     </button>
                  )}
               </div>
            </>
         )}
         {!loadingDetail && !kakaoDetail && (
            <div className="sp-no-kakao">
               <span className="sp-no-kakao-text">카카오맵 정보 없음</span>
               {onLandValue && (
                  <button onClick={onLandValue} className="sp-landval-btn">
                     🏷️ 공시지가
                  </button>
               )}
            </div>
         )}

         {nearbyStores.length > 0 && (
            <>
               <div className="sp-divider sp-divider--top" />
               <div className="sp-nearby-title">
                  같은 건물 상가 ({nearbyStores.length}건)
               </div>
               <div className="sp-nearby-list">
                  {nearbyStores.slice(0, 20).map((s, i) => (
                     <StoreItem
                        key={`${s.STORE_ID || "x"}-${i}`}
                        store={s}
                        onClick={onStoreSelect}
                     />
                  ))}
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
   chatOpen = false,
}) {
   const [showList, setShowList] = useState(false);
   const popupClass = `sp-popup${hasDongPanel ? " sp-popup--dong-open" : ""}${chatOpen ? " sp-popup--chat-open" : ""}`;

   // 클러스터 목록 모드
   if (clusterStores && clusterStores.length > 0 && !popup) {
      return (
         <div className={popupClass}>
            <div style={{ height: 4, background: "var(--brand-blue)" }} />
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
         <div className={popupClass}>
            <div style={{ height: 4, background: "var(--brand-blue)" }} />
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
      <div className={popupClass}>
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
