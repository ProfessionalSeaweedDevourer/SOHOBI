// hooks/map/useMapZoom.js
// OL 뷰 줌 레벨 추적 + +/- 버튼 사이 숫자 배지 렌더링

import { useState, useEffect } from "react";

export function useMapZoom(mapInstance, mapRef, mapReady) {
  const [currentZoom, setCurrentZoom] = useState(16);

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

  return currentZoom;
}
