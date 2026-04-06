// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\panel\Layerpanel.jsx
// 공식 프론트 위치: frontend\src\components\map\panel\Layerpanel.jsx

import React, { useState } from "react";
import TileLayer from "ol/layer/Tile";
import TileWMS from "ol/source/TileWMS";
import "./Layerpanel.css";

function makeWmsLayer(layerName, layerKey, zIndex, vworldKey) {
   const layer = new TileLayer({
      source: new TileWMS({
         url: `${import.meta.env.VITE_API_URL || ""}/wms/req/wms?KEY=${vworldKey}&DOMAIN=localhost`,
         params: {
            SERVICE: "WMS",
            VERSION: "1.3.0",
            REQUEST: "GetMap",
            LAYERS: layerName,
            STYLES: "",
            FORMAT: "image/png",
            TRANSPARENT: "TRUE",
            CRS: "EPSG:3857",
         },
         crossOrigin: "anonymous",
         transition: 0,
      }),
      opacity: 1,
      zIndex,
   });
   layer.set("name", layerKey);
   return layer;
}

function makeCadastralLayer(vworldKey) {
   const layer = new TileLayer({
      source: new TileWMS({
         url: `${import.meta.env.VITE_API_URL || ""}/wms/req/wms?KEY=${vworldKey}&DOMAIN=localhost`,
         params: {
            SERVICE: "WMS",
            VERSION: "1.3.0",
            REQUEST: "GetMap",
            LAYERS: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
            STYLES: ",",
            FORMAT: "image/png",
            TRANSPARENT: "TRUE",
            CRS: "EPSG:3857",
         },
         crossOrigin: "anonymous",
         transition: 0,
      }),
      opacity: 0.7,
      zIndex: 200,
      minZoom: 17,
   });
   layer.set("name", "cadastral");
   return layer;
}

export default function LayerPanel({
   map,
   vworldKey,
   wmsLayerRef,
   currentZoom,
   landmarkLayerRef,
   festivalLayerRef,
   schoolLayerRef,
   landmarkLoaded,
   festivalLoaded,
   schoolLoaded,
}) {
   const [cadastralOn, setCadastralOn] = useState(true);
   const [touristInfoOn, setTouristInfoOn] = useState(true);
   const [landmarkOn, setLandmarkOn] = useState(true);
   const [festivalOn, setFestivalOn] = useState(true);
   const [schoolOn, setSchoolOn] = useState(true);

   // 초기 레이어 자동 추가
   const initDoneRef = React.useRef(false);
   React.useEffect(() => {
      if (!map || initDoneRef.current) return;
      initDoneRef.current = true;
      // 지적도 초기 ON (zoom 17+ 에서만 타일 데이터 반환)
      const layer = makeCadastralLayer(vworldKey);
      map.addLayer(layer);
      wmsLayerRef.current = layer;
      // 관광안내소 초기 ON
      map.addLayer(
         makeWmsLayer("lt_p_dgtouristinfo", "tourist_info", 215, vworldKey),
      );
   }, [map]); // eslint-disable-line

   // ── 지적도 ──────────────────────────────────────────────────
   const toggleCadastral = () => {
      const layer =
         map.getLayers().getArray().find((l) => l.get("name") === "cadastral") ??
         wmsLayerRef.current;
      if (!layer) return;
      const next = !cadastralOn;
      layer.setVisible(next);
      wmsLayerRef.current = layer;
      setCadastralOn(next);
   };

   // ── 관광안내소 (VWorld WMS) ──────────────────────────────────
   const toggleTouristInfo = () => {
      const layer =
         map.getLayers().getArray().find((l) => l.get("name") === "tourist_info") ??
         null;
      if (!layer) return;
      const next = !touristInfoOn;
      layer.setVisible(next);
      setTouristInfoOn(next);
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
      <div className="lp-panel">
         <div className="lp-title">🗂️ 레이어 관리</div>

         <div className="lp-section-label">VWorld</div>
         <LayerRow
            label="📋 지적도"
            desc={
               cadastralOn && currentZoom < 17
                  ? `줌 ${Math.floor(currentZoom)}/17 — 더 확대하면 표시`
                  : "토지 경계 (줌 17+ 필요)"
            }
            on={cadastralOn}
            color="#2196F3"
            onClick={toggleCadastral}
         />
         <LayerRow
            label="ℹ️ 관광안내소"
            desc="VWorld WMS"
            on={touristInfoOn}
            color="#0288D1"
            onClick={toggleTouristInfo}
         />

         <div className="lp-section-label">한국관광공사</div>
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

         <div className="lp-section-label">교육</div>
         <LayerRow
            label="🏫 학교"
            desc="DB 마커"
            on={schoolOn}
            color="#10b981"
            onClick={toggleSchool}
            disabled={!schoolLoaded}
         />

         <div className="lp-notice">💡 동 클릭 시 해당 구역 마커 자동 로드</div>
      </div>
   );
}

function LayerRow({ label, desc, on, color, onClick, disabled }) {
   return (
      <div className="lp-row" style={{ opacity: disabled ? 0.4 : 1 }}>
         <div style={{ flex: 1 }}>
            <div className="lp-layer-name">{label}</div>
            <div className="lp-layer-desc">{desc}</div>
         </div>
         <button
            onClick={disabled ? undefined : onClick}
            className={`lp-toggle ${on ? "" : "lp-toggle--off"}`}
            style={{
               background: on ? color : undefined,
               color: on ? "#fff" : undefined,
               cursor: disabled ? "default" : "pointer",
            }}
         >
            {on ? "ON" : "OFF"}
         </button>
      </div>
   );
}
