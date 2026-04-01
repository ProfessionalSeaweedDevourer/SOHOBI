// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\hooks\useWmsClick.js
// 공식 프론트 위치: frontend\src\hooks\map\useWmsClick.js

// WMS 레이어 클릭 → GetFeatureInfo → wmsPopup 상태 설정

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
         pnu: p.pnu || "",
         addr: p.addr || p.uname || "",
         jibun: p.jibun || (p.bubun ? `${p.bubun}-${p.bonbun}` : ""),
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
   if (layerType === "tourist_info") {
      return {
         pnu: "",
         jibun: "",
         addr: p.new_adr || p.jibun_adr || "",
         sido: p.sido_nam || "",
         sigg: p.sigg_nam || "",
         dong: "",
         name: p.tur_nam || "관광안내소",
         remark: p.des_inf || p.add_inf || "",
         tel: p.inf_tel || "",
         hours:
            p.wws_tme && p.wwe_tme
               ? `평일 ${p.wws_tme.slice(0, 5)}~${p.wwe_tme.slice(0, 5)}`
               : "",
      };
   }
   if (layerType === "tourist_spot") {
      return {
         pnu: "",
         jibun: "",
         addr: p.new_adr || p.adr || p.jibun_adr || "",
         sido: p.sido_nam || p.ctpv_nm || "",
         sigg: p.sigg_nam || p.sig_nm || "",
         dong: "",
         name: p.tur_nam || p.mus_nam || p.fac_nam || p.nm || "관광지",
         remark: p.des_inf || p.fac_inf || "",
         tel: p.mng_tel || p.tel || "",
         hours:
            p.wds_tme && p.wde_tme
               ? `평일 ${p.wds_tme.slice(0, 5)}~${p.wde_tme.slice(0, 5)}`
               : "",
      };
   }
   if (layerType === "market") {
      return {
         pnu: "",
         jibun: "",
         addr: p.new_adr || p.jibun_adr || p.adr || "",
         sido: p.sido_nam || p.ctpv_nm || "",
         sigg: p.sigg_nam || p.sig_nm || "",
         dong: "",
         name: p.name || p.nm || "전통시장",
         remark: p.mkt_type || "",
         tel: p.inf_tel || p.tel || "",
         hours: "",
      };
   }
   return {
      pnu: "",
      addr: "",
      jibun: "",
      sido: "",
      sigg: "",
      dong: "",
      name: "정보 없음",
      remark: "",
      tel: "",
      hours: "",
   };
}

/**
 * WMS 레이어 클릭 처리
 * @returns {Promise<{parsed, layerType, landValue}|null>}
 */

// ── WMS 레이어 클릭 처리 ────────────────────────────────────────
export async function handleWmsClick(map, coordinate) {
   const wmsLayers = map
      .getLayers()
      .getArray()
      .filter((l) =>
         ["cadastral", "tourist_info", "tourist_spot", "market"].includes(
            l.get("name"),
         ),
      );

   for (const wmsLayer of wmsLayers) {
      if (!wmsLayer.getVisible()) continue;
      const source = wmsLayer.getSource();
      const url = source.getFeatureInfoUrl(
         coordinate,
         map.getView().getResolution(),
         "EPSG:3857",
         { INFO_FORMAT: "application/json", FEATURE_COUNT: 1 },
      );
      if (!url) continue;
      try {
         const urlObj = new URL(url, window.location.origin);
         urlObj.searchParams.set("REQUEST", "GetFeatureInfo");
         const res = await fetch(urlObj.pathname + urlObj.search);
         const text = await res.text();
         let feat = null;
         try {
            feat = JSON.parse(text).features?.[0];
         } catch {
            /* ignore */
         }
         if (!feat) continue;

         const layerType = wmsLayer.get("name");
         const parsed = parseWmsProps(feat.properties, layerType);

         // 지적도 공시지가 처리
         let landValue = null;
         if (layerType === "cadastral" && parsed.jiga && parsed.gosi_year) {
            const price = parseInt(String(parsed.jiga).replace(/,/g, ""));
            const manwon = Math.round(price / 10000);
            landValue = [
               {
                  year: parsed.gosi_year,
                  month: parsed.gosi_month || "",
                  price,
                  price_str: `${manwon.toLocaleString()}만원/㎡`,
                  label: `${parsed.gosi_year}년${parsed.gosi_month ? ` ${parsed.gosi_month}월` : ""} 기준`,
               },
            ];
         }
         return {
            parsed: { ...parsed, type: layerType },
            layerType,
            landValue,
         };
      } catch (err) {
         console.error("[WMS 오류]", err);
      }
   }
   return null;
}
