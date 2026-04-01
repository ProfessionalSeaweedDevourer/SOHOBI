// hooks/useDongLayer.js
import { useRef } from "react";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import GeoJSON from "ol/format/GeoJSON";
import { Style, Fill, Stroke } from "ol/style";

// ── 동 폴리곤 스타일 상수 (컴포넌트 밖 → 매 렌더마다 재생성 방지) ──
export const DONG_STYLE_DEFAULT = new Style({
   fill: new Fill({ color: "rgba(59,130,246,0.06)" }),
   stroke: new Stroke({ color: "rgba(59,130,246,0.45)", width: 1 }),
});
export const DONG_STYLE_HOVER = new Style({
   fill: new Fill({ color: "rgba(59,130,246,0.22)" }),
   stroke: new Stroke({ color: "#1d4ed8", width: 2.5 }),
});
export const DONG_STYLE_SELECTED = new Style({
   fill: new Fill({ color: "rgba(16,185,129,0.22)" }),
   stroke: new Stroke({ color: "#059669", width: 3 }),
});

// ── 훅: 동 WFS 레이어 로드 / 호버 / 초기화 ──────────────────────
// useCallback 제거 → ref만 사용하므로 메모이제이션 불필요
export function useDongLayer(mapInstance) {
   const dongBoundaryLayerRef = useRef(null);
   const dongHoverFeatRef = useRef(null);
   const dongHoverNameRef = useRef("");

   // ── WFS 폴리곤 최초 1회 로드 ────────────────────────────────────
   const ensureDongBoundaryLayer = async () => {
      const map = mapInstance.current;
      if (!map) return;

      // 이미 서울 전체 로드됨 → 즉시 반환
      if (dongBoundaryLayerRef.current) return;

      try {
         // public/seoul_adm_dong.geojson 직접 로드 (WFS 대신)
         // adm_cd: 8자리, adm_nm: 동이름, gu_nm: 구이름 포함
         const res = await fetch("/seoul_adm_dong.geojson");
         const json = await res.json();
         const features = new GeoJSON().readFeatures(json, {
            dataProjection: "EPSG:4326",
            featureProjection: "EPSG:3857",
         });
         features.forEach((f) => f.setStyle(DONG_STYLE_DEFAULT));
         const layer = new VectorLayer({
            source: new VectorSource({ features }),
            zIndex: 48,
         });
         layer.set("name", "dong_boundary_bg");
         map.addLayer(layer);
         dongBoundaryLayerRef.current = layer;
         console.log(`[동 경계] ${features.length}개 로드 완료 (행정동)`);
      } catch (err) {
         console.error("[동 경계] 로드 실패:", err);
      }
   };

   // ── 스타일 초기화 (모드 off 시) ────────────────────────────────
   const resetDongLayer = () => {
      const layer = dongBoundaryLayerRef.current;
      if (layer?.getSource?.()) {
         layer
            .getSource()
            .getFeatures()
            .forEach((f) => f.setStyle(DONG_STYLE_DEFAULT));
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
      dongHoverFeatRef.current = null;
      dongHoverNameRef.current = "";
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
