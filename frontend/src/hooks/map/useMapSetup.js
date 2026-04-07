// hooks/map/useMapSetup.js
// 줌 추적, 지적도 초기화, 랜드마크/학교 로드 (지도 준비 후 1회)
import { useRef, useEffect } from "react";

export function useMapSetup({
   mapInstance,
   mapRef,
   mapReady,
   wmsLayerRef,
   loadLandmarks,
   loadSchools,
   ensureDongBoundaryLayer,
   setCurrentZoom,
   setLandmarkLoaded,
   setSchoolLoaded,
}) {
   const landmarkInitRef = useRef(false);

   // 줌 레벨 추적 + OL +/- 버튼 사이에 숫자 표시
   useEffect(() => {
      const map = mapInstance.current;
      if (!map) return;
      const updateZoom = () => {
         const z = Math.round(map.getView().getZoom() || 16);
         setCurrentZoom(z);
         const zoomEl = mapRef.current?.querySelector(".ol-zoom");
         if (zoomEl) {
            let badge = zoomEl.querySelector(".zoom-level-badge");
            if (!badge) {
               badge = document.createElement("div");
               badge.className = "zoom-level-badge";
               badge.style.cssText =
                  "text-align:center;font-size:11px;font-weight:700;color:#333;padding:2px 0;background:#fff;border-left:2px solid #ddd;border-right:2px solid #ddd;";
               const btns = zoomEl.querySelectorAll("button");
               if (btns.length >= 2) zoomEl.insertBefore(badge, btns[1]);
            }
            badge.textContent = z;
         }
      };
      map.getView().on("change:resolution", updateZoom);
      updateZoom();
      return () => map.getView().un("change:resolution", updateZoom);
   }, [mapReady]); // eslint-disable-line

   // 랜드마크/학교 초기 로드 + 지적도 ON + 행정동 경계 로드
   useEffect(() => {
      if (!mapReady || !mapInstance.current || landmarkInitRef.current) return;
      landmarkInitRef.current = true;
      loadLandmarks().then(() => setLandmarkLoaded(true));
      loadSchools().then(() => setSchoolLoaded(true));
      ensureDongBoundaryLayer();

      const map = mapInstance.current;
      const vKey = import.meta.env.VITE_VWORLD_API_KEY;
      if (
         !map
            .getLayers()
            .getArray()
            .some((l) => l.get("name") === "cadastral")
      ) {
         Promise.all([
            import("ol/layer/Tile"),
            import("ol/source/TileWMS"),
         ]).then(([{ default: TileLayer }, { default: TileWMS }]) => {
            const layer = new TileLayer({
               source: new TileWMS({
                  url: `/wms/req/wms?KEY=${vKey}&DOMAIN=${import.meta.env.VITE_VWORLD_DOMAIN || "localhost"}`,
                  params: {
                     SERVICE: "WMS",
                     VERSION: "1.3.0",
                     REQUEST: "GetMap",
                     LAYERS: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
                     STYLES: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
                     FORMAT: "image/png",
                     TRANSPARENT: "TRUE",
                     CRS: "EPSG:3857",
                  },
                  crossOrigin: "anonymous",
                  transition: 0,
               }),
               opacity: 0.7,
               zIndex: 50,
               minZoom: 17,
            });
            layer.set("name", "cadastral");
            map.addLayer(layer);
            wmsLayerRef.current = layer;
         });
      }
   }, [mapReady]); // eslint-disable-line
}
