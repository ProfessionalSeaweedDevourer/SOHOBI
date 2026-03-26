// 위치: src/components/panel/PopulationPanel.jsx

/**
 * PopulationPanel.jsx  –  서울 실시간 유동인구 패널
 *
 * 탭 1) 거리별  : 현재 지도 중심 기준 반경 내 장소 자동 조회
 * 탭 2) 구별    : 25개 구 드롭다운 선택 → 해당 구 전체 장소 조회
 *
 * API키 없을 때 → 장소 목록+위치는 표시, 혼잡도는 "(키 미설정)" 표시
 */

import { useState, useEffect, useCallback } from "react";

const REALESTATE_URL = "http://localhost:8682";

/* 혼잡도 → 색상/이모지 */
const CONGEST_STYLE = {
   붐빔: { color: "#E03131", bg: "#FFF0F0", emoji: "🔴" },
   약간붐빔: { color: "#FF9800", bg: "#FFF8F0", emoji: "🟠" },
   보통: { color: "#2196F3", bg: "#F0F4FF", emoji: "🔵" },
   여유: { color: "#2F9E44", bg: "#F0FFF4", emoji: "🟢" },
};

function CongestBadge({ level }) {
   if (!level) return <span style={S.naTag}>(키 미설정)</span>;
   const s = CONGEST_STYLE[level] || {
      color: "#888",
      bg: "#f5f5f5",
      emoji: "⚪",
   };
   return (
      <span style={{ ...S.congestBadge, background: s.bg, color: s.color }}>
         {s.emoji} {level}
      </span>
   );
}

function PlaceRow({ item }) {
   return (
      <div style={S.placeRow}>
         <div style={S.placeLeft}>
            <div style={S.placeName}>{item.name}</div>
            {item.distance_m != null && (
               <div style={S.placeDist}>{item.distance_m}m</div>
            )}
         </div>
         <div style={S.placeRight}>
            <CongestBadge level={item.혼잡도} />
            {item.인구_최소 && item.인구_최대 && (
               <div style={S.popRange}>
                  {Number(item.인구_최소).toLocaleString()}~
                  {Number(item.인구_최대).toLocaleString()}명
               </div>
            )}
         </div>
      </div>
   );
}

export default function PopulationPanel({ centerLat, centerLng, onClose }) {
   const [tab, setTab] = useState("nearby"); // "nearby" | "gu"
   const [guList, setGuList] = useState([]); // 25개 구 목록
   const [selectedGu, setSelectedGu] = useState("");
   const [radius, setRadius] = useState(3); // km
   const [data, setData] = useState([]);
   const [loading, setLoading] = useState(false);
   const [error, setError] = useState(null);
   const [updatedAt, setUpdatedAt] = useState(null);

   /* 구 목록 초기 로드 */
   useEffect(() => {
      fetch(`${REALESTATE_URL}/realestate/places-list`)
         .then((r) => r.json())
         .then((d) => {
            setGuList(d.gu_list || []);
            if (d.gu_list?.length) setSelectedGu(d.gu_list[0]);
         })
         .catch(() => {});
   }, []);

   /* 거리별 조회 */
   const fetchNearby = useCallback(async () => {
      if (!centerLat || !centerLng) return;
      setLoading(true);
      setError(null);
      try {
         const res = await fetch(
            `${REALESTATE_URL}/realestate/nearby-population` +
               `?lat=${centerLat}&lng=${centerLng}&radius_km=${radius}`,
         );
         const d = await res.json();
         setData(d.data || []);
         setUpdatedAt(new Date().toLocaleTimeString());
      } catch (e) {
         setError("조회 실패: " + e.message);
      } finally {
         setLoading(false);
      }
   }, [centerLat, centerLng, radius]);

   /* 구별 조회 */
   const fetchByGu = useCallback(async () => {
      if (!selectedGu) return;
      setLoading(true);
      setError(null);
      try {
         const res = await fetch(
            `${REALESTATE_URL}/realestate/population-by-gu?gu=${encodeURIComponent(selectedGu)}`,
         );
         const d = await res.json();
         setData(d.data || []);
         setUpdatedAt(new Date().toLocaleTimeString());
      } catch (e) {
         setError("조회 실패: " + e.message);
      } finally {
         setLoading(false);
      }
   }, [selectedGu]);

   /* 탭 전환 시 자동 조회 */
   useEffect(() => {
      setData([]);
      if (tab === "nearby") fetchNearby();
      else fetchByGu();
   }, [tab]); // eslint-disable-line

   return (
      <div style={S.panel}>
         {/* 헤더 */}
         <div style={S.header}>
            <span style={S.headerTitle}>👥 서울 실시간 유동인구</span>
            <button style={S.closeBtn} onClick={onClose}>
               ✕
            </button>
         </div>

         {/* 탭 */}
         <div style={S.tabs}>
            <button
               style={{ ...S.tab, ...(tab === "nearby" ? S.tabActive : {}) }}
               onClick={() => setTab("nearby")}
            >
               📍 거리별
            </button>
            <button
               style={{ ...S.tab, ...(tab === "gu" ? S.tabActive : {}) }}
               onClick={() => setTab("gu")}
            >
               🏙️ 구별
            </button>
         </div>

         {/* 컨트롤 영역 */}
         <div style={S.controls}>
            {tab === "nearby" ? (
               <>
                  <label style={S.label}>반경</label>
                  {[1, 2, 3, 5].map((km) => (
                     <button
                        key={km}
                        style={{
                           ...S.radiusBtn,
                           ...(radius === km ? S.radiusBtnActive : {}),
                        }}
                        onClick={() => setRadius(km)}
                     >
                        {km}km
                     </button>
                  ))}
                  <button
                     style={S.searchBtn}
                     onClick={fetchNearby}
                     disabled={loading}
                  >
                     {loading ? "..." : "조회"}
                  </button>
               </>
            ) : (
               <>
                  <select
                     style={S.select}
                     value={selectedGu}
                     onChange={(e) => setSelectedGu(e.target.value)}
                  >
                     {guList.map((g) => (
                        <option key={g} value={g}>
                           {g}
                        </option>
                     ))}
                  </select>
                  <button
                     style={S.searchBtn}
                     onClick={fetchByGu}
                     disabled={loading}
                  >
                     {loading ? "..." : "조회"}
                  </button>
               </>
            )}
         </div>

         {/* 결과 */}
         <div style={S.resultArea}>
            {loading && <div style={S.loadingMsg}>🔄 조회 중...</div>}
            {error && <div style={S.errorMsg}>{error}</div>}
            {!loading && !error && data.length === 0 && (
               <div style={S.emptyMsg}>
                  {tab === "nearby"
                     ? `반경 ${radius}km 내 주요 장소가 없습니다`
                     : "조회 버튼을 눌러주세요"}
               </div>
            )}
            {!loading &&
               data.map((item, i) => (
                  <PlaceRow key={item.code || i} item={item} />
               ))}
         </div>

         {/* 업데이트 시각 + 안내 */}
         <div style={S.footer}>
            {updatedAt && <span>🕐 {updatedAt} 기준</span>}
            <span style={{ color: "#bbb", fontSize: 10 }}>
               {" "}
               · API키 발급 후 혼잡도 실시간 표시
            </span>
         </div>
      </div>
   );
}

