// hooks/useDongLayer.js
import { useRef } from "react";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import TileLayer from "ol/layer/Tile";
import TileWMS from "ol/source/TileWMS";
import GeoJSON from "ol/format/GeoJSON";
import { Style, Fill, Stroke } from "ol/style";

// ── 동 폴리곤 스타일 상수 (컴포넌트 밖 → 매 렌더마다 재생성 방지) ──
export const DONG_STYLE_DEFAULT  = new Style({ fill: new Fill({ color: "rgba(59,130,246,0.06)" }),  stroke: new Stroke({ color: "rgba(59,130,246,0.45)", width: 1 }) });
export const DONG_STYLE_HOVER    = new Style({ fill: new Fill({ color: "rgba(59,130,246,0.22)" }),  stroke: new Stroke({ color: "#1d4ed8", width: 2.5 }) });
export const DONG_STYLE_SELECTED = new Style({ fill: new Fill({ color: "rgba(16,185,129,0.22)" }), stroke: new Stroke({ color: "#059669", width: 3 }) });

const REALESTATE_URL = "http://localhost:8682";
const VWORLD_KEY     = import.meta.env.VITE_VWORLD_API_KEY;

// ── 훅: 동 WFS 레이어 로드 / 호버 / 초기화 ──────────────────────
// useCallback 제거 → ref만 사용하므로 메모이제이션 불필요
export function useDongLayer(mapInstance) {
   const dongBoundaryLayerRef = useRef(null);
   const dongHoverFeatRef     = useRef(null);
   const dongHoverNameRef     = useRef("");

   // ── WFS 폴리곤 최초 1회 로드 ────────────────────────────────────
   const ensureDongBoundaryLayer = async () => {
      const map = mapInstance.current;
      if (!map || dongBoundaryLayerRef.current) return;

      try {
         const res      = await fetch(`${REALESTATE_URL}/realestate/wfs-dong?sig_cd=11`);
         const json     = await res.json();
         const features = new GeoJSON().readFeatures(json, {
            dataProjection: "EPSG:3857", featureProjection: "EPSG:3857",
         });
         features.forEach(f => f.setStyle(DONG_STYLE_DEFAULT));
         const layer = new VectorLayer({
            source: new VectorSource({ features }),
            zIndex: 48,
         });
         layer.set("name", "dong_boundary_bg");
         map.addLayer(layer);
         dongBoundaryLayerRef.current = layer;
         console.log(`[동 WFS] ${features.length}개 로드 완료`);
      } catch (err) {
         console.error("[동 WFS] 로드 실패, WMS fallback:", err);
         const fallback = new TileLayer({
            source: new TileWMS({
               url: `/wms/req/wms?KEY=${VWORLD_KEY}&DOMAIN=localhost`,
               params: { SERVICE:"WMS", VERSION:"1.3.0", REQUEST:"GetMap",
                         LAYERS:"lt_c_ademd_info", FORMAT:"image/png",
                         TRANSPARENT:"TRUE", CRS:"EPSG:3857" },
               crossOrigin: "anonymous", transition: 0,
            }),
            opacity: 0.6, zIndex: 48,
         });
         fallback.set("name", "dong_boundary_bg");
         map.addLayer(fallback);
         dongBoundaryLayerRef.current = fallback;
      }
   };

   // ── 스타일 초기화 (모드 off 시) ────────────────────────────────
   const resetDongLayer = () => {
      const layer = dongBoundaryLayerRef.current;
      if (layer?.getSource?.()) {
         layer.getSource().getFeatures().forEach(f => f.setStyle(DONG_STYLE_DEFAULT));
      }
      dongHoverFeatRef.current = null;
      dongHoverNameRef.current = "";
   };

   // ── 레이어 제거 ─────────────────────────────────────────────────
   const removeDongLayer = () => {
      const map = mapInstance.current;
      if (!map || !dongBoundaryLayerRef.current) return;
      map.removeLayer(dongBoundaryLayerRef.current);
      dongBoundaryLayerRef.current = null;
      dongHoverFeatRef.current     = null;
      dongHoverNameRef.current     = "";
   };

   return {
      dongBoundaryLayerRef,
      dongHoverFeatRef,
      dongHoverNameRef,
      ensureDongBoundaryLayer,
      resetDongLayer,
      removeDongLayer,
   };
}