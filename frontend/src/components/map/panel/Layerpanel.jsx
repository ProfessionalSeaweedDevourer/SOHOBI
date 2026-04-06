// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\panel\Layerpanel.jsx
// 공식 프론트 위치: frontend\src\components\map\panel\Layerpanel.jsx

import React, { useState } from "react";
import TileLayer from "ol/layer/Tile";
import TileWMS from "ol/source/TileWMS";

export default function LayerPanel({
   map,
   mapReady,
   vworldKey,
   wmsLayerRef,
   landmarkLayerRef,
   festivalLayerRef,
   schoolLayerRef,
   landmarkLoaded,
   festivalLoaded,
   schoolLoaded,
}) {
   const [cadastralOn, setCadastralOn] = useState(true);
   const [landmarkOn, setLandmarkOn] = useState(true);
   const [festivalOn, setFestivalOn] = useState(true);
   const [schoolOn, setSchoolOn] = useState(true);

   // 초기 레이어 자동 추가
   const initDoneRef = React.useRef(false);
   React.useEffect(() => {
      if (!map || !mapReady || initDoneRef.current) return;
      initDoneRef.current = true;
      // MapView에서 이미 추가했으면 ref만 연결하고 중복 추가 방지
      const existing = map
         .getLayers()
         .getArray()
         .find((l) => l.get("name") === "cadastral");
      if (existing) {
         wmsLayerRef.current = existing;
         return;
      }
      // 없으면 새로 추가
      const layer = new TileLayer({
         source: new TileWMS({
            url: `/wms/req/wms?KEY=${vworldKey}&DOMAIN=localhost`,
            params: {
               SERVICE: "WMS",
               VERSION: "1.3.0",
               REQUEST: "GetMap",
               LAYERS: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
               STYLES: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
               FORMAT: "image/png",
               TRANSPARENT: "TRUE",
               CRS: "EPSG:3857",
            },
            crossOrigin: "anonymous",
            transition: 0,
         }),
         opacity: 0.7,
         zIndex: 50,
         minZoom: 19,
      });
      layer.set("name", "cadastral");
      map.addLayer(layer);
      wmsLayerRef.current = layer;
   }, [map, mapReady]); // eslint-disable-line

   // ── 지적도 ──────────────────────────────────────────────────
   const toggleCadastral = () => {
      if (cadastralOn) {
         // name 기준으로 모든 지적도 레이어 제거 (중복 방지)
         map.getLayers()
            .getArray()
            .filter((l) => l.get("name") === "cadastral")
            .forEach((l) => map.removeLayer(l));
         wmsLayerRef.current = null;
         setCadastralOn(false);
      } else {
         const layer = new TileLayer({
            source: new TileWMS({
               url: `/wms/req/wms?KEY=${vworldKey}&DOMAIN=localhost`,
               params: {
                  SERVICE: "WMS",
                  VERSION: "1.3.0",
                  REQUEST: "GetMap",
                  LAYERS: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
                  STYLES: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
                  FORMAT: "image/png",
                  TRANSPARENT: "TRUE",
                  CRS: "EPSG:3857",
               },
               crossOrigin: "anonymous",
               transition: 0,
            }),
            opacity: 0.7,
            zIndex: 50,
            minZoom: 19,
         });
         layer.set("name", "cadastral");
         map.addLayer(layer);
         wmsLayerRef.current = layer;
         setCadastralOn(true);
      }
   };

   // ── 관광지·문화시설 (KTO DB 마커) ───────────────────────────
   const toggleLandmark = () => {
      if (!landmarkLoaded || !landmarkLayerRef?.current) return;
      const next = !landmarkOn;
      landmarkLayerRef.current.setVisible(next);
      setLandmarkOn(next);
   };

   const toggleFestival = () => {
      if (!festivalLoaded || !festivalLayerRef?.current) return;
      const next = !festivalOn;
      festivalLayerRef.current.setVisible(next);
      setFestivalOn(next);
   };

   const toggleSchool = () => {
      if (!schoolLoaded || !schoolLayerRef?.current) return;
      const next = !schoolOn;
      schoolLayerRef.current.setVisible(next);
      setSchoolOn(next);
   };

   return (
      <div style={S.panel}>
         <div style={S.title}>🗂️ 레이어 관리</div>

         <div style={S.sectionLabel}>VWorld</div>
         <LayerRow
            label="📋 지적도"
            desc="토지 경계 · 공시지가"
            on={cadastralOn}
            color="#2196F3"
            onClick={toggleCadastral}
         />

         <div style={S.sectionLabel}>한국관광공사</div>
         <LayerRow
            label="🏛️ 관광지·문화"
            desc="DB 마커 (관광지+문화시설)"
            on={landmarkOn}
            color="#7B1FA2"
            onClick={toggleLandmark}
            disabled={!landmarkLoaded}
         />
         <LayerRow
            label="🎉 축제"
            desc="실시간 API 마커"
            on={festivalOn}
            color="#ef4444"
            onClick={toggleFestival}
            disabled={!festivalLoaded}
         />

         <div style={S.sectionLabel}>교육</div>
         <LayerRow
            label="🏫 학교"
            desc="DB 마커"
            on={schoolOn}
            color="#10b981"
            onClick={toggleSchool}
            disabled={!schoolLoaded}
         />

         <div style={S.notice}>💡 동 클릭 시 해당 구역 마커 자동 로드</div>
      </div>
   );
}

function LayerRow({ label, desc, on, color, onClick, disabled }) {
   return (
      <div style={{ ...S.row, opacity: disabled ? 0.4 : 1 }}>
         <div style={{ flex: 1 }}>
            <div style={S.layerName}>{label}</div>
            <div style={S.layerDesc}>{desc}</div>
         </div>
         <button
            onClick={disabled ? undefined : onClick}
            style={{
               ...S.toggle,
               background: on ? color : "#e0e0e0",
               color: on ? "#fff" : "#555",
               cursor: disabled ? "default" : "pointer",
            }}
         >
            {on ? "ON" : "OFF"}
         </button>
      </div>
   );
}

const S = {
   panel: {
      background: "#fff",
      border: "1px solid #ddd",
      borderRadius: 10,
      padding: 16,
      minWidth: 230,
      boxShadow: "0 4px 16px rgba(0,0,0,0.1)",
   },
   title: {
      fontSize: 13,
      fontWeight: 700,
      color: "#111",
      marginBottom: 12,
      paddingBottom: 8,
      borderBottom: "1px solid #f0f0f0",
   },
   sectionLabel: {
      fontSize: 10,
      fontWeight: 700,
      color: "#aaa",
      textTransform: "uppercase",
      letterSpacing: 1,
      margin: "10px 0 4px 2px",
   },
   row: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: 10,
      background: "#f9f9f9",
      borderRadius: 8,
      marginBottom: 6,
   },
   layerName: { fontSize: 13, fontWeight: 600, color: "#333" },
   layerDesc: { fontSize: 11, color: "#999", marginTop: 2 },
   toggle: {
      border: "none",
      borderRadius: 6,
      padding: "6px 14px",
      fontSize: 12,
      fontWeight: 700,
      flexShrink: 0,
      transition: "all 0.2s",
   },
   notice: {
      fontSize: 11,
      color: "#bbb",
      padding: 8,
      background: "#f9f9f9",
      borderRadius: 6,
      textAlign: "center",
      marginTop: 4,
   },
};
