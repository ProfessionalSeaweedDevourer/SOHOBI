// hooks/useLandmarkLayer.js
// KTO 랜드마크(관광지/문화시설) + 축제 + 학교 레이어

import { useRef } from "react";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { fromLonLat } from "ol/proj";
import { Style, Circle as CircleStyle, Fill, Stroke } from "ol/style";

const MAP_URL = import.meta.env.VITE_MAP_URL || "/map-api";

// ── 타입별 스타일 설정 ────────────────────────────────────────
const TYPE_STYLE = {
   12: { color: "#f59e0b", label: "관광" }, // 관광지 - 노랑
   14: { color: "#8b5cf6", label: "문화" }, // 문화시설 - 보라
   15: { color: "#ef4444", label: "축제" }, // 축제 - 빨강
   school: { color: "#10b981", label: "학교" }, // 학교 - 초록
};

function makeStyle(typeKey, selected = false) {
   const { color } = TYPE_STYLE[typeKey] || { color: "#999" };
   return new Style({
      image: new CircleStyle({
         radius: selected ? 10 : 7,
         fill: new Fill({ color: selected ? "#fff" : color }),
         stroke: new Stroke({
            color: selected ? color : "#fff",
            width: selected ? 3 : 2,
         }),
      }),
   });
}

export function useLandmarkLayer(mapInstance) {
   // 레이어 ref
   const landmarkLayerRef = useRef(null); // 관광지+문화시설 (DB)
   const festivalLayerRef = useRef(null); // 축제 (API)
   const schoolLayerRef = useRef(null); // 학교 (DB)
   const selectedFeatRef = useRef(null);

   // ── 공통: feature 생성 ───────────────────────────────────────
   const makeFeatures = (items, typeKey) =>
      items
         .filter((d) => d.lng && d.lat)
         .map((d) => {
            const f = new Feature({
               geometry: new Point(fromLonLat([d.lng, d.lat])),
            });
            f.set("lmData", d);
            f.set("lmType", typeKey);
            f.setStyle(makeStyle(typeKey));
            return f;
         });

   // ── 레이어 추가 헬퍼 ─────────────────────────────────────────
   const addLayer = (features, zIndex) => {
      const map = mapInstance.current;
      if (!map) return null;
      const layer = new VectorLayer({
         source: new VectorSource({ features }),
         zIndex,
      });
      map.addLayer(layer);
      return layer;
   };

   // ── 관광지 + 문화시설 (DB) ───────────────────────────────────
   // adm_cd 없으면 서울 전체 조회
   const loadLandmarks = async (adm_cd) => {
      try {
         const url = adm_cd
            ? `${MAP_URL}/map/landmarks?adm_cd=${adm_cd}&types=12,14`
            : `${MAP_URL}/map/landmarks?types=12,14`;
         const json = await (await fetch(url)).json();
         const features = makeFeatures(json.landmarks || [], "12");
         // 타입별 스타일 적용
         features.forEach((f) => {
            const d = f.get("lmData");
            f.setStyle(makeStyle(String(d.content_type_id)));
         });
         if (landmarkLayerRef.current) {
            mapInstance.current?.removeLayer(landmarkLayerRef.current);
         }
         landmarkLayerRef.current = addLayer(features, 210);
      } catch (e) {
         console.error("[useLandmarkLayer] loadLandmarks:", e);
      }
   };

   // ── 축제 (API 실시간) ────────────────────────────────────────
   const loadFestivals = async (adm_cd) => {
      try {
         const res = await fetch(`${MAP_URL}/map/festivals?adm_cd=${adm_cd}`);
         const json = await res.json();
         const features = makeFeatures(json.festivals || [], "15");
         if (festivalLayerRef.current) {
            mapInstance.current?.removeLayer(festivalLayerRef.current);
         }
         festivalLayerRef.current = addLayer(features, 211);
      } catch (e) {
         console.error("[useLandmarkLayer] loadFestivals:", e);
      }
   };

   // ── 학교 (DB) ────────────────────────────────────────────────
   const loadSchools = async (sgg_nm) => {
      try {
         const url = sgg_nm
            ? `${MAP_URL}/map/schools?sgg_nm=${encodeURIComponent(sgg_nm)}`
            : `${MAP_URL}/map/schools`;
         const res = await fetch(url);
         const json = await res.json();
         const features = makeFeatures(
            json.schools || [],
            "school",
            "school_id",
         );
         if (schoolLayerRef.current) {
            mapInstance.current?.removeLayer(schoolLayerRef.current);
         }
         schoolLayerRef.current = addLayer(features, 212);
      } catch (e) {
         console.error("[useLandmarkLayer] loadSchools:", e);
      }
   };

   // ── 레이어 표시/숨김 ─────────────────────────────────────────
   const setLandmarkVisible = (v) => landmarkLayerRef.current?.setVisible(v);
   const setFestivalVisible = (v) => festivalLayerRef.current?.setVisible(v);
   const setSchoolVisible = (v) => schoolLayerRef.current?.setVisible(v);

   // ── 마커 하이라이트 ──────────────────────────────────────────
   const selectLandmark = (feature) => {
      if (selectedFeatRef.current) {
         const prev = selectedFeatRef.current;
         prev.setStyle(makeStyle(prev.get("lmType")));
      }
      if (!feature) {
         selectedFeatRef.current = null;
         return;
      }
      feature.setStyle(makeStyle(feature.get("lmType"), true));
      selectedFeatRef.current = feature;
   };

   // ── 레이어 제거 ──────────────────────────────────────────────
   const clearLandmarks = () => {
      const map = mapInstance.current;
      if (!map) return;
      [landmarkLayerRef, festivalLayerRef, schoolLayerRef].forEach((ref) => {
         if (ref.current) {
            map.removeLayer(ref.current);
            ref.current = null;
         }
      });
   };

   return {
      landmarkLayerRef,
      festivalLayerRef,
      schoolLayerRef,
      loadLandmarks,
      loadFestivals,
      loadSchools,
      setLandmarkVisible,
      setFestivalVisible,
      setSchoolVisible,
      selectLandmark,
      clearLandmarks,
   };
}
