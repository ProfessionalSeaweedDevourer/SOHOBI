// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\hooks\useLandmarkLayer.js
// 공식 프론트 위치: frontend\src\hooks\map\useLandmarkLayer.js

import { useEffect, useRef } from "react";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import XYZ from "ol/source/XYZ";
import { fromLonLat } from "ol/proj";
import "ol/ol.css";

const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY;

export function useMap(targetRef) {
   const mapInstance = useRef(null);

   useEffect(() => {
      if (!targetRef.current || mapInstance.current) return;

      const baseLayer = new TileLayer({
         source: new XYZ({
            url: `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY}/Base/{z}/{y}/{x}.png`,
            crossOrigin: "anonymous",
         }),
         zIndex: 0,
      });
      baseLayer.set("name", "base");

      mapInstance.current = new Map({
         target: targetRef.current,
         layers: [baseLayer],
         view: new View({
            center: fromLonLat([126.978, 37.5665]),
            zoom: 14,
            minZoom: 6,
            maxZoom: 19,
         }),
      });

      // 사이드바 등 레이아웃 변경 후 지도 크기 재계산
      setTimeout(() => {
         mapInstance.current?.updateSize();
      }, 300);

      // ResizeObserver로 크기 변화 감지 → updateSize 자동 호출
      const ro = new ResizeObserver(() => {
         mapInstance.current?.updateSize();
      });
      ro.observe(targetRef.current);

      return () => {
         ro.disconnect();
         if (mapInstance.current) {
            mapInstance.current.setTarget(null);
            mapInstance.current = null;
         }
      };
   }, [targetRef]);

   return mapInstance;
}
