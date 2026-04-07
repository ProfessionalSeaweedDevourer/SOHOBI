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
   const selectedFeatRef = useRef(null); // 선택된 STORE_ID (feature 참조 대신 ID로 비교)
   const clusterSourceRef = useRef(null);
   const vectorSourceRef = useRef(null);

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
         zIndex: 90,
      });
      map.addLayer(layer);
      circleLayerRef.current = layer;
   };

   const drawMarkers = (stores, visible = visibleCats) => {
      const map = mapInstance.current;
      if (!map) return;

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

      // 레이어가 이미 존재하면 소스만 교체 (Layer 재생성 생략)
      if (clusterLayerRef.current && vectorSourceRef.current) {
         selectedFeatRef.current = null;
         vectorSourceRef.current.clear();
         vectorSourceRef.current.addFeatures(features);
         return;
      }

      if (clusterLayerRef.current) map.removeLayer(clusterLayerRef.current);

      const vectorSource = new VectorSource({ features });
      vectorSourceRef.current = vectorSource;
      const clusterSource = new Cluster({ source: vectorSource, distance: 40 });
      clusterSourceRef.current = clusterSource;

      const layer = new VectorLayer({
         source: clusterSource,
         zIndex: 200,
         style: (feature) => {
            const members = feature.get("features") || [];
            // feature 참조 대신 STORE_ID로 비교 (zoom 변경 시 cluster가 feature 재생성)
            const selId = selectedFeatRef.current;
            const isSel =
               selId != null &&
               members.some((f) => {
                  const s = f.get("store");
                  return (s?.STORE_ID || s?.store_id) === selId;
               });

            if (members.length === 1) {
               const store = members[0].get("store");
               return makeMarkerStyle(store?.CAT_CD, isSel);
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
            if (isSel) {
               // 선택된 클러스터: 색 반전 (배경=흰색, 글자=원래색, 테두리=원래색)
               const radius =
                  members.length > 99 ? 18 : members.length > 9 ? 15 : 12;
               return new Style({
                  image: new CircleStyle({
                     radius: radius + 3,
                     fill: new Fill({ color: "#fff" }),
                     stroke: new Stroke({ color, width: 3 }),
                  }),
                  text: new Text({
                     text: String(members.length),
                     fill: new Fill({ color }),
                     font: `bold ${radius}px sans-serif`,
                  }),
               });
            }
            return makeClusterStyle(members.length, color);
         },
      });

      map.addLayer(layer);
      clusterLayerRef.current = layer;
   };

   // 클러스터/단일 모두 대응: cluster feature는 "features" 배열 안에 store가 있음
   const _getCatCd = (feat) => {
      if (!feat) return undefined;
      const direct = feat.get("store");
      if (direct) return direct.CAT_CD;
      const members = feat.get("features");
      return members?.[0]?.get("store")?.CAT_CD;
   };

   // 스토어 ID로 클러스터 소스에서 feature 찾아 하이라이트
   const _highlightById = (storeId) => {
      if (!storeId) return;
      selectedFeatRef.current = storeId;
      clusterLayerRef.current?.changed();
   };

   const selectMarker = (feature) => {
      if (!feature) {
         selectedFeatRef.current = null;
      } else {
         // cluster wrapper에서 STORE_ID 추출해서 저장 (zoom 변경 시 feature 재생성에 대응)
         const members = feature.get("features") || [];
         const store = members[0]?.get("store");
         selectedFeatRef.current = store?.STORE_ID || store?.store_id || null;
      }
      clusterLayerRef.current?.changed();

      // 지도 이동은 하지 않음
      // 이동이 필요한 경우(클러스터 팝업 상가 선택)는 MapView에서 직접 처리
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
      vectorSourceRef.current = null;
      clusterSourceRef.current = null;
      selectedFeatRef.current = null;
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
      highlightById: _highlightById,
      getSingleFeature,
   };
}
