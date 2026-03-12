import { useRef, useState, useCallback, useEffect } from "react";
import { useMap } from "../hooks/useMap";
import { toLonLat, fromLonLat } from "ol/proj";
import { circular } from "ol/geom/Polygon";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import TileLayer from "ol/layer/Tile";
import TileWMS from "ol/source/TileWMS";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import {
   Style,
   Circle as CircleStyle,
   Fill,
   Stroke,
   Text as OlText,
} from "ol/style";
import Layerpanel from "./Layerpanel";
import CategoryPanel from "./CategoryPanel";
import { CATEGORIES } from "../constants/categories";
import "./MapView.css";

const FASTAPI_URL = "http://localhost:8681";
const REALESTATE_URL = "http://localhost:8682";
const KAKAO_REST_KEY = import.meta.env.VITE_KAKAO_API_KEY;
const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY;

// ── WMS 레이어 타입별 메타 (팝업 아이콘/색상/제목) ────────────────
const LAYER_META = {
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

// 레이어 타입별 WMS 응답 필드 → 공통 팝업 구조로 파싱
function parseWmsProps(p, layerType) {
   const isCadastral = layerType === "cadastral";
   if (isCadastral) {
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
         // ── 공시지가 (WMS GetFeatureInfo에 이미 포함) ──
         jiga: p.jiga || p.pblntfPclnd || "",
         gosi_year: p.gosi_year || p.stdrYear || "",
         gosi_month: p.gosi_month || "",
      };
   }
   // 관광안내소
   if (layerType === "tourist_info") {
      return {
         pnu: "",
         addr: p.new_adr || p.jibun_adr || "",
         jibun: "",
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
   // 관광지 (lt_c_uo601, lt_p_dgmuseumart)
   if (layerType === "tourist_spot") {
      return {
         pnu: "",
         addr: p.new_adr || p.adr || p.jibun_adr || "",
         jibun: "",
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
   // 전통시장 (lt_p_tradsijang)
   if (layerType === "market") {
      return {
         pnu: "",
         addr: p.new_adr || p.jibun_adr || p.adr || "",
         jibun: "",
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

// ── 업종 색상 ────────────────────────────────────────────────────
const CAT_COLORS = {
   음식: { color: "#FF6B6B", bg: "#FFF0F0" },
   소매: { color: "#FF9800", bg: "#FFF8F0" },
   생활서비스: { color: "#4ecdc4", bg: "#F0FAFA" },
   부동산: { color: "#2196F3", bg: "#F0F4FF" },
   숙박: { color: "#9C27B0", bg: "#F8F0FF" },
   교육: { color: "#FFD700", bg: "#FFFDF0" },
   의료: { color: "#E03131", bg: "#FFF0F0" },
   스포츠: { color: "#2F9E44", bg: "#F0FFF4" },
   "과학·기술": { color: "#1971C2", bg: "#F0F4FF" },
   "수리·개인": { color: "#7B4F2E", bg: "#FFF8F0" },
};

function getCatStyle(category) {
   if (!category) return { color: "#555", bg: "#F5F5F5" };
   for (const [key, val] of Object.entries(CAT_COLORS)) {
      if (category.includes(key)) return val;
   }
   return { color: "#555", bg: "#F5F5F5" };
}

function makeMarkerStyle(category, selected = false) {
   const { color } = getCatStyle(category);
   return new Style({
      image: new CircleStyle({
         radius: selected ? 10 : 7,
         fill: new Fill({ color }),
         stroke: new Stroke({ color: "#fff", width: selected ? 3 : 2 }),
      }),
   });
}

// 카카오 키워드 검색으로 상세정보 조회
async function fetchKakaoDetail(name, address) {
   const query = address ? `${address} ${name}` : name;
   try {
      const res = await fetch(
         `/kakao/v2/local/search/keyword.json?query=${encodeURIComponent(query)}&size=1`,
         { headers: { Authorization: `KakaoAK ${KAKAO_REST_KEY}` } },
      );
      const data = await res.json();
      return data.documents?.[0] || null;
   } catch {
      return null;
   }
}

// ── 줌 레벨별 반경/건수 계산 ────────────────────────────────────
function getRadiusAndLimit(zoom) {
   if (zoom >= 18) return { radius: 100, limit: 2000 };
   if (zoom >= 17) return { radius: 200, limit: 1500 };
   if (zoom >= 16) return { radius: 300, limit: 1000 };
   if (zoom >= 15) return { radius: 400, limit: 700 };
   if (zoom >= 14) return { radius: 500, limit: 500 };
   if (zoom >= 13) return { radius: 800, limit: 400 };
   return { radius: 1200, limit: 300 };
}

// ── 동 레이어 헬퍼 ────────────────────────────────────────────────
const DONG_MODE_CONFIG = {
   realestate: { label: "🏢 실거래가", color: "#2563EB" },
   sales: { label: "📊 매출", color: "#059669" },
};

function formatAmt(v) {
   if (!v || v === 0) return "-";
   if (v >= 1e8) return `${(v / 1e8).toFixed(1)}억`;
   if (v >= 1e4) return `${Math.round(v / 1e4)}만`;
   return `${v}`;
}

// ── 컴포넌트 ─────────────────────────────────────────────────────
export default function MapView() {
   const mapRef = useRef(null);
   const mapInstance = useMap(mapRef);
   const markerLayerRef = useRef(null);
   const circleLayerRef = useRef(null);
   const clickModeRef = useRef(true);

   const [coords, setCoords] = useState({ lat: "37.5665", lng: "126.9780" });
   const [popup, setPopup] = useState(null);
   const [kakaoDetail, setKakaoDetail] = useState(null);
   const [loadingDetail, setLoadingDetail] = useState(false);
   const [nearbyCount, setNearbyCount] = useState(null);
   const [loading, setLoading] = useState(false);
   const wmsLayerRef = useRef(null);
   const [wmsPopup, setWmsPopup] = useState(null);
   const [landValue, setLandValue] = useState(null); // 공시지가 (지적도 전용)
   const [showPanel, setShowPanel] = useState(false);
   const [clickMode, setClickMode] = useState(true);

   // ── 동 레이어 모드 ──────────────────────────────────────────────
   const [dongMode, setDongMode] = useState("none"); // "none"|"realestate"|"sales"
   const currentGuNmRef = useRef(""); // 현재 지도 구명 ref (클로저 문제 방지)
   const dongLayerRef = useRef(null); // VectorLayer (폴리곤)
   const dongModeRef = useRef("none");
   const [dongLoading, setDongLoading] = useState(false);
   const [dongPanel, setDongPanel] = useState(null); // 클릭 핸들러에서 ref로 읽기용
   useEffect(() => {
      dongModeRef.current = dongMode;
   }, [dongMode]);

   // 카테고리 필터 상태
   const allCatKeys = new Set(CATEGORIES.map((c) => c.key));
   const [visibleCats, setVisibleCats] = useState(allCatKeys);
   const allStoresRef = useRef([]); // useState 대신 ref로 관리 → 의존성 문제 없음
   const [catCounts, setCatCounts] = useState({});

   useEffect(() => {
      clickModeRef.current = clickMode;
   }, [clickMode]);

   // ── 반경 원 그리기 ──
   const drawCircle = useCallback(
      (lng, lat, radius) => {
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
      },
      [mapInstance],
   );

   // ── 마커 그리기 (visibleCats 필터 적용) ──
   const drawMarkers = useCallback(
      (stores, visible = visibleCats) => {
         const map = mapInstance.current;
         if (!map) return;
         if (markerLayerRef.current) map.removeLayer(markerLayerRef.current);

         const features = stores
            .filter((s) => s.경도 && s.위도)
            .filter((s) => {
               const key = CATEGORIES.find((c) =>
                  s.상권업종대분류명?.includes(c.key),
               )?.key;
               return key ? visible.has(key) : true;
            })
            .map((store) => {
               const feature = new Feature({
                  geometry: new Point(
                     fromLonLat([
                        parseFloat(store.경도),
                        parseFloat(store.위도),
                     ]),
                  ),
               });
               feature.setProperties({ store });
               feature.setStyle(makeMarkerStyle(store.상권업종대분류명));
               return feature;
            });

         const layer = new VectorLayer({
            source: new VectorSource({ features }),
            zIndex: 100,
         });
         map.addLayer(layer);
         markerLayerRef.current = layer;
      },
      [mapInstance, visibleCats],
   );

   // visibleCats 바뀌면 마커 재렌더링
   useEffect(() => {
      if (allStoresRef.current.length > 0)
         drawMarkers(allStoresRef.current, visibleCats);
   }, [visibleCats, drawMarkers]);

   // ── 카테고리 핸들러 ──
   const handleToggleCat = (key) => {
      setVisibleCats((prev) => {
         const next = new Set(prev);
         next.has(key) ? next.delete(key) : next.add(key);
         return next;
      });
   };
   const handleShowAll = () =>
      setVisibleCats(new Set(CATEGORIES.map((c) => c.key)));
   const handleHideAll = () => setVisibleCats(new Set());

   // ── 지도 이벤트 등록 ──
   useEffect(() => {
      const map = mapInstance.current;
      if (!map) return;

      // 호버 디바운스 타이머
      let hoverTimer = null;

      const moveHandler = (e) => {
         const [lng, lat] = toLonLat(e.coordinate);
         setCoords({ lat: lat.toFixed(6), lng: lng.toFixed(6) });

         // 행정동 모드일 때 호버 하이라이트
         if (dongModeRef.current === "none") return;
         if (hoverTimer) clearTimeout(hoverTimer);
         hoverTimer = setTimeout(async () => {
            const dongNm = await getDongNameAtCoord(e.coordinate);
            if (!dongNm || dongNm === dongHoverNameRef.current) return;
            dongHoverNameRef.current = dongNm;
            // 커서 변경으로 클릭 가능 표시
            map.getTargetElement().style.cursor = "pointer";
            // 호버 라벨 (별도 오버레이 대신 콘솔 + 커서)
            console.log(`[동 호버] ${dongNm}`);
         }, 120);
      };

      const clickHandler = async (e) => {
         // ── 행정동 WMS 클릭 (GetFeatureInfo로 동명 파악 → 패널) ──
         if (dongModeRef.current !== "none") {
            const dongNm = await getDongNameAtCoord(e.coordinate);
            if (dongNm) {
               console.log(
                  `[동 클릭] ${dongNm} / 모드: ${dongModeRef.current}`,
               );
               loadDongPanel(dongNm, dongModeRef.current);
               return;
            }
         }

         // ── WMS 레이어 클릭 감지 (GetFeatureInfo) ──
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
            const viewResolution = map.getView().getResolution();
            const url = source.getFeatureInfoUrl(
               e.coordinate,
               viewResolution,
               "EPSG:3857",
               { INFO_FORMAT: "application/json", FEATURE_COUNT: 1 },
            );
            if (url) {
               try {
                  // getFeatureInfoUrl → pathname이 이미 /wms/req/wms 형태
                  const urlObj = new URL(url, window.location.origin);
                  // REQUEST=GetMap → GetFeatureInfo 강제 교체
                  urlObj.searchParams.set("REQUEST", "GetFeatureInfo");
                  const fetchUrl = urlObj.pathname + urlObj.search;
                  console.log("[WMS GetFeatureInfo]", fetchUrl);
                  const res = await fetch(fetchUrl);
                  const text = await res.text();
                  console.log("[WMS 응답]", text);
                  let feat = null;
                  try {
                     const data = JSON.parse(text);
                     feat = data.features?.[0];
                  } catch {
                     /* JSON 파싱 실패 무시 */
                  }
                  if (feat) {
                     const p = feat.properties;
                     setPopup(null);
                     const layerType = wmsLayer.get("name");
                     const parsed = parseWmsProps(p, layerType);
                     setWmsPopup({ ...parsed, type: layerType });

                     // 지적도 클릭 → 공시지가 WMS 필드 직접 추출 (별도 API 호출 불필요)
                     if (layerType === "cadastral") {
                        if (parsed.sigg) currentGuNmRef.current = parsed.sigg;
                        setLandValue(null);
                        if (parsed.jiga && parsed.gosi_year) {
                           const price = parseInt(
                              String(parsed.jiga).replace(/,/g, ""),
                           );
                           const manwon = Math.round(price / 10000);
                           const label = `${parsed.gosi_year}년${parsed.gosi_month ? ` ${parsed.gosi_month}월` : ""} 기준`;
                           setLandValue([
                              {
                                 year: parsed.gosi_year,
                                 month: parsed.gosi_month || "",
                                 price,
                                 price_str: `${manwon.toLocaleString()}만원/㎡`,
                                 label,
                              },
                           ]);
                        }
                     }
                     return;
                  }
               } catch (err) {
                  console.error("[WMS 오류]", err);
               }
            }
         }
         setWmsPopup(null);
         // 마커 클릭 확인
         const feature = map.forEachFeatureAtPixel(e.pixel, (f) => f);
         if (feature?.get("store")) {
            const store = feature.get("store");
            setPopup(store);
            setWmsPopup(null);
            setKakaoDetail(null);
            setLoadingDetail(true);
            const detail = await fetchKakaoDetail(
               store.상호명,
               store.도로명주소,
            );
            setKakaoDetail(detail);
            setLoadingDetail(false);
            return;
         }

         if (!clickModeRef.current) return;

         // 빈 지도 클릭 → FastAPI DB 조회
         const [lng, lat] = toLonLat(e.coordinate);
         const zoom = map.getView().getZoom() ?? 14;
         const { radius, limit } = getRadiusAndLimit(zoom);
         setLoading(true);
         setPopup(null);
         setKakaoDetail(null);

         try {
            const res = await fetch(
               `${FASTAPI_URL}/map/nearby?lat=${lat}&lng=${lng}&radius=${radius}&limit=${limit}`,
            );
            const data = await res.json();
            const stores = data.stores || [];
            setNearbyCount(data.count);
            allStoresRef.current = stores;

            // 카테고리별 건수 계산
            const counts = {};
            stores.forEach((s) => {
               const key =
                  CATEGORIES.find((c) => s.상권업종대분류명?.includes(c.key))
                     ?.key || "기타";
               counts[key] = (counts[key] || 0) + 1;
            });
            setCatCounts(counts);
            drawCircle(lng, lat, radius);
            drawMarkers(stores, visibleCats);
         } catch (err) {
            console.error("DB 조회 오류:", err);
         } finally {
            setLoading(false);
         }
      };

      map.on("pointermove", moveHandler);
      map.on("click", clickHandler);
      return () => {
         map.un("pointermove", moveHandler);
         map.un("click", clickHandler);
      };
   }, [mapInstance.current, drawMarkers]); // eslint-disable-line

   const clearAll = () => {
      if (markerLayerRef.current) {
         mapInstance.current?.removeLayer(markerLayerRef.current);
         markerLayerRef.current = null;
      }
      setPopup(null);
      setKakaoDetail(null);
      setNearbyCount(null);
      if (circleLayerRef.current) {
         mapInstance.current?.removeLayer(circleLayerRef.current);
         circleLayerRef.current = null;
      }
      allStoresRef.current = [];
      setCatCounts({});
      setLandValue(null);
      setWmsPopup(null);
      // 동 뱃지 레이어만 제거 (경계는 유지)
      if (dongLayerRef.current) {
         mapInstance.current?.removeLayer(dongLayerRef.current);
         dongLayerRef.current = null;
      }
      setDongPanel(null);
   };

   // ── 행정동 경계 WMS + 호버/클릭 인터랙션 ────────────────────
   const dongBoundaryLayerRef = useRef(null);
   const dongHoverNameRef = useRef(""); // 현재 호버 중인 동명

   const ensureDongBoundaryLayer = useCallback(() => {
      const map = mapInstance.current;
      if (!map || dongBoundaryLayerRef.current) return;
      const layer = new TileLayer({
         source: new TileWMS({
            url: `/wms/req/wms?KEY=${VWORLD_KEY}&DOMAIN=localhost`,
            params: {
               SERVICE: "WMS",
               VERSION: "1.3.0",
               REQUEST: "GetMap",
               LAYERS: "lt_c_ademd_info",
               FORMAT: "image/png",
               TRANSPARENT: "TRUE",
               CRS: "EPSG:3857",
            },
            crossOrigin: "anonymous",
            transition: 0,
         }),
         opacity: 0.7,
         zIndex: 48,
      });
      layer.set("name", "dong_boundary_bg");
      map.addLayer(layer);
      dongBoundaryLayerRef.current = layer;
      console.log("[동 경계] WMS 레이어 추가 (lt_c_ademd_info)");
   }, [mapInstance]);

   // ── 행정동 WMS GetFeatureInfo 호출 → 동명 반환 ────────────────
   const getDongNameAtCoord = useCallback(
      async (coordinate) => {
         const map = mapInstance.current;
         if (!map || !dongBoundaryLayerRef.current) return null;
         try {
            const source = dongBoundaryLayerRef.current.getSource();
            const res = map.getView().getResolution();
            const url = source.getFeatureInfoUrl(coordinate, res, "EPSG:3857", {
               INFO_FORMAT: "application/json",
               FEATURE_COUNT: 1,
            });
            if (!url) return null;
            const r = await fetch(url);
            const txt = await r.text();
            if (!txt || txt.startsWith("<")) return null;
            const data = JSON.parse(txt);
            const props = data.features?.[0]?.properties;
            // lt_c_ademd_info 필드: emd_kor_nm(행정동명), sig_kor_nm(구명)
            const dongNm =
               props?.emd_kor_nm ||
               props?.adm_nm ||
               props?.emd_nm ||
               props?.name ||
               null;
            const guNm =
               props?.sig_kor_nm || props?.sig_nm || props?.gu_nm || "";
            if (guNm) currentGuNmRef.current = guNm;
            return dongNm;
         } catch {
            return null;
         }
      },
      [mapInstance],
   );

   // ── 동 데이터 패널 로드 (클릭 시) ──────────────────────────────
   const loadDongPanel = useCallback(async (dongNm, mode) => {
      if (!dongNm || mode === "none") return;
      const guNm = currentGuNmRef.current;
      setDongLoading(true);
      setDongPanel(null);
      try {
         if (mode === "sales") {
            const r = await fetch(
               `${REALESTATE_URL}/realestate/sangkwon?dong=${encodeURIComponent(dongNm)}&gu=${encodeURIComponent(guNm)}`,
            );
            const j = await r.json();
            if (j.data) setDongPanel({ mode, dongNm, guNm, apiData: j.data });
         } else if (mode === "realestate") {
            const r = await fetch(
               `${REALESTATE_URL}/realestate/analysis?sigungu=${encodeURIComponent(guNm)}&dong=${encodeURIComponent(dongNm)}`,
            );
            const j = await r.json();
            if (j) setDongPanel({ mode, dongNm, guNm, apiData: j });
         }
      } catch (err) {
         console.error("[동 패널 오류]", err);
      } finally {
         setDongLoading(false);
      }
   }, []);

   // ── drawDongLayer: 뱃지 없이 경계만 표시 ──────────────────────
   const drawDongLayer = useCallback(
      async (mode) => {
         if (mode === "none") {
            setDongPanel(null);
            return;
         }
         ensureDongBoundaryLayer();
      },
      [mapInstance, ensureDongBoundaryLayer],
   );

   // 모드 전환 핸들러
   const handleDongMode = (mode) => {
      const next = dongMode === mode ? "none" : mode;
      setDongMode(next);
      drawDongLayer(next);
   };

   // ── 맵 마운트 시 자동으로 구명 파악 ────────────────────────────
   useEffect(() => {
      const map = mapInstance.current;
      if (!map) return;
      // 초기 중심 좌표로 구명 파악
      const init = async () => {
         try {
            const [cLng, cLat] = toLonLat(map.getView().getCenter());
            const r = await fetch(
               `/kakao/v2/local/geo/coord2regioncode.json?x=${cLng}&y=${cLat}`,
               { headers: { Authorization: `KakaoAK ${KAKAO_REST_KEY}` } },
            );
            const rj = await r.json();
            const region = rj.documents?.find((d) => d.region_type === "H");
            const gu = region?.region_2depth_name || "";
            if (gu) currentGuNmRef.current = gu;
         } catch {
            /* ignore */
         }
      };
      init();
   }, [mapInstance.current]); // eslint-disable-line

   const cat = popup ? getCatStyle(popup.상권업종대분류명) : null;

   return (
      <div
         style={{
            position: "relative",
            width: "100%",
            height: "100vh",
            overflow: "hidden",
            display: "flex",
            fontFamily: "'Pretendard','Apple SD Gothic Neo',sans-serif",
         }}
      >
         {/* 왼쪽 카테고리 사이드바 */}
         <CategoryPanel
            visibleCats={visibleCats}
            onToggle={handleToggleCat}
            onShowAll={handleShowAll}
            onHideAll={handleHideAll}
            totalCount={nearbyCount}
            catCounts={catCounts}
         />

         <div ref={mapRef} style={{ flex: 1, height: "100%", minWidth: 0 }} />

         {/* 상단 컨트롤 바 */}
         <div
            style={{
               position: "absolute",
               top: 14,
               left: "50%",
               transform: "translateX(-50%)",
               zIndex: 200,
               display: "flex",
               alignItems: "center",
               gap: 8,
               background: "#fff",
               border: "1px solid #e5e7eb",
               borderRadius: 12,
               padding: "6px 10px",
               boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
            }}
         >
            <button
               style={{
                  border: "none",
                  borderRadius: 8,
                  padding: "5px 14px",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  transition: "all 0.18s",
                  background: clickMode ? "#2563EB" : "#e5e7eb",
                  color: clickMode ? "#fff" : "#555",
               }}
               onClick={() => setClickMode((v) => !v)}
            >
               {clickMode ? "📍 반경분석 ON" : "📍 반경분석 OFF"}
            </button>
            {nearbyCount !== null && (
               <span
                  style={{
                     background: "#eff6ff",
                     border: "1px solid #bfdbfe",
                     borderRadius: 8,
                     padding: "5px 12px",
                     fontSize: 12,
                     color: "#2563eb",
                     fontWeight: 600,
                  }}
               >
                  반경 500m · {nearbyCount}건
               </span>
            )}
            {loading && (
               <span
                  style={{
                     background: "#fff",
                     border: "1px solid #ddd",
                     borderRadius: 8,
                     padding: "5px 12px",
                     fontSize: 12,
                     color: "#999",
                  }}
               >
                  DB 조회 중...
               </span>
            )}
            {nearbyCount !== null && (
               <button
                  style={{
                     background: "#fff",
                     border: "1px solid #ddd",
                     borderRadius: 8,
                     padding: "5px 12px",
                     fontSize: 12,
                     color: "#666",
                     cursor: "pointer",
                  }}
                  onClick={clearAll}
               >
                  ✕ 초기화
               </button>
            )}
         </div>

         {/* 레이어 패널 */}
         <button
            style={{
               position: "absolute",
               top: 14,
               right: 14,
               zIndex: 200,
               background: "#fff",
               border: "1px solid #e5e7eb",
               borderRadius: 10,
               padding: "8px 12px",
               fontSize: 18,
               cursor: "pointer",
               boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            }}
            onClick={() => setShowPanel((p) => !p)}
         >
            🗂️
         </button>
         {showPanel && mapInstance.current && (
            <div
               style={{ position: "absolute", top: 58, right: 14, zIndex: 200 }}
            >
               <Layerpanel
                  map={mapInstance.current}
                  vworldKey={VWORLD_KEY}
                  wmsLayerRef={wmsLayerRef}
               />
            </div>
         )}

         {/* WMS 팝업 (지적도 / 관광안내소 / 관광지 / 전통시장) */}
         {wmsPopup &&
            (() => {
               const meta = LAYER_META[wmsPopup.type] || LAYER_META.cadastral;
               return (
                  <div
                     style={{
                        position: "absolute",
                        bottom: 50,
                        left: "50%",
                        transform: "translateX(-50%)",
                        zIndex: 300,
                        width: 320,
                        background: "#fff",
                        borderRadius: 16,
                        boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
                        overflow: "hidden",
                     }}
                  >
                     <div style={{ height: 4, background: meta.color }} />
                     <div style={{ padding: "12px 16px 16px" }}>
                        <div
                           style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              marginBottom: 8,
                           }}
                        >
                           <div
                              style={{
                                 borderRadius: 20,
                                 padding: "3px 10px",
                                 fontSize: 11,
                                 fontWeight: 700,
                                 background: meta.bg,
                                 color: meta.color,
                                 border: `1px solid ${meta.color}`,
                              }}
                           >
                              {meta.icon} {meta.label}
                           </div>
                           <button
                              style={{
                                 background: "transparent",
                                 border: "none",
                                 color: "#bbb",
                                 cursor: "pointer",
                                 fontSize: 16,
                              }}
                              onClick={() => setWmsPopup(null)}
                           >
                              ✕
                           </button>
                        </div>
                        {/* 지적도 */}
                        {wmsPopup.type === "cadastral" ? (
                           <>
                              <div
                                 style={{
                                    fontSize: 17,
                                    fontWeight: 700,
                                    color: "#111",
                                    marginBottom: 4,
                                 }}
                              >
                                 {wmsPopup.addr || "주소 없음"}
                              </div>
                              <div
                                 style={{
                                    height: 1,
                                    background: "#f0f0f0",
                                    margin: "10px 0",
                                 }}
                              />
                              <div
                                 style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 6,
                                 }}
                              >
                                 {wmsPopup.sido && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          🏙️
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          {wmsPopup.sido} {wmsPopup.sigg}{" "}
                                          {wmsPopup.dong}
                                       </span>
                                    </div>
                                 )}
                                 {wmsPopup.jibun && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          📋
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          지번: {wmsPopup.jibun}
                                       </span>
                                    </div>
                                 )}
                                 {wmsPopup.pnu && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          🔑
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          PNU: {wmsPopup.pnu}
                                       </span>
                                    </div>
                                 )}
                              </div>

                              {/* ── 공시지가 섹션 ── */}
                              <div
                                 style={{
                                    height: 1,
                                    background: "#f0f0f0",
                                    margin: "10px 0",
                                 }}
                              />
                              {landValue?.length > 0 ? (
                                 <div
                                    style={{
                                       background: "#f0fdf4",
                                       border: "1px solid #bbf7d0",
                                       borderRadius: 10,
                                       padding: "10px 12px",
                                    }}
                                 >
                                    <div
                                       style={{
                                          fontSize: 11,
                                          fontWeight: 700,
                                          color: "#166534",
                                          marginBottom: 6,
                                       }}
                                    >
                                       🏷️ 개별공시지가 ·{" "}
                                       {landValue[0].label ||
                                          `${landValue[0].year}년 기준`}
                                    </div>
                                    {landValue.slice(0, 3).map((lv, i) => (
                                       <div
                                          key={i}
                                          style={{
                                             display: "flex",
                                             justifyContent: "space-between",
                                             alignItems: "center",
                                             fontSize: 12,
                                             marginBottom: 3,
                                          }}
                                       >
                                          <span style={{ color: "#4b7c5e" }}>
                                             {lv.year}년
                                             {lv.month ? ` ${lv.month}월` : ""}
                                          </span>
                                          <b
                                             style={{
                                                color: "#14532d",
                                                fontSize: 14,
                                             }}
                                          >
                                             {lv.price_str}
                                          </b>
                                       </div>
                                    ))}
                                 </div>
                              ) : wmsPopup.pnu ? (
                                 <div
                                    style={{
                                       fontSize: 11,
                                       color: "#bbb",
                                       textAlign: "center",
                                    }}
                                 >
                                    공시지가 정보 없음
                                 </div>
                              ) : null}
                           </>
                        ) : (
                           <>
                              <div
                                 style={{
                                    fontSize: 17,
                                    fontWeight: 700,
                                    color: "#111",
                                    marginBottom: 4,
                                 }}
                              >
                                 {wmsPopup.name}
                              </div>
                              <div
                                 style={{
                                    height: 1,
                                    background: "#f0f0f0",
                                    margin: "10px 0",
                                 }}
                              />
                              <div
                                 style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 6,
                                 }}
                              >
                                 {wmsPopup.sido && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          🏙️
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          {wmsPopup.sido} {wmsPopup.sigg}
                                       </span>
                                    </div>
                                 )}
                                 {wmsPopup.addr && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          📍
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          {wmsPopup.addr}
                                       </span>
                                    </div>
                                 )}
                                 {wmsPopup.tel && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          📞
                                       </span>
                                       <a
                                          href={`tel:${wmsPopup.tel}`}
                                          style={{
                                             fontSize: 13,
                                             color: "#2563eb",
                                             textDecoration: "none",
                                          }}
                                       >
                                          {wmsPopup.tel}
                                       </a>
                                    </div>
                                 )}
                                 {wmsPopup.hours && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          🕐
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          {wmsPopup.hours}
                                       </span>
                                    </div>
                                 )}
                                 {wmsPopup.remark && (
                                    <div
                                       style={{
                                          display: "flex",
                                          alignItems: "flex-start",
                                          gap: 7,
                                       }}
                                    >
                                       <span
                                          style={{
                                             fontSize: 13,
                                             flexShrink: 0,
                                             marginTop: 1,
                                          }}
                                       >
                                          📝
                                       </span>
                                       <span
                                          style={{
                                             fontSize: 13,
                                             color: "#444",
                                             lineHeight: 1.4,
                                          }}
                                       >
                                          {wmsPopup.remark}
                                       </span>
                                    </div>
                                 )}
                              </div>
                           </>
                        )}
                     </div>
                  </div>
               );
            })()}

         {/* 상세 팝업 */}
         {popup && cat && (
            <div
               style={{
                  position: "absolute",
                  bottom: 50,
                  left: "50%",
                  transform: "translateX(-50%)",
                  zIndex: 300,
                  width: 320,
                  background: "#fff",
                  borderRadius: 16,
                  boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
                  overflow: "hidden",
               }}
            >
               <div style={{ height: 4, background: cat.color }} />
               <div style={{ padding: "12px 16px 16px" }}>
                  <div
                     style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 8,
                     }}
                  >
                     <div
                        style={{
                           borderRadius: 20,
                           padding: "3px 10px",
                           fontSize: 11,
                           fontWeight: 700,
                           background: cat.bg,
                           color: cat.color,
                           border: `1px solid ${cat.color}`,
                        }}
                     >
                        {popup.상권업종대분류명}
                     </div>
                     <button
                        style={{
                           background: "transparent",
                           border: "none",
                           color: "#bbb",
                           cursor: "pointer",
                           fontSize: 16,
                        }}
                        onClick={() => {
                           setPopup(null);
                           setKakaoDetail(null);
                        }}
                     >
                        ✕
                     </button>
                  </div>

                  <div
                     style={{
                        fontSize: 17,
                        fontWeight: 700,
                        color: "#111",
                        marginBottom: 4,
                     }}
                  >
                     {popup.상호명}
                  </div>
                  {popup.상권업종소분류명 && (
                     <div
                        style={{ fontSize: 12, color: "#888", marginBottom: 4 }}
                     >
                        {popup.상권업종중분류명} · {popup.상권업종소분류명}
                     </div>
                  )}

                  <div
                     style={{
                        height: 1,
                        background: "#f0f0f0",
                        margin: "10px 0",
                     }}
                  />

                  {/* DB 데이터 */}
                  <div
                     style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                     }}
                  >
                     {popup.도로명주소 && (
                        <div
                           style={{
                              display: "flex",
                              alignItems: "flex-start",
                              gap: 7,
                           }}
                        >
                           <span
                              style={{
                                 fontSize: 13,
                                 flexShrink: 0,
                                 marginTop: 1,
                              }}
                           >
                              📍
                           </span>
                           <span
                              style={{
                                 fontSize: 13,
                                 color: "#444",
                                 lineHeight: 1.4,
                              }}
                           >
                              {popup.도로명주소}
                              {popup.층정보 && ` ${popup.층정보}층`}
                              {popup.호정보 && ` ${popup.호정보}호`}
                           </span>
                        </div>
                     )}
                     <div
                        style={{
                           display: "flex",
                           alignItems: "flex-start",
                           gap: 7,
                        }}
                     >
                        <span
                           style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}
                        >
                           🏙️
                        </span>
                        <span
                           style={{
                              fontSize: 13,
                              color: "#444",
                              lineHeight: 1.4,
                           }}
                        >
                           {popup.시도명} {popup.시군구명} {popup.행정동명}
                        </span>
                     </div>
                  </div>

                  {/* 카카오 상세 */}
                  {loadingDetail && (
                     <div
                        style={{
                           marginTop: 10,
                           fontSize: 12,
                           color: "#999",
                           textAlign: "center",
                           padding: "8px 0",
                        }}
                     >
                        📱 카카오맵 상세정보 조회 중...
                     </div>
                  )}
                  {!loadingDetail && kakaoDetail && (
                     <>
                        <div
                           style={{
                              marginTop: 10,
                              padding: "10px 12px",
                              background: "#fffde7",
                              borderRadius: 10,
                              display: "flex",
                              flexDirection: "column",
                              gap: 6,
                           }}
                        >
                           <div
                              style={{
                                 fontSize: 11,
                                 fontWeight: 700,
                                 color: "#b8860b",
                                 marginBottom: 2,
                              }}
                           >
                              📱 카카오맵 추가정보
                           </div>
                           {kakaoDetail.phone && (
                              <div
                                 style={{
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 7,
                                 }}
                              >
                                 <span
                                    style={{
                                       fontSize: 13,
                                       flexShrink: 0,
                                       marginTop: 1,
                                    }}
                                 >
                                    📞
                                 </span>
                                 <a
                                    href={`tel:${kakaoDetail.phone}`}
                                    style={{
                                       fontSize: 13,
                                       color: "#2563eb",
                                       textDecoration: "none",
                                    }}
                                 >
                                    {kakaoDetail.phone}
                                 </a>
                              </div>
                           )}
                           {kakaoDetail.category_name && (
                              <div
                                 style={{
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 7,
                                 }}
                              >
                                 <span
                                    style={{
                                       fontSize: 13,
                                       flexShrink: 0,
                                       marginTop: 1,
                                    }}
                                 >
                                    🏷️
                                 </span>
                                 <span
                                    style={{
                                       fontSize: 13,
                                       color: "#444",
                                       lineHeight: 1.4,
                                    }}
                                 >
                                    {kakaoDetail.category_name}
                                 </span>
                              </div>
                           )}
                        </div>
                        <a
                           href={kakaoDetail.place_url}
                           target="_blank"
                           rel="noreferrer"
                           style={{
                              marginTop: 12,
                              display: "flex",
                              justifyContent: "center",
                              alignItems: "center",
                              background: "#fee500",
                              borderRadius: 10,
                              padding: "9px",
                              fontSize: 13,
                              fontWeight: 700,
                              color: "#111",
                              textDecoration: "none",
                           }}
                        >
                           카카오맵에서 보기 →
                        </a>
                     </>
                  )}
                  {!loadingDetail && !kakaoDetail && (
                     <div
                        style={{
                           marginTop: 10,
                           fontSize: 11,
                           color: "#bbb",
                           textAlign: "center",
                        }}
                     >
                        카카오맵 정보를 찾을 수 없습니다
                     </div>
                  )}
               </div>
            </div>
         )}

         {/* ── 동 레이어 모드 탭 (지도 왼쪽 하단) ── */}
         <div
            style={{
               position: "absolute",
               bottom: 50,
               left: 16,
               zIndex: 200,
               display: "flex",
               flexDirection: "column",
               gap: 6,
            }}
         >
            {currentGuNmRef.current && dongMode !== "none" && (
               <div
                  style={{
                     background: "rgba(255,255,255,0.95)",
                     borderRadius: 8,
                     padding: "4px 10px",
                     fontSize: 11,
                     color: "#555",
                     boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                     textAlign: "center",
                  }}
               >
                  📍 {currentGuNmRef.current}
               </div>
            )}
            {!currentGuNmRef.current && dongMode !== "none" && (
               <div
                  style={{
                     background: "#fffbeb",
                     border: "1px solid #fbbf24",
                     borderRadius: 8,
                     padding: "5px 10px",
                     fontSize: 11,
                     color: "#92400e",
                     boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                  }}
               >
                  ⚠️ 지적도를 먼저 클릭하세요
               </div>
            )}
            {dongLoading && (
               <div
                  style={{
                     background: "rgba(255,255,255,0.95)",
                     borderRadius: 8,
                     padding: "5px 12px",
                     fontSize: 11,
                     color: "#555",
                     boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                  }}
               >
                  ⏳ 동 데이터 로딩 중...
               </div>
            )}
            {[
               {
                  mode: "realestate",
                  label: "🏢 실거래가",
                  activeColor: "#2563EB",
               },
               { mode: "sales", label: "📊 매출", activeColor: "#059669" },
            ].map(({ mode, label, activeColor }) => {
               const isActive = dongMode === mode;
               return (
                  <button
                     key={mode}
                     onClick={() => handleDongMode(mode)}
                     style={{
                        border: `2px solid ${isActive ? activeColor : "#e5e7eb"}`,
                        borderRadius: 10,
                        padding: "7px 14px",
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                        background: isActive ? activeColor : "#fff",
                        color: isActive ? "#fff" : "#555",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                        transition: "all 0.18s",
                        whiteSpace: "nowrap",
                     }}
                  >
                     {label}
                     {isActive ? " ✓" : ""}
                  </button>
               );
            })}
         </div>

         {/* ── 동 클릭 → 오른쪽 슬라이드 패널 ── */}
         {dongPanel &&
            (() => {
               const d = dongPanel.apiData;
               const isRE = dongPanel.mode === "realestate";
               const panelColor = isRE ? "#2563EB" : "#059669";
               const panelBg = isRE ? "#eff6ff" : "#f0fdf4";

               return (
                  <div
                     style={{
                        position: "absolute",
                        top: 0,
                        right: 0,
                        width: 300,
                        height: "100%",
                        background: "#fff",
                        boxShadow: "-4px 0 20px rgba(0,0,0,0.15)",
                        zIndex: 350,
                        display: "flex",
                        flexDirection: "column",
                        overflow: "hidden",
                     }}
                  >
                     {/* 헤더 */}
                     <div
                        style={{
                           background: panelColor,
                           padding: "16px 16px 14px",
                           color: "#fff",
                        }}
                     >
                        <div
                           style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "flex-start",
                           }}
                        >
                           <div>
                              <div
                                 style={{
                                    fontSize: 11,
                                    opacity: 0.8,
                                    marginBottom: 2,
                                 }}
                              >
                                 {dongPanel.admNm}
                              </div>
                              <div style={{ fontSize: 18, fontWeight: 800 }}>
                                 {dongPanel.dongNm}
                              </div>
                           </div>
                           <button
                              onClick={() => setDongPanel(null)}
                              style={{
                                 background: "rgba(255,255,255,0.2)",
                                 border: "none",
                                 borderRadius: 8,
                                 padding: "4px 10px",
                                 color: "#fff",
                                 cursor: "pointer",
                                 fontSize: 14,
                              }}
                           >
                              ✕
                           </button>
                        </div>
                        <div
                           style={{ marginTop: 8, fontSize: 11, opacity: 0.85 }}
                        >
                           {isRE ? "🏢 실거래가 분석" : "📊 상권 매출 분석"}
                        </div>
                     </div>

                     {/* 바디 */}
                     <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
                        {!d ? (
                           <div
                              style={{
                                 color: "#bbb",
                                 fontSize: 13,
                                 textAlign: "center",
                                 marginTop: 40,
                              }}
                           >
                              데이터 없음
                           </div>
                        ) : isRE ? (
                           /* ── 실거래가 패널 (price-overlay 기반) ── */
                           <div
                              style={{
                                 display: "flex",
                                 flexDirection: "column",
                                 gap: 12,
                              }}
                           >
                              <div
                                 style={{
                                    background: panelBg,
                                    borderRadius: 12,
                                    padding: 14,
                                 }}
                              >
                                 <div
                                    style={{
                                       fontSize: 10,
                                       color: "#888",
                                       marginBottom: 4,
                                    }}
                                 >
                                    평균 거래금액
                                 </div>
                                 <div
                                    style={{
                                       fontSize: 22,
                                       fontWeight: 800,
                                       color: panelColor,
                                    }}
                                 >
                                    {d?.avg_str || "-"}
                                 </div>
                                 <div
                                    style={{
                                       fontSize: 11,
                                       color: "#64748b",
                                       marginTop: 2,
                                    }}
                                 >
                                    거래건수 {d?.count?.toLocaleString() || "-"}
                                    건
                                 </div>
                              </div>
                              <button
                                 style={{
                                    padding: "10px",
                                    background: panelColor,
                                    color: "#fff",
                                    border: "none",
                                    borderRadius: 8,
                                    fontSize: 12,
                                    fontWeight: 700,
                                    cursor: "pointer",
                                 }}
                                 onClick={async () => {
                                    const res = await fetch(
                                       `${REALESTATE_URL}/realestate/analysis?sigungu=${encodeURIComponent(dongPanel.guNm)}&dong=${encodeURIComponent(dongPanel.dongNm)}`,
                                    );
                                    const json = await res.json();
                                    setDongPanel((prev) => ({
                                       ...prev,
                                       analysisData: json,
                                    }));
                                 }}
                              >
                                 📋 상세 실거래가 조회
                              </button>
                              {dongPanel.analysisData &&
                                 (() => {
                                    const a = dongPanel.analysisData;
                                    return (
                                       <div>
                                          {["상업용", "오피스텔"].map(
                                             (type) => {
                                                const t = a[type];
                                                if (!t || t.거래건수 === 0)
                                                   return null;
                                                return (
                                                   <div
                                                      key={type}
                                                      style={{
                                                         background: "#f8fafc",
                                                         borderRadius: 12,
                                                         padding: 14,
                                                         marginBottom: 8,
                                                      }}
                                                   >
                                                      <div
                                                         style={{
                                                            fontSize: 11,
                                                            fontWeight: 700,
                                                            color: "#475569",
                                                            marginBottom: 8,
                                                         }}
                                                      >
                                                         {type === "상업용"
                                                            ? "🏪 상업용"
                                                            : "🏠 오피스텔"}
                                                      </div>
                                                      <div
                                                         style={{
                                                            display: "grid",
                                                            gridTemplateColumns:
                                                               "1fr 1fr",
                                                            gap: 6,
                                                         }}
                                                      >
                                                         {[
                                                            [
                                                               "건수",
                                                               `${t.거래건수}건`,
                                                            ],
                                                            ["평균", t.평균가],
                                                            ["최저", t.최저가],
                                                            ["최고", t.최고가],
                                                         ].map(([k, v]) => (
                                                            <div key={k}>
                                                               <div
                                                                  style={{
                                                                     fontSize: 10,
                                                                     color: "#888",
                                                                  }}
                                                               >
                                                                  {k}
                                                               </div>
                                                               <div
                                                                  style={{
                                                                     fontSize: 12,
                                                                     fontWeight: 700,
                                                                  }}
                                                               >
                                                                  {v || "-"}
                                                               </div>
                                                            </div>
                                                         ))}
                                                      </div>
                                                   </div>
                                                );
                                             },
                                          )}
                                          {a.분석기간 && (
                                             <div
                                                style={{
                                                   fontSize: 10,
                                                   color: "#bbb",
                                                   textAlign: "right",
                                                }}
                                             >
                                                {a.분析기간}
                                             </div>
                                          )}
                                       </div>
                                    );
                                 })()}
                           </div>
                        ) : (
                           /* ── 매출 패널 ── */
                           <div
                              style={{
                                 display: "flex",
                                 flexDirection: "column",
                                 gap: 12,
                              }}
                           >
                              {/* 총매출 */}
                              <div
                                 style={{
                                    background: panelBg,
                                    borderRadius: 12,
                                    padding: 14,
                                 }}
                              >
                                 <div
                                    style={{
                                       fontSize: 10,
                                       color: "#888",
                                       marginBottom: 4,
                                    }}
                                 >
                                    총 매출
                                 </div>
                                 <div
                                    style={{
                                       fontSize: 22,
                                       fontWeight: 800,
                                       color: panelColor,
                                    }}
                                 >
                                    {formatAmt(d.sales)}
                                 </div>
                                 <div
                                    style={{
                                       fontSize: 11,
                                       color: "#64748b",
                                       marginTop: 2,
                                    }}
                                 >
                                    점포수 {d.selng_co?.toLocaleString() || "-"}
                                    개
                                    {d.quarter &&
                                       ` · ${String(d.quarter).replace(/(\d{4})(\d)/, "$1년 $2분기")}`}
                                 </div>
                              </div>

                              {/* 주중/주말 */}
                              <div
                                 style={{
                                    background: "#f8fafc",
                                    borderRadius: 12,
                                    padding: 14,
                                 }}
                              >
                                 <div
                                    style={{
                                       fontSize: 11,
                                       fontWeight: 700,
                                       color: "#475569",
                                       marginBottom: 8,
                                    }}
                                 >
                                    📅 주중/주말
                                 </div>
                                 {[
                                    {
                                       label: "주중",
                                       val: d.sales_mdwk,
                                       total: d.sales,
                                       color: "#3b82f6",
                                    },
                                    {
                                       label: "주말",
                                       val: d.sales_wkend,
                                       total: d.sales,
                                       color: "#8b5cf6",
                                    },
                                 ].map(({ label, val, total, color }) => {
                                    const pct =
                                       total > 0
                                          ? Math.round((val / total) * 100)
                                          : 0;
                                    return (
                                       <div
                                          key={label}
                                          style={{ marginBottom: 8 }}
                                       >
                                          <div
                                             style={{
                                                display: "flex",
                                                justifyContent: "space-between",
                                                fontSize: 12,
                                                marginBottom: 3,
                                             }}
                                          >
                                             <span>{label}</span>
                                             <span style={{ fontWeight: 700 }}>
                                                {formatAmt(val)} ({pct}%)
                                             </span>
                                          </div>
                                          <div
                                             style={{
                                                height: 6,
                                                background: "#e2e8f0",
                                                borderRadius: 3,
                                                overflow: "hidden",
                                             }}
                                          >
                                             <div
                                                style={{
                                                   width: `${pct}%`,
                                                   height: "100%",
                                                   background: color,
                                                   borderRadius: 3,
                                                }}
                                             />
                                          </div>
                                       </div>
                                    );
                                 })}
                              </div>

                              {/* 성별 */}
                              <div
                                 style={{
                                    background: "#f8fafc",
                                    borderRadius: 12,
                                    padding: 14,
                                 }}
                              >
                                 <div
                                    style={{
                                       fontSize: 11,
                                       fontWeight: 700,
                                       color: "#475569",
                                       marginBottom: 8,
                                    }}
                                 >
                                    👤 성별 매출
                                 </div>
                                 {[
                                    {
                                       label: "남성",
                                       val: d.sales_male,
                                       total: d.sales,
                                       color: "#2563eb",
                                    },
                                    {
                                       label: "여성",
                                       val: d.sales_female,
                                       total: d.sales,
                                       color: "#ec4899",
                                    },
                                 ].map(({ label, val, total, color }) => {
                                    const pct =
                                       total > 0
                                          ? Math.round((val / total) * 100)
                                          : 0;
                                    return (
                                       <div
                                          key={label}
                                          style={{ marginBottom: 8 }}
                                       >
                                          <div
                                             style={{
                                                display: "flex",
                                                justifyContent: "space-between",
                                                fontSize: 12,
                                                marginBottom: 3,
                                             }}
                                          >
                                             <span>{label}</span>
                                             <span style={{ fontWeight: 700 }}>
                                                {formatAmt(val)} ({pct}%)
                                             </span>
                                          </div>
                                          <div
                                             style={{
                                                height: 6,
                                                background: "#e2e8f0",
                                                borderRadius: 3,
                                                overflow: "hidden",
                                             }}
                                          >
                                             <div
                                                style={{
                                                   width: `${pct}%`,
                                                   height: "100%",
                                                   background: color,
                                                   borderRadius: 3,
                                                }}
                                             />
                                          </div>
                                       </div>
                                    );
                                 })}
                              </div>

                              {/* 연령대 */}
                              {(d.age20 || d.age30 || d.age40 || d.age50) && (
                                 <div
                                    style={{
                                       background: "#f8fafc",
                                       borderRadius: 12,
                                       padding: 14,
                                    }}
                                 >
                                    <div
                                       style={{
                                          fontSize: 11,
                                          fontWeight: 700,
                                          color: "#475569",
                                          marginBottom: 8,
                                       }}
                                    >
                                       🎂 연령대 매출
                                    </div>
                                    {[
                                       { label: "20대", val: d.age20 },
                                       { label: "30대", val: d.age30 },
                                       { label: "40대", val: d.age40 },
                                       { label: "50대", val: d.age50 },
                                    ].map(({ label, val }) => {
                                       const pct =
                                          d.sales > 0
                                             ? Math.round(
                                                  ((val || 0) / d.sales) * 100,
                                               )
                                             : 0;
                                       return (
                                          <div
                                             key={label}
                                             style={{ marginBottom: 6 }}
                                          >
                                             <div
                                                style={{
                                                   display: "flex",
                                                   justifyContent:
                                                      "space-between",
                                                   fontSize: 12,
                                                   marginBottom: 2,
                                                }}
                                             >
                                                <span>{label}</span>
                                                <span
                                                   style={{ fontWeight: 700 }}
                                                >
                                                   {formatAmt(val)} ({pct}%)
                                                </span>
                                             </div>
                                             <div
                                                style={{
                                                   height: 5,
                                                   background: "#e2e8f0",
                                                   borderRadius: 3,
                                                   overflow: "hidden",
                                                }}
                                             >
                                                <div
                                                   style={{
                                                      width: `${pct}%`,
                                                      height: "100%",
                                                      background: "#059669",
                                                      borderRadius: 3,
                                                   }}
                                                />
                                             </div>
                                          </div>
                                       );
                                    })}
                                 </div>
                              )}
                           </div>
                        )}
                     </div>
                  </div>
               );
            })()}

         {/* 좌표 바 */}
         <div
            style={{
               position: "absolute",
               bottom: 14,
               left: "50%",
               transform: "translateX(-50%)",
               background: "rgba(255,255,255,0.92)",
               border: "1px solid #e5e7eb",
               borderRadius: 8,
               padding: "5px 16px",
               fontSize: 12,
               color: "#666",
               fontFamily: "'JetBrains Mono',monospace",
               zIndex: 100,
            }}
         >
            📍 위도: {coords.lat} | 경도: {coords.lng}
         </div>
      </div>
   );
}
