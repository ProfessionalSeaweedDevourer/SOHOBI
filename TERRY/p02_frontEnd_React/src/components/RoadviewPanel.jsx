/**
 * RoadviewPanel.jsx  –  카카오 로드뷰 플로팅 오버레이
 *
 * 사용법:
 *   <RoadviewPanel lat={37.5665} lng={126.9780} onClose={() => setRoadview(null)} />
 *
 * 카카오 JS SDK는 index.html에서 이미 로드되어 있어야 함:
 *   <script src="//dapi.kakao.com/v2/maps/sdk.js?appkey=YOUR_KEY&libraries=services,clusterer"></script>
 *   → libraries에 'roadview' 추가 필요: &libraries=services,clusterer,roadview
 */

import { useEffect, useRef, useState } from "react";

export default function RoadviewPanel({ lat, lng, label, onClose }) {
   const containerRef = useRef(null);
   const roadviewRef = useRef(null);
   // lat/lng 바뀔 때마다 loading으로 초기화 → useState 초기값 + key prop 활용
   const [status, setStatus] = useState(() =>
      window.kakao?.maps ? "loading" : "error",
   );

   useEffect(() => {
      if (!lat || !lng) return;
      if (!window.kakao?.maps) return; // 이미 "error" 상태

      const kakao = window.kakao.maps;

      // Roadview 인스턴스는 비동기 콜백 안에서만 setState 호출
      const container = containerRef.current;
      const rv = new kakao.Roadview(container);
      roadviewRef.current = rv;

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
            <div style={S.headerLeft}>
               <span style={S.icon}>🚶</span>
               <span style={S.title}>로드뷰</span>
               {label && <span style={S.label}>{label}</span>}
            </div>
            <div style={S.headerRight}>
               <a
                  href={`https://map.kakao.com/link/roadview/${lat},${lng}`}
                  target="_blank"
                  rel="noreferrer"
                  style={S.externalBtn}
                  title="카카오맵에서 열기"
               >
                  ↗
               </a>
               <button style={S.closeBtn} onClick={onClose}>
                  ✕
               </button>
            </div>
         </div>

         {/* 뷰어 영역 */}
         <div style={S.viewerWrap}>
            {/* 로드뷰 DOM 컨테이너 */}
            <div ref={containerRef} style={S.viewer} />

            {/* 상태 오버레이 */}
            {status === "loading" && (
               <div style={S.overlay}>
                  <div style={S.spinner}>⟳</div>
                  <div style={S.overlayText}>로드뷰 불러오는 중...</div>
               </div>
            )}
            {status === "notfound" && (
               <div style={S.overlay}>
                  <div style={{ fontSize: 36, marginBottom: 8 }}>🚫</div>
                  <div style={S.overlayText}>
                     이 위치에서 로드뷰를 찾을 수 없어요
                  </div>
                  <div style={{ fontSize: 11, color: "#aaa", marginTop: 4 }}>
                     반경 50m 이내 로드뷰 데이터 없음
                  </div>
               </div>
            )}
            {status === "error" && (
               <div style={S.overlay}>
                  <div style={{ fontSize: 36, marginBottom: 8 }}>⚠️</div>
                  <div style={S.overlayText}>카카오 SDK 로드 오류</div>
                  <div style={{ fontSize: 11, color: "#aaa", marginTop: 4 }}>
                     index.html script에 roadview 라이브러리 추가 필요
                  </div>
               </div>
            )}
         </div>

         {/* 좌표 표시 */}
         <div style={S.footer}>
            📍 {lat.toFixed(6)}, {lng.toFixed(6)}
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
      borderRadius: 0,
   },
   header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "10px 14px",
      background: "#1a1a2e",
      color: "#fff",
   },
   headerLeft: { display: "flex", alignItems: "center", gap: 8 },
   icon: { fontSize: 18 },
   title: { fontSize: 14, fontWeight: 700, color: "#fff" },
   label: {
      fontSize: 11,
      color: "#aaa",
      background: "rgba(255,255,255,0.1)",
      padding: "2px 8px",
      borderRadius: 20,
   },
   headerRight: { display: "flex", alignItems: "center", gap: 6 },
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
   viewerWrap: {
      position: "relative",
      width: "100%",
      flex: 1,
      background: "#111",
      minHeight: 0,
   },
   viewer: {
      width: "100%",
      height: "100%",
      position: "absolute",
      inset: 0,
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
   spinner: {
      fontSize: 36,
      marginBottom: 8,
      animation: "spin 1s linear infinite",
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
