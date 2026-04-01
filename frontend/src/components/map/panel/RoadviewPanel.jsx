// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\panel\RoadviewPanel.jsx
// 공식 프론트 위치: frontend\src\components\map\panel\RoadviewPanel.jsx

// 로드뷰 - 버튼 ON 후 지도 클릭 시 해당 좌표로 열림

import { useEffect, useRef, useState } from "react";

export default function RoadviewPanel({ lat, lng, label, onClose }) {
   const containerRef = useRef(null);
   const initStatus = !lat || !lng || !window.kakao?.maps ? "error" : "loading";
   const [status, setStatus] = useState(initStatus);

   useEffect(() => {
      if (!lat || !lng || !window.kakao?.maps) return;

      const kakao = window.kakao.maps;
      const container = containerRef.current;
      const rv = new kakao.Roadview(container);
      const client = new kakao.RoadviewClient();

      client.getNearestPanoId(new kakao.LatLng(lat, lng), 50, (panoId) => {
         if (panoId === null) {
            setStatus("notfound");
            return;
         }
         rv.setPanoId(panoId, new kakao.LatLng(lat, lng));
         setStatus("ok");
      });

      return () => {
         if (container) container.innerHTML = "";
      };
   }, [lat, lng]);

   return (
      <div style={S.panel}>
         {/* 헤더 */}
         <div style={S.header}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
               <span style={{ fontSize: 18 }}>🚶</span>
               <span style={S.title}>로드뷰</span>
               {label && <span style={S.label}>{label}</span>}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
               <a
                  href={`https://map.kakao.com/link/roadview/${lat},${lng}`}
                  target="_blank"
                  rel="noreferrer"
                  style={S.externalBtn}
               >
                  ↗
               </a>
               <button style={S.closeBtn} onClick={onClose}>
                  ✕
               </button>
            </div>
         </div>

         {/* 안내 배너 */}
         <div style={S.guideBanner}>
            🖱️ 지도에서 <strong>도로를 클릭</strong>하면 해당 위치 로드뷰로 이동
         </div>

         {/* 뷰어 */}
         <div
            style={{
               position: "relative",
               width: "100%",
               flex: 1,
               background: "#111",
               minHeight: 0,
            }}
         >
            <div
               ref={containerRef}
               style={{
                  width: "100%",
                  height: "100%",
                  position: "absolute",
                  inset: 0,
               }}
            />
            {status === "loading" && (
               <div style={S.overlay}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>⟳</div>
                  <div style={S.overlayText}>로드뷰 불러오는 중...</div>
               </div>
            )}
            {status === "notfound" && (
               <div style={S.overlay}>
                  <div style={{ fontSize: 36, marginBottom: 8 }}>🚫</div>
                  <div style={S.overlayText}>로드뷰를 찾을 수 없어요</div>
                  <div style={{ fontSize: 11, color: "#aaa", marginTop: 4 }}>
                     도로를 직접 클릭해주세요
                  </div>
               </div>
            )}
            {status === "error" && (
               <div style={S.overlay}>
                  <div style={{ fontSize: 36, marginBottom: 8 }}>⚠️</div>
                  <div style={S.overlayText}>카카오 SDK 오류</div>
                  <div style={{ fontSize: 11, color: "#aaa", marginTop: 4 }}>
                     index.html에 roadview 라이브러리 추가 필요
                  </div>
               </div>
            )}
         </div>

         {/* 좌표 */}
         <div style={S.footer}>
            📍 {lat?.toFixed(5)}, {lng?.toFixed(5)}
         </div>
      </div>
   );
}

const S = {
   panel: {
      position: "absolute",
      top: 0,
      right: 0,
      width: "50%",
      height: "100%",
      zIndex: 400,
      background: "#111",
      boxShadow: "-6px 0 32px rgba(0,0,0,0.35)",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
   },
   header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "10px 14px",
      background: "#1a1a2e",
      color: "#fff",
   },
   title: { fontSize: 14, fontWeight: 700, color: "#fff" },
   label: {
      fontSize: 11,
      color: "#aaa",
      background: "rgba(255,255,255,0.1)",
      padding: "2px 8px",
      borderRadius: 20,
   },
   externalBtn: {
      color: "#aaa",
      fontSize: 16,
      textDecoration: "none",
      padding: "2px 6px",
      borderRadius: 4,
      background: "rgba(255,255,255,0.08)",
   },
   closeBtn: {
      background: "rgba(255,255,255,0.1)",
      border: "none",
      color: "#fff",
      borderRadius: 6,
      padding: "3px 8px",
      cursor: "pointer",
      fontSize: 14,
   },
   guideBanner: {
      padding: "8px 14px",
      background: "#1e293b",
      color: "#94a3b8",
      fontSize: 11,
      borderBottom: "1px solid #334155",
   },
   overlay: {
      position: "absolute",
      inset: 0,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "rgba(17,17,17,0.85)",
      color: "#fff",
   },
   overlayText: { fontSize: 13, fontWeight: 600 },
   footer: {
      padding: "6px 14px",
      fontSize: 11,
      color: "#aaa",
      background: "#f9f9f9",
      borderTop: "1px solid #eee",
   },
};
