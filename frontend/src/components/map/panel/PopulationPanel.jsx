// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\panel\PopulationPanel.jsx
// 공식 프론트 위치: frontend\src\components\map\panel\PopulationPanel.jsx
// 유동인구 마커 범례 패널 (실제 마커는 usePopulationLayer에서 지도에 표시)

import { CONGEST_STYLE } from "../../../hooks/map/usePopulationLayer";

export default function PopulationPanel({ onClose, visible, onToggle, count }) {
   return (
      <div style={S.panel}>
         <div style={S.header}>
            <span style={S.title}>👥 실시간 유동인구</span>
            <button style={S.closeBtn} onClick={onClose}>
               ✕
            </button>
         </div>

         {/* ON/OFF 토글 */}
         <div style={S.toggleRow}>
            <span style={{ fontSize: 12, color: "#555" }}>마커 표시</span>
            <button
               onClick={onToggle}
               style={{
                  ...S.toggleBtn,
                  background: visible ? "#2563EB" : "#e0e0e0",
                  color: visible ? "#fff" : "#555",
               }}
            >
               {visible ? "ON" : "OFF"}
            </button>
            {count > 0 && <span style={S.count}>{count}개 스팟</span>}
         </div>

         <div style={S.divider} />

         {/* 범례 */}
         <div style={S.legendTitle}>혼잡도 기준</div>
         {Object.entries(CONGEST_STYLE).map(([key, val]) => (
            <div key={key} style={S.legendRow}>
               <div style={{ ...S.dot, background: val.color }} />
               <span style={S.emoji}>{val.emoji}</span>
               <span style={S.levelLabel}>{key}</span>
               <span style={S.levelDesc}>
                  {key === "붐빔" && "매우 혼잡"}
                  {key === "약간붐빔" && "다소 혼잡"}
                  {key === "보통" && "적정 수준"}
                  {key === "여유" && "한산함"}
               </span>
            </div>
         ))}

         <div style={S.footer}>💡 서울 주요 장소 기준 · 실시간 갱신</div>
      </div>
   );
}

const S = {
   panel: {
      position: "absolute",
      bottom: 50,
      right: 14,
      zIndex: 300,
      width: 220,
      background: "#fff",
      borderRadius: 16,
      boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
      overflow: "hidden",
   },
   header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "12px 14px 8px",
      borderBottom: "1px solid #f0f0f0",
   },
   title: { fontSize: 13, fontWeight: 700, color: "#111" },
   closeBtn: {
      background: "transparent",
      border: "none",
      color: "#bbb",
      cursor: "pointer",
      fontSize: 15,
   },
   toggleRow: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "10px 14px",
   },
   toggleBtn: {
      border: "none",
      borderRadius: 6,
      padding: "4px 12px",
      fontSize: 12,
      fontWeight: 700,
      cursor: "pointer",
      transition: "all 0.2s",
   },
   count: { fontSize: 11, color: "#888" },
   divider: { height: 1, background: "#f0f0f0", margin: "0 14px" },
   legendTitle: {
      fontSize: 11,
      fontWeight: 700,
      color: "#aaa",
      padding: "10px 14px 4px",
      textTransform: "uppercase",
      letterSpacing: 1,
   },
   legendRow: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "7px 14px",
   },
   dot: { width: 10, height: 10, borderRadius: "50%", flexShrink: 0 },
   emoji: { fontSize: 13 },
   levelLabel: { fontSize: 12, fontWeight: 700, color: "#333", width: 55 },
   levelDesc: { fontSize: 11, color: "#888" },
   footer: {
      fontSize: 10,
      color: "#bbb",
      padding: "8px 14px",
      borderTop: "1px solid #f0f0f0",
      textAlign: "center",
   },
};
