import { useEffect, useRef, useState } from "react";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import XYZ from "ol/source/XYZ";
import { fromLonLat } from "ol/proj";
import "ol/ol.css";

export function useMap(targetRef) {
  const mapInstance = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!targetRef.current || mapInstance.current) return;

    const initMap = (center) => {
      const apiKey = import.meta.env.VITE_VWORLD_API_KEY;

      // VWorld 기본 지도 (Base 타일)
      const baseLayer = new TileLayer({
        source: new XYZ({
          url: `https://api.vworld.kr/req/wmts/1.0.0/${apiKey}/Base/{z}/{y}/{x}.png`,
          crossOrigin: "anonymous",
        }),
      });
      baseLayer.set("name", "base");

      mapInstance.current = new Map({
        target: targetRef.current,
        layers: [baseLayer],
        view: new View({
          center: center,
          zoom: 17,
          minZoom: 5,
          maxZoom: 19,
        }),
      });

      // 지도 준비 완료 알림
      setTimeout(() => setMapReady(true), 100);
    };

    // 서울시청 (서울 중심부) — 서비스 스코프가 서울 지역이므로 고정 좌표 사용
    initMap(fromLonLat([126.978, 37.5665]));

    return () => {
      if (mapInstance.current) {
        mapInstance.current.setTarget(null);
        mapInstance.current = null;
      }
    };
  }, [targetRef]);

  return { mapInstance, mapReady };
}
