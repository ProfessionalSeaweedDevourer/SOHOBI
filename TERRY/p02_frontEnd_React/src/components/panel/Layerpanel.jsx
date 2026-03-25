// 위치: src/components/panel/Layerpanel.jsx

import { useState } from "react";
import TileLayer from "ol/layer/Tile";
import TileWMS from "ol/source/TileWMS";

function makeWmsLayer(layerName, layerKey, zIndex, vworldKey) {
   const layer = new TileLayer({
      source: new TileWMS({
         url: `/wms/req/wms?KEY=${vworldKey}&DOMAIN=localhost`,
         params: {
            SERVICE: "WMS",
            VERSION: "1.3.0",
            REQUEST: "GetMap",
            LAYERS: layerName,
            STYLES: layerName,
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

export default function LayerPanel({ map, vworldKey, wmsLayerRef }) {
   const [cadastralOn, setCadastralOn] = useState(false);
   const [touristInfoOn, setTouristInfoOn] = useState(false);
   const [touristSpotOn, setTouristSpotOn] = useState(false);
   const [marketOn, setMarketOn] = useState(false);

   // ── 지적도 ──────────────────────────────────────────────────────
   const toggleCadastral = () => {
      if (cadastralOn) {
         if (wmsLayerRef.current) {
            map.removeLayer(wmsLayerRef.current);
            wmsLayerRef.current = null;
         }
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
            zIndex: 200,
         });
         layer.set("name", "cadastral");
         map.addLayer(layer);
         wmsLayerRef.current = layer;
         setCadastralOn(true);
      }
   };

   // ── 관광안내소 ──────────────────────────────────────────────────
   const toggleTouristInfo = () => {
      if (touristInfoOn) {
         map.getLayers()
            .getArray()
            .filter((l) => l.get("name") === "tourist_info")
            .forEach((l) => map.removeLayer(l));
         setTouristInfoOn(false);
      } else {
         map.addLayer(
            makeWmsLayer("lt_p_dgtouristinfo", "tourist_info", 201, vworldKey),
         );
         setTouristInfoOn(true);
      }
   };

   // ── 관광지·문화시설 ─────────────────────────────────────────────
   const toggleTouristSpot = () => {
      if (touristSpotOn) {
         map.getLayers()
            .getArray()
            .filter((l) => l.get("name") === "tourist_spot")
            .forEach((l) => map.removeLayer(l));
         setTouristSpotOn(false);
      } else {
         map.addLayer(
            makeWmsLayer(
               "lt_c_uo601,lt_p_dgmuseumart",
               "tourist_spot",
               202,
               vworldKey,
            ),
         );
         setTouristSpotOn(true);
      }
   };

   // ── 전통시장 ────────────────────────────────────────────────────
   const toggleMarket = () => {
      if (marketOn) {
         map.getLayers()
            .getArray()
            .filter((l) => l.get("name") === "market")
            .forEach((l) => map.removeLayer(l));
         setMarketOn(false);
      } else {
         map.addLayer(
            makeWmsLayer("lt_p_tradsijang", "market", 203, vworldKey),
         );
         setMarketOn(true);
      }
   };

   return (
      <div style={S.panel}>
         <div style={S.title}>🗂️ 레이어 관리</div>

         <LayerRow
            label="📋 지적도"
            desc="토지 경계 · 공시지가"
            on={cadastralOn}
            color="#2196F3"
            onClick={toggleCadastral}
         />
         <LayerRow
            label="ℹ️ 관광안내소"
            desc="lt_p_dgtouristinfo"
            on={touristInfoOn}
            color="#0288D1"
            onClick={toggleTouristInfo}
         />
         <LayerRow
            label="🏛️ 관광지·문화"
            desc="lt_c_uo601 · lt_p_dgmuseumart"
            on={touristSpotOn}
            color="#7B1FA2"
            onClick={toggleTouristSpot}
         />
         <LayerRow
            label="🏪 전통시장"
            desc="lt_p_tradsijang"
            on={marketOn}
            color="#E53935"
            onClick={toggleMarket}
         />

         <div style={S.notice}>💡 각 레이어 클릭 시 상세 팝업 표시</div>

      </div>
   );
}

function LayerRow({ label, desc, on, color, onClick }) {
   return (
      <div style={S.row}>
         <div style={{ flex: 1 }}>
            <div style={S.layerName}>{label}</div>
            <div style={S.layerDesc}>{desc}</div>
         </div>
         <button
            onClick={onClick}
            style={{
               ...S.toggle,
               background: on ? color : "#e0e0e0",
               color: on ? "#fff" : "#555",
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
      minWidth: 220,
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
   row: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: 10,
      background: "#f9f9f9",
      borderRadius: 8,
      marginBottom: 8,
   },
   layerName: { fontSize: 13, fontWeight: 600, color: "#333" },
   layerDesc: { fontSize: 11, color: "#999", marginTop: 2 },
   toggle: {
      border: "none",
      borderRadius: 6,
      padding: "6px 14px",
      fontSize: 12,
      fontWeight: 700,
      cursor: "pointer",
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
      marginBottom: 8,
   },
};