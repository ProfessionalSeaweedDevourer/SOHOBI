// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\hooks\useMarkers.js
// 공식 프론트 위치: frontend\src\hooks\map\useMarkers.js

import { useRef, useEffect } from "react";
import { fromLonLat } from "ol/proj";
import { circular } from "ol/geom/Polygon";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { Style, Circle as CircleStyle, Fill, Stroke, Text } from "ol/style";
import Cluster from "ol/source/Cluster";
import { CATEGORIES } from "../../constants/categories";

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
   const color = CAT_COLORS[category] || "#999";
   return new Style({
      image: new CircleStyle({
         radius: selected ? 11 : 7,
         fill: new Fill({ color: selected ? "#fff" : color }),
         stroke: new Stroke({
            color: selected ? color : "#fff",
            width: selected ? 3 : 2,
         }),
      }),
   });
}

// 클러스터 스타일
function makeClusterStyle(size, color) {
   const radius = size < 5 ? 10 : size < 20 ? 13 : size < 100 ? 16 : 20;
   return new Style({
      image: new CircleStyle({
         radius,
         fill: new Fill({ color }),
         stroke: new Stroke({ color: "#fff", width: 2 }),
      }),
      text: new Text({
         text: String(size),
         fill: new Fill({ color: "#fff" }),
         font: `bold ${radius}px sans-serif`,
      }),
   });
}

export function useMarkers(mapInstance, visibleCats) {
   const clusterLayerRef = useRef(null);
   const circleLayerRef = useRef(null);
   const allStoresRef = useRef([]);
   const selectedFeatRef = useRef(null);
   const clusterSourceRef = useRef(null);

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

   const drawMarkers = (stores, visible = visibleCats) => {
      const map = mapInstance.current;
      if (!map) return;
      if (clusterLayerRef.current) map.removeLayer(clusterLayerRef.current);

      const features = stores
         .filter((s) => s.LNG && s.LAT)
         .filter((s) => !s.CAT_CD || visible.has(s.CAT_CD))
         .map((store) => {
            const f = new Feature({
               geometry: new Point(
                  fromLonLat([parseFloat(store.LNG), parseFloat(store.LAT)]),
               ),
            });
            f.setProperties({ store });
            return f;
         });

      const vectorSource = new VectorSource({ features });
      const clusterSource = new Cluster({ source: vectorSource, distance: 40 });
      clusterSourceRef.current = clusterSource;

      const layer = new VectorLayer({
         source: clusterSource,
         zIndex: 100,
         style: (feature) => {
            const members = feature.get("features") || [];
            if (members.length === 1) {
               const store = members[0].get("store");
               return makeMarkerStyle(store?.CAT_CD);
            }
            // 클러스터 - 대표 카테고리 색상
            const cats = members
               .map((f) => f.get("store")?.CAT_CD)
               .filter(Boolean);
            const topCat = cats.sort(
               (a, b) =>
                  cats.filter((c) => c === b).length -
                  cats.filter((c) => c === a).length,
            )[0];
            const color = CAT_COLORS[topCat] || "#888";
            return makeClusterStyle(members.length, color);
         },
      });

      map.addLayer(layer);
      clusterLayerRef.current = layer;
   };

   const selectMarker = (feature) => {
      if (selectedFeatRef.current) {
         const prev = selectedFeatRef.current;
         prev.setStyle(makeMarkerStyle(prev.get("store")?.CAT_CD));
      }
      if (!feature) {
         selectedFeatRef.current = null;
         return;
      }
      const store = feature.get("store");
      feature.setStyle(makeMarkerStyle(store?.CAT_CD, true));
      selectedFeatRef.current = feature;
   };

   const clearMarkers = () => {
      const map = mapInstance.current;
      if (!map) return;
      if (clusterLayerRef.current) {
         map.removeLayer(clusterLayerRef.current);
         clusterLayerRef.current = null;
      }
      if (circleLayerRef.current) {
         map.removeLayer(circleLayerRef.current);
         circleLayerRef.current = null;
      }
      allStoresRef.current = [];
   };

   const visibleKey = [...visibleCats].sort().join(",");
   useEffect(() => {
      if (allStoresRef.current.length > 0)
         drawMarkers(allStoresRef.current, visibleCats);
   }, [visibleKey]); // eslint-disable-line

   // 클러스터 클릭 시 단일 피처 반환 헬퍼
   const getSingleFeature = (feature) => {
      const members = feature?.get("features");
      if (members?.length === 1) return members[0];
      return null;
   };

   return {
      markerLayerRef: clusterLayerRef,
      allStoresRef,
      drawCircle,
      drawMarkers,
      clearMarkers,
      selectMarker,
      getSingleFeature,
   };
}
