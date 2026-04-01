// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\hooks\usePopulationLayer.js
// 공식 프론트 위치: frontend\src\hooks\map\usePopulationLayer.js

// 서울 실시간 유동인구 히트맵 레이어 (citydata_ppltn API)

import { useRef } from "react";
import HeatmapLayer from "ol/layer/Heatmap";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { fromLonLat } from "ol/proj";
import { Style, Circle as CircleStyle, Fill, Stroke, Text } from "ol/style";

const POP_URL = import.meta.env.VITE_MAP_URL || "http://localhost:8681";

// 혼잡도 → 히트맵 강도 (0~1)
const CONGEST_WEIGHT = {
   붐빔: 1.0,
   "약간 붐빔": 0.65,
   보통: 0.35,
   여유: 0.1,
};

// 혼잡도별 색상 (범례용)
export const CONGEST_STYLE = {
   붐빔: { color: "#E03131", bg: "#FFF0F0", emoji: "🔴", label: "붐빔" },
   "약간 붐빔": {
      color: "#FF9800",
      bg: "#FFF8F0",
      emoji: "🟠",
      label: "약간 붐빔",
   },
   보통: { color: "#2196F3", bg: "#F0F4FF", emoji: "🔵", label: "보통" },
   여유: { color: "#2F9E44", bg: "#F0FFF4", emoji: "🟢", label: "여유" },
};

export function usePopulationLayer(mapInstance) {
   const heatLayerRef = useRef(null); // 히트맵 레이어
   const dotLayerRef = useRef(null); // 장소명 표시 레이어 (줌인 시)
   const sourceRef = useRef(null);

   const loadPopulation = async () => {
      const map = mapInstance.current;
      if (!map) return 0;
      try {
         const res = await fetch(`${POP_URL}/map/population/all`);
         const json = await res.json();
         const spots = json.data || [];

         const features = spots
            .filter((s) => s.lat && s.lng)
            .map((s) => {
               const f = new Feature({
                  geometry: new Point(fromLonLat([s.lng, s.lat])),
               });
               const weight = CONGEST_WEIGHT[s.혼잡도] ?? 0.2;
               f.set("weight", weight);
               f.set("popData", s);
               return f;
            });

         const source = new VectorSource({ features });
         sourceRef.current = source;

         // ── 히트맵 레이어 ──────────────────────────────────────
         if (heatLayerRef.current) map.removeLayer(heatLayerRef.current);
         const heatLayer = new HeatmapLayer({
            source,
            blur: 40,
            radius: 30,
            weight: (f) => f.get("weight"),
            // 파란→초록→노랑→빨강 온도 색상
            gradient: ["#0000ff", "#00ffff", "#00ff00", "#ffff00", "#ff0000"],
            zIndex: 215,
            opacity: 0.75,
         });
         map.addLayer(heatLayer);
         heatLayerRef.current = heatLayer;

         // ── 장소명 마커 (줌 14 이상에서만 표시) ──────────────
         if (dotLayerRef.current) map.removeLayer(dotLayerRef.current);
         const dotLayer = new VectorLayer({
            source,
            minZoom: 13,
            style: (f) => {
               const d = f.get("popData");
               const cs = CONGEST_STYLE[d?.혼잡도];
               return new Style({
                  image: new CircleStyle({
                     radius: 5,
                     fill: new Fill({ color: cs?.color || "#888" }),
                     stroke: new Stroke({ color: "#fff", width: 1.5 }),
                  }),
                  text: new Text({
                     text: d?.name || "",
                     font: "bold 11px sans-serif",
                     offsetY: -14,
                     fill: new Fill({ color: "#222" }),
                     stroke: new Stroke({ color: "#fff", width: 3 }),
                  }),
               });
            },
            zIndex: 216,
         });
         map.addLayer(dotLayer);
         dotLayerRef.current = dotLayer;

         return features.length;
      } catch (e) {
         console.error("[usePopulationLayer]", e);
         return 0;
      }
   };

   const setPopVisible = (v) => {
      heatLayerRef.current?.setVisible(v);
      dotLayerRef.current?.setVisible(v);
   };

   const clearPop = () => {
      const map = mapInstance.current;
      if (!map) return;
      [heatLayerRef, dotLayerRef].forEach((ref) => {
         if (ref.current) {
            map.removeLayer(ref.current);
            ref.current = null;
         }
      });
   };

   return {
      heatLayerRef,
      dotLayerRef,
      loadPopulation,
      setPopVisible,
      clearPop,
   };
}
