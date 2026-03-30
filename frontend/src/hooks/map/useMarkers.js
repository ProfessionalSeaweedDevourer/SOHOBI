// hooks/useMarkers.js
import { useRef, useEffect } from "react";
import { fromLonLat } from "ol/proj";
import { circular } from "ol/geom/Polygon";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { Style, Circle as CircleStyle, Fill, Stroke } from "ol/style";
import { CATEGORIES } from "../../constants/categories";

// ── 마커 스타일 생성 ───────────────────────────────────────────
const CAT_COLORS = {
   I2: "#FF6B6B",
   G2: "#FF9800",
   S2: "#4ecdc4",
   L1: "#2196F3",
   I1: "#9C27B0",
   P1: "#F59E0B",
   Q1: "#E03131",
   R1: "#2F9E44",
   M1: "#1971C2",
   N1: "#607D8B",
};

function makeMarkerStyle(category, selected = false) {
   let color = "#999";
   color = CAT_COLORS[category] || "#999";
   return new Style({
      image: new CircleStyle({
         radius: selected ? 10 : 7,
         fill: new Fill({ color }),
         stroke: new Stroke({ color: "#fff", width: selected ? 3 : 2 }),
      }),
   });
}

// ── 훅: 마커/반경원 그리기 ─────────────────────────────────────
export function useMarkers(mapInstance, visibleCats) {
   const markerLayerRef = useRef(null);
   const circleLayerRef = useRef(null);
   const allStoresRef = useRef([]);

   // ── 반경 원 그리기 ──────────────────────────────────────────
   const drawCircle = (lng, lat, radius) => {
      const map = mapInstance.current;
      if (!map) return;
      if (circleLayerRef.current) map.removeLayer(circleLayerRef.current);
      const circle = circular([lng, lat], radius, 64);
      circle.transform("EPSG:4326", "EPSG:3857");
      const feature = new Feature(circle);
      feature.setStyle(
         new Style({
            stroke: new Stroke({ color: "#2563EB", width: 2 }),
            fill: new Fill({ color: "rgba(37,99,235,0.08)" }),
         }),
      );
      const layer = new VectorLayer({
         source: new VectorSource({ features: [feature] }),
         zIndex: 99,
      });
      map.addLayer(layer);
      circleLayerRef.current = layer;
   };

   // ── 마커 렌더링 (카테고리 필터 적용) ────────────────────────
   const drawMarkers = (stores, visible = visibleCats) => {
      const map = mapInstance.current;
      if (!map) return;
      if (markerLayerRef.current) map.removeLayer(markerLayerRef.current);

      const features = stores
         .filter((s) => s.LNG && s.LAT)
         .filter((s) => {
            const code = s.CAT_CD;
            if (!code) return true; // 코드 없으면 표시
            return visible.has(code);
         })
         .map((store) => {
            const feature = new Feature({
               geometry: new Point(
                  fromLonLat([parseFloat(store.LNG), parseFloat(store.LAT)]),
               ),
            });
            feature.setProperties({ store });
            feature.setStyle(makeMarkerStyle(store.CAT_CD));
            return feature;
         });

      const layer = new VectorLayer({
         source: new VectorSource({ features }),
         zIndex: 100,
      });
      map.addLayer(layer);
      markerLayerRef.current = layer;
   };

   // ── 마커/원 제거 ────────────────────────────────────────────
   const clearMarkers = () => {
      const map = mapInstance.current;
      if (!map) return;
      if (markerLayerRef.current) {
         map.removeLayer(markerLayerRef.current);
         markerLayerRef.current = null;
      }
      if (circleLayerRef.current) {
         map.removeLayer(circleLayerRef.current);
         circleLayerRef.current = null;
      }
      allStoresRef.current = [];
   };

   // visibleCats 바뀌면 마커 재렌더링
   // Set 참조 동일성 문제 → size + join으로 변경 감지
   const visibleKey = [...visibleCats].sort().join(",");
   useEffect(() => {
      if (allStoresRef.current.length > 0)
         drawMarkers(allStoresRef.current, visibleCats);
   }, [visibleKey]); // eslint-disable-line react-hooks/exhaustive-deps

   return {
      markerLayerRef,
      allStoresRef,
      drawCircle,
      drawMarkers,
      clearMarkers,
   };
}
