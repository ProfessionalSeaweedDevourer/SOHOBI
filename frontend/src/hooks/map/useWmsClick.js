// frontend/src/hooks/map/useWmsClick.js

// ── WMS 레이어 타입별 메타 정보 ────────────────────────────────
export const LAYER_META = {
   cadastral: { icon: "📋", label: "지적도", color: "#2196F3", bg: "#E3F2FD" },
   tourist_info: {
      icon: "ℹ️",
      label: "관광안내소",
      color: "#FF9800",
      bg: "#FFF3E0",
   },
   tourist_spot: {
      icon: "🏖️",
      label: "관광지",
      color: "#9C27B0",
      bg: "#F3E5F5",
   },
   market: { icon: "🏪", label: "전통시장", color: "#E53935", bg: "#FFEBEE" },
};

// ── WMS GetFeatureInfo 응답 → 공통 팝업 구조 파싱 ──────────────
export function parseWmsProps(p, layerType) {
   if (layerType === "cadastral") {
      return {
         pnu: p.pnu || p.PNU || p.필지번호 || p.jibun_cd || "",
         addr: p.addr || p.uname || "",
         // 본번-부번 순서 관례 적용
         jibun: p.jibun || (p.bonbun ? `${p.bonbun}-${p.bubun}` : ""),
         sido: p.ctp_nm || p.sido_name || "",
         sigg: p.sig_nm || p.sigg_name || "",
         dong: p.emd_nm || "",
         name: p.uname || p.addr || p.sig_nm || "정보 없음",
         remark: p.remark || "",
         tel: "",
         hours: "",
         jiga: p.jiga || p.pblntfPclnd || "",
         gosi_year: p.gosi_year || p.stdrYear || "",
         gosi_month: p.gosi_month || "",
      };
   }
   // 관광/시장 파싱 로직 (생략 - 기존 유지)
   return { pnu: "", addr: "", jibun: "", name: "정보 없음" };
}

const CADASTRAL_MIN_ZOOM = 17;
export const CADASTRAL_QUERY_LAYER = "lp_pa_cbnd_bubun";
export const CADASTRAL_LAYERS = `${CADASTRAL_QUERY_LAYER},lp_pa_cbnd_bonbun`;

// ── WMS 레이어 클릭 처리 ────────────────────────────────────────
export async function handleWmsClick(
   map,
   coordinate,
   { skipZoomGuard = false } = {},
) {
   const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY;
   const DOMAIN = "sohobi.net";

   // [최적화] 레이어 우선순위 명시 (지적도가 다른 레이어에 가려 클릭 안되는 현상 방지)
   const LAYER_ORDER = ["cadastral", "tourist_info", "tourist_spot", "market"];
   const allLayers = map.getLayers().getArray();
   const wmsLayers = LAYER_ORDER.map((name) =>
      allLayers.find((l) => l.get("name") === name),
   ).filter(Boolean);

   for (const wmsLayer of wmsLayers) {
      if (!wmsLayer.getVisible()) continue;
      const layerName = wmsLayer.get("name");

      // 지적도 줌 제한 가드
      if (!skipZoomGuard && layerName === "cadastral") {
         if ((map.getView().getZoom() ?? 0) < CADASTRAL_MIN_ZOOM) continue;
      }

      const source = wmsLayer.getSource();
      const extraParams = {
         INFO_FORMAT: "application/json",
         FEATURE_COUNT: 1,
         // 지적도의 경우 쿼리 레이어 명시 (속도 향상)
         ...(layerName === "cadastral" && {
            QUERY_LAYERS: CADASTRAL_QUERY_LAYER,
         }),
      };

      const url = source.getFeatureInfoUrl(
         coordinate,
         map.getView().getResolution(),
         "EPSG:3857",
         extraParams,
      );

      if (!url) continue;

      try {
         // [핵심 수정] 백엔드 프록시를 우회하여 브이월드 직접 호출 (CORS/인증 해결)
         const urlObj = new URL(url);
         const directUrl = `https://api.vworld.kr/req/wms${urlObj.search}&DOMAIN=${DOMAIN}&KEY=${VWORLD_KEY}`;

         const res = await fetch(directUrl);
         const text = await res.text();

         let feat = null;
         try {
            feat = JSON.parse(text).features?.[0];
         } catch {
            /* ignore */
         }

         if (!feat) continue;

         const parsed = parseWmsProps(feat.properties, layerName);

         // 지적도 공시지가 처리
         let landValue = null;
         if (layerName === "cadastral" && (parsed.jiga || parsed.pblntfPclnd)) {
            const rawJiga = parsed.jiga || parsed.pblntfPclnd;
            const price = parseInt(String(rawJiga).replace(/,/g, ""));
            const manwon = Math.round(price / 10000);
            landValue = [
               {
                  year: parsed.gosi_year || "2024",
                  month: parsed.gosi_month || "",
                  price,
                  price_str: `${manwon.toLocaleString()}만원/㎡`,
                  label: `${parsed.gosi_year || "2024"}년 기준`,
               },
            ];
         }

         return {
            parsed: { ...parsed, type: layerName },
            layerType: layerName,
            landValue,
         };
      } catch (err) {
         console.error("[WMS 직접 호출 오류]", err);
      }
   }
   return null;
}
