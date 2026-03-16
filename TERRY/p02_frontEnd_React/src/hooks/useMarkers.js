// hooks/useMarkers.js
import { useRef, useEffect } from "react";
import { fromLonLat } from "ol/proj";
import { circular } from "ol/geom/Polygon";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { Style, Circle as CircleStyle, Fill, Stroke } from "ol/style";
import { CATEGORIES } from "../constants/categories";

// ── 마커 스타일 생성 ───────────────────────────────────────────
const CAT_COLORS = {
   음식: "#FF6B6B", 소매: "#FF9800", 생활서비스: "#4ecdc4",
   부동산: "#2196F3", 숙박: "#9C27B0", 교육: "#FFD700",
   의료: "#E03131", 스포츠: "#2F9E44", "과학·기술": "#1971C2",
   "수리·개인": "#7B4F2E",
};

function makeMarkerStyle(category, selected = false) {
   let color = "#999";
   for (const [key, val] of Object.entries(CAT_COLORS)) {
      if (category?.includes(key)) { color = val; break; }
   }
   return new Style({
      image: new CircleStyle({
         radius: selected ? 10 : 7,
         fill:   new Fill({ color }),
         stroke: new Stroke({ color: "#fff", width: selected ? 3 : 2 }),
      }),
   });
}

// ── 훅: 마커/반경원 그리기 ─────────────────────────────────────
export function useMarkers(mapInstance, visibleCats) {
   const markerLayerRef = useRef(null);
   const circleLayerRef = useRef(null);
   const allStoresRef   = useRef([]);

   // ── 반경 원 그리기 ──────────────────────────────────────────
   const drawCircle = (lng, lat, radius) => {
      const map = mapInstance.current;
      if (!map) return;
      if (circleLayerRef.current) map.removeLayer(circleLayerRef.current);
      const circle = circular([lng, lat], radius, 64);
      circle.transform("EPSG:4326", "EPSG:3857");
      const feature = new Feature(circle);
      feature.setStyle(new Style({
         stroke: new Stroke({ color: "#2563EB", width: 2 }),
         fill:   new Fill({ color: "rgba(37,99,235,0.08)" }),
      }));
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
         .filter((s) => s.경도 && s.위도)
         .filter((s) => {
            const key = CATEGORIES.find((c) => s.상권업종대분류명?.includes(c.key))?.key;
            return key ? visible.has(key) : true;
         })
         .map((store) => {
            const feature = new Feature({
               geometry: new Point(fromLonLat([parseFloat(store.경도), parseFloat(store.위도)])),
            });
            feature.setProperties({ store });
            feature.setStyle(makeMarkerStyle(store.상권업종대분류명));
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
      if (markerLayerRef.current) { map.removeLayer(markerLayerRef.current); markerLayerRef.current = null; }
      if (circleLayerRef.current) { map.removeLayer(circleLayerRef.current); circleLayerRef.current = null; }
      allStoresRef.current = [];
   };

   // visibleCats 바뀌면 마커 재렌더링
   useEffect(() => {
      if (allStoresRef.current.length > 0)
         drawMarkers(allStoresRef.current, visibleCats);
   }, [visibleCats]); // eslint-disable-line react-hooks/exhaustive-deps

   return { markerLayerRef, allStoresRef, drawCircle, drawMarkers, clearMarkers };
}