const S = {
   panel: {
      position: "absolute",
      bottom: 50,
      right: 14,
      zIndex: 300,
      width: 300,
      background: "#fff",
      borderRadius: 16,
      boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      maxHeight: "70vh",
   },
   header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "12px 16px 8px",
      borderBottom: "1px solid #f0f0f0",
   },
   headerTitle: { fontSize: 14, fontWeight: 700, color: "#111" },
   closeBtn: {
      background: "transparent",
      border: "none",
      color: "#bbb",
      cursor: "pointer",
      fontSize: 16,
   },
   tabs: {
      display: "flex",
      borderBottom: "1px solid #f0f0f0",
   },
   tab: {
      flex: 1,
      padding: "8px 0",
      background: "transparent",
      border: "none",
      fontSize: 12,
      fontWeight: 600,
      color: "#888",
      cursor: "pointer",
      borderBottom: "2px solid transparent",
      transition: "all 0.15s",
   },
   tabActive: {
      color: "#2563EB",
      borderBottom: "2px solid #2563EB",
   },
   controls: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "10px 12px",
      background: "#f9fafb",
      flexWrap: "wrap",
   },
   label: { fontSize: 11, color: "#888", fontWeight: 600 },
   radiusBtn: {
      padding: "4px 8px",
      borderRadius: 6,
      border: "1px solid #e0e0e0",
      background: "#fff",
      fontSize: 11,
      cursor: "pointer",
      color: "#555",
   },
   radiusBtnActive: {
      background: "#2563EB",
      color: "#fff",
      border: "1px solid #2563EB",
   },
   select: {
      flex: 1,
      padding: "5px 8px",
      borderRadius: 6,
      border: "1px solid #e0e0e0",
      fontSize: 12,
      color: "#333",
      background: "#fff",
   },
   searchBtn: {
      padding: "5px 12px",
      background: "#2563EB",
      color: "#fff",
      border: "none",
      borderRadius: 6,
      fontSize: 12,
      fontWeight: 700,
      cursor: "pointer",
   },
   resultArea: {
      overflowY: "auto",
      flex: 1,
      padding: "4px 0",
   },
   loadingMsg: {
      padding: "20px",
      textAlign: "center",
      color: "#888",
      fontSize: 12,
   },
   errorMsg: { padding: "12px 16px", color: "#E03131", fontSize: 12 },
   emptyMsg: {
      padding: "20px",
      textAlign: "center",
      color: "#bbb",
      fontSize: 12,
   },
   placeRow: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "9px 16px",
      borderBottom: "1px solid #f5f5f5",
   },
   placeLeft: { display: "flex", flexDirection: "column", gap: 2 },
   placeName: { fontSize: 13, fontWeight: 600, color: "#222" },
   placeDist: { fontSize: 10, color: "#aaa" },
   placeRight: {
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-end",
      gap: 3,
   },
   congestBadge: {
      fontSize: 11,
      fontWeight: 700,
      padding: "2px 8px",
      borderRadius: 20,
   },
   popRange: { fontSize: 10, color: "#aaa" },
   naTag: { fontSize: 10, color: "#bbb" },
   footer: {
      padding: "6px 12px",
      fontSize: 10,
      color: "#aaa",
      borderTop: "1px solid #f0f0f0",
   },
};
