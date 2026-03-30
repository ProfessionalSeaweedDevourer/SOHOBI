import { useRef, useState, useEffect } from "react";
import { useMap } from "../../hooks/map/useMap";
import { toLonLat, fromLonLat } from "ol/proj";
import { getCenter as getExtentCenter, extend as extendExtent, createEmpty as createEmptyExtent } from "ol/extent";

// ── UI 컴포넌트 ────────────────────────────────────────────────
import Layerpanel from "./panel/Layerpanel";
import CategoryPanel from "./panel/CategoryPanel";
import MapControls from "./controls/MapControls";
import DongPanel from "./panel/DongPanel";
import DongTooltip from "./controls/DongTooltip";
import WmsPopup from "./popup/WmsPopup";
import StorePopup from "./popup/StorePopup";
import ChatPanel from "./ChatPanel";

// ── 커스텀 훅 ──────────────────────────────────────────────────
import { useMarkers } from "../../hooks/map/useMarkers";
import {
   useDongLayer,
   DONG_STYLE_DEFAULT,
   DONG_STYLE_HOVER,
   DONG_STYLE_SELECTED,
} from "../../hooks/map/useDongLayer";
import { handleWmsClick } from "../../hooks/map/useWmsClick";
// ── 상수/스타일 ────────────────────────────────────────────────
import { CATEGORIES } from "../../constants/categories";
import "./MapView.css";

// ── API 엔드포인트 (vite proxy: /map-api → 8681, /realestate → 8682) ──
const FASTAPI_URL = import.meta.env.VITE_MAP_API_URL || "/map-api";
const REALESTATE_URL = import.meta.env.VITE_REALESTATE_URL || "";
const KAKAO_REST_KEY = import.meta.env.VITE_KAKAO_API_KEY;

// ── 카카오 키워드 검색 ──────────────────────────────────────────
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

// ── 줌 레벨별 반경/건수 계산 ───────────────────────────────────
function getRadiusAndLimit(zoom) {
   if (zoom >= 18) return { radius: 100, limit: 2000 };
   if (zoom >= 17) return { radius: 200, limit: 1500 };
   if (zoom >= 16) return { radius: 300, limit: 1000 };
   if (zoom >= 15) return { radius: 400, limit: 700 };
   if (zoom >= 14) return { radius: 500, limit: 500 };
   if (zoom >= 13) return { radius: 800, limit: 400 };
   return { radius: 1200, limit: 300 };
}

// ── 메인 컴포넌트 ──────────────────────────────────────────────
export default function MapView() {
   const mapRef = useRef(null);
   const mapInstance = useMap(mapRef);
   const clickModeRef = useRef(true);
   const wmsLayerRef = useRef(null);

   const [coords, setCoords] = useState({ lat: "37.5665", lng: "126.9780" });
   const [chatOpen, setChatOpen] = useState(false);
   const [chatContext, setChatContext] = useState(null);
   const [popup, setPopup] = useState(null);
   const [kakaoDetail, setKakaoDetail] = useState(null);
   const [loadingDetail, setLoadingDetail] = useState(false);
   const [nearbyCount, setNearbyCount] = useState(null);
   const [loading, setLoading] = useState(false);
   const [wmsPopup, setWmsPopup] = useState(null);
   const [landValue, setLandValue] = useState(null);
   const [showPanel, setShowPanel] = useState(false);
   const [clickMode, setClickMode] = useState(true);

   const [dongMode, setDongMode] = useState("none");
   const [dongLoading, setDongLoading] = useState(false);
   const [dongPanel, setDongPanel] = useState(null);
   const [dongTooltip, setDongTooltip] = useState(null);
   const [quarters, setQuarters] = useState([]);
   const [selectedQtr, setSelectedQtr] = useState("");
   const dongModeRef = useRef("none");
   const currentGuNmRef = useRef("");

   useEffect(() => {
      dongModeRef.current = dongMode;
   }, [dongMode]);

   // ── 분기 변경 시 현재 패널 자동 재조회 ─────────────────────────────
   useEffect(() => {
      if (
         !selectedQtr ||
         !dongPanel ||
         dongPanel.mode !== "sales" ||
         !dongPanel.admCd
      )
         return;
      const qtrParam = `&quarter=${encodeURIComponent(selectedQtr)}`;
      fetch(
         `${REALESTATE_URL}/realestate/sangkwon?adm_cd=${encodeURIComponent(dongPanel.admCd)}${qtrParam}`,
      )
         .then((r) => r.json())
         .then((jj) => {
            if (jj.data)
               setDongPanel((prev) =>
                  prev ? { ...prev, apiData: jj.data, avg: jj.avg } : prev,
               );
         })
         .catch(() => {});
   }, [selectedQtr]); // eslint-disable-line

   // ── 분기 목록 초기 로드 ──────────────────────────────────────────
   useEffect(() => {
      fetch(`${REALESTATE_URL}/realestate/sangkwon-quarters`)
         .then((r) => r.json())
         .then((d) => {
            if (d.quarters?.length) {
               const sorted = [...d.quarters].sort((a, b) =>
                  b.localeCompare(a),
               );
               setQuarters(sorted);
               setSelectedQtr(sorted[0]); // 최신 분기 기본 선택
            }
         })
         .catch(() => {});
   }, []);
   useEffect(() => {
      clickModeRef.current = clickMode;
   }, [clickMode]);

   const allCatKeys = new Set(CATEGORIES.map((c) => c.key));
   const [visibleCats, setVisibleCats] = useState(allCatKeys);
   const visibleCatsRef = useRef(allCatKeys); // 클로저 캡처 방지용 ref
   const [catCounts, setCatCounts] = useState({});
   const [svcData, setSvcData] = useState([]);
   const [selectedSvc, setSelectedSvc] = useState(""); // 업종 필터 선택값

   const { allStoresRef, drawCircle, drawMarkers, clearMarkers } = useMarkers(
      mapInstance,
      visibleCats,
   );
   const {
      dongBoundaryLayerRef,
      dongHoverFeatRef,
      dongHoverNameRef,
      ensureDongBoundaryLayer,
      resetDongLayer,
   } = useDongLayer(mapInstance);
   const dongSelectedFeatRef = useRef(null); // 현재 선택(클릭)된 폴리곤
   const dongSearchFeatsRef = useRef([]); // 검색으로 하이라이트된 폴리곤 목록

   const handleToggleCat = (key) =>
      setVisibleCats((prev) => {
         const n = new Set(prev);
         n.has(key) ? n.delete(key) : n.add(key);
         visibleCatsRef.current = n;
         return n;
      });
   const handleShowAll = () => {
      const all = new Set(CATEGORIES.map((c) => c.key));
      visibleCatsRef.current = all;
      setVisibleCats(all);
   };
   const handleHideAll = () => {
      visibleCatsRef.current = new Set();
      setVisibleCats(new Set());
   };

   // ── 채팅 → 지도 네비게이션 콜백 ────────────────────────────────
   // ChatPanel에서 onNavigate(lng, lat, zoom) 형태로 호출
   const handleChatNavigate = (lng, lat, zoom = 16) => {
      const map = mapInstance.current;
      if (!map) return;
      map.getView().animate({
         center: fromLonLat([lng, lat]),
         zoom,
         duration: 800,
      });
   };

   // ── 상권 분석 결과 → 행정동 폴리곤 하이라이트 ──────────────────
   // ChatPanel에서 onHighlightArea(admCodes) 형태로 호출
   const handleHighlightArea = (admCodes) => {
      const layer = dongBoundaryLayerRef.current;
      if (!layer) return;
      const admSet = new Set(admCodes.map((c) => String(c).trim()));
      const features = layer.getSource().getFeatures();
      features.forEach((f) => {
         const cd = String(f.getProperties().adm_cd || "").trim();
         f.setStyle(admSet.has(cd) ? DONG_STYLE_SELECTED : null);
      });
      if (admCodes.length === 0) return;
      const matched = features.filter((f) =>
         admSet.has(String(f.getProperties().adm_cd || "").trim()),
      );
      if (matched.length > 0) {
         const extent = matched.reduce(
            (acc, f) => extendExtent(acc, f.getGeometry().getExtent()),
            createEmptyExtent(),
         );
         mapInstance.current?.getView().fit(extent, {
            padding: [80, 480, 80, 80],
            duration: 800,
            maxZoom: 16,
         });
      }
   };

   const clearAll = () => {
      clearMarkers();
      setPopup(null);
      setKakaoDetail(null);
      setNearbyCount(null);
      setLandValue(null);
      setWmsPopup(null);
      setDongPanel(null);
      setCatCounts({});
   };

   // ── 구/동 검색 → 폴리곤 하이라이트 ────────────────────────────
   const handleSearch = async (query) => {
      const bLayer = dongBoundaryLayerRef.current;
      if (!bLayer?.getSource?.()?.getFeatures) {
         ensureDongBoundaryLayer().then(() => handleSearch(query));
         return;
      }
      const q = query.trim();
      if (!q) return;

      const features = bLayer.getSource().getFeatures();

      // 이전 선택 초기화
      features.forEach((f) => f.setStyle(DONG_STYLE_DEFAULT));
      dongSelectedFeatRef.current = null;
      dongHoverFeatRef.current = null;
      dongHoverNameRef.current = "";
      setDongPanel(null);
      setDongTooltip(null);

      // 1차: GeoJSON 폴리곤에서 직접 매칭
      let matched = features.filter((f) => {
         const p = f.getProperties();
         return (p.adm_nm || "").includes(q) || (p.gu_nm || "").includes(q);
      });

      // 2차: GeoJSON에서 못 찾으면 DB LIKE 검색 → adm_cd로 매칭
      if (!matched.length) {
         try {
            const res = await fetch(
               `${REALESTATE_URL}/realestate/search-dong?q=${encodeURIComponent(q)}`,
            );
            const jj = await res.json();
            if (jj.data?.length) {
               const admCds = new Set(jj.data.map((d) => d.adm_cd));
               matched = features.filter((f) =>
                  admCds.has(f.getProperties().adm_cd),
               );
            }
         } catch (e) {
            console.error("[search-dong]", e);
         }
      }

      if (!matched.length) return;

      // 하이라이트 + ref 저장
      matched.forEach((f) => f.setStyle(DONG_STYLE_SELECTED));
      dongSearchFeatsRef.current = matched;
      if (matched.length === 1) dongSelectedFeatRef.current = matched[0];

      // 첫 번째 매칭 폴리곤으로 지도 이동
      const map = mapInstance.current;
      if (!map) return;
      const extent = matched[0].getGeometry().getExtent();
      map.getView().fit(extent, {
         padding: [60, 60, 60, 60],
         duration: 600,
         maxZoom: 17,
      });

      // ── 폴리곤 중심점 기반 반경 검색 자동 실행 ──────────────────
      const centerCoord = getExtentCenter(extent);
      const [lng, lat] = toLonLat(centerCoord);
      const zoom = map.getView().getZoom() ?? 15;
      const { radius, limit } = getRadiusAndLimit(zoom);

      setLoading(true);
      setNearbyCount(null);
      setCatCounts({});
      clearMarkers();

      fetch(
         `${FASTAPI_URL}/map/nearby?lat=${lat}&lng=${lng}&radius=${radius}&limit=${limit}`,
      )
         .then((r) => r.json())
         .then((data) => {
            const stores = data.stores || [];
            setNearbyCount(data.count);
            allStoresRef.current = stores;
            const counts = {};
            stores.forEach((s) => {
               const key =
                  CATEGORIES.find((c) => c.key === s.상권업종대분류코드)?.key ||
                  "기타";
               counts[key] = (counts[key] || 0) + 1;
            });
            setCatCounts(counts);
            drawCircle(lng, lat, radius);
            drawMarkers(stores, visibleCatsRef.current);
         })
         .catch(() => {})
         .finally(() => setLoading(false));
   };

   // ── 동 모드 전환 핸들러 ─────────────────────────────────────────
   const handleDongMode = async (mode) => {
      const next = dongMode === mode ? "none" : mode;
      setDongMode(next);
      if (next === "none") {
         resetDongLayer();
         setDongPanel(null);
         setDongTooltip(null);
         dongSelectedFeatRef.current = null;
         dongSearchFeatsRef.current = [];
      } else {
         await ensureDongBoundaryLayer();
         // ── 3번: 선택된 폴리곤 있으면 모드 전환 시 자동 재조회 ──
         const selFeat = dongSelectedFeatRef.current;
         if (selFeat) {
            const p = selFeat.getProperties();
            const _emdCd = (p.adm_cd || "").trim();
            const _admCd = (p.adm_cd || "").trim();
            const _dongNm = p.adm_nm || "";
            const _admNm = p.adm_nm || _dongNm;
            const _guNm = p.gu_nm || currentGuNmRef.current || "";
            setDongLoading(true);
            setDongPanel(null);
            try {
               if (next === "sales") {
                  const qtrParam = selectedQtr
                     ? `&quarter=${encodeURIComponent(selectedQtr)}`
                     : "";
                  const url = _admCd
                     ? `${REALESTATE_URL}/realestate/sangkwon?adm_cd=${encodeURIComponent(_admCd)}${qtrParam}`
                     : `${REALESTATE_URL}/realestate/sangkwon?dong=${encodeURIComponent(_dongNm)}&gu=${encodeURIComponent(_guNm)}`;
                  const rr = await fetch(url);
                  const jj = await rr.json();
                  if (jj.data)
                     setDongPanel({
                        mode: next,
                        dongNm: _dongNm,
                        admNm: _admNm,
                        guNm: _guNm,
                        admCd: _admCd,
                        apiData: jj.data,
                        avg: jj.avg,
                     });
               } else if (next === "realestate") {
                  const rr = await fetch(
                     `${REALESTATE_URL}/realestate/seoul-rtms?adm_cd=${encodeURIComponent(_admCd || _emdCd)}`,
                  );
                  const jj = await rr.json();
                  if (jj)
                     setDongPanel({
                        mode: next,
                        dongNm: _dongNm,
                        admNm: _admNm,
                        guNm: _guNm,
                        admCd: _admCd,
                        apiData: jj,
                     });
               } else if (next === "store") {
                  const rr = await fetch(
                     `${REALESTATE_URL}/realestate/sangkwon-store?adm_cd=${encodeURIComponent(_admCd)}`,
                  );
                  const jj = await rr.json();
                  if (jj)
                     setDongPanel({
                        mode: next,
                        dongNm: _dongNm,
                        admNm: _admNm,
                        guNm: _guNm,
                        admCd: _admCd,
                        apiData: jj,
                     });
               }
            } catch (e) {
               console.error("[모드전환 재조회]", e);
            } finally {
               setDongLoading(false);
            }
         }
      }
   };

   useEffect(() => {
      const map = mapInstance.current;
      if (!map) return;

      (async () => {
         try {
            const [cLng, cLat] = toLonLat(map.getView().getCenter());
            const r = await fetch(
               `/kakao/v2/local/geo/coord2regioncode.json?x=${cLng}&y=${cLat}`,
               { headers: { Authorization: `KakaoAK ${KAKAO_REST_KEY}` } },
            );
            const rj = await r.json();
            const region = rj.documents?.find((d) => d.region_type === "H");
            if (region?.region_2depth_name)
               currentGuNmRef.current = region.region_2depth_name;
         } catch {
            /* ignore */
         }
      })();

      const moveHandler = (e) => {
         const [lng, lat] = toLonLat(e.coordinate);
         setCoords({ lat: lat.toFixed(6), lng: lng.toFixed(6) });

         if (dongModeRef.current === "none") return;
         const bLayer = dongBoundaryLayerRef.current;
         if (!bLayer?.getSource?.()?.getFeatures) return;

         const feat = map.forEachFeatureAtPixel(e.pixel, (f) => f, {
            layerFilter: (l) => l === bLayer,
            hitTolerance: 4,
         });

         if (feat === dongHoverFeatRef.current) {
            if (feat)
               setDongTooltip((prev) =>
                  prev ? { ...prev, x: e.pixel[0], y: e.pixel[1] } : prev,
               );
            return;
         }
         if (
            dongHoverFeatRef.current &&
            dongHoverFeatRef.current !== dongSelectedFeatRef.current &&
            !dongSearchFeatsRef.current.includes(dongHoverFeatRef.current)
         ) {
            dongHoverFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
         }

         if (feat) {
            feat.setStyle(DONG_STYLE_HOVER);
            dongHoverFeatRef.current = feat;
            map.getTargetElement().style.cursor = "pointer";

            const p = feat.getProperties();
            const dongNm = p.adm_nm || p.name || "";
            const guNm = p.sig_kor_nm || p.sig_nm || p.sgg_nm || "";
            if (guNm) currentGuNmRef.current = guNm;

            if (dongNm !== dongHoverNameRef.current) {
               dongHoverNameRef.current = dongNm;
               setDongTooltip({
                  x: e.pixel[0],
                  y: e.pixel[1],
                  dongNm,
                  guNm,
                  sales: null,
                  loading: true,
               });
               clearTimeout(moveHandler._t);
               moveHandler._t = setTimeout(async () => {
                  if (dongModeRef.current === "none") return;
                  try {
                     const _admCd = feat.getProperties().adm_cd || "";
                     if (!_admCd) {
                        setDongTooltip((prev) =>
                           prev?.dongNm === dongNm
                              ? { ...prev, sales: null, loading: false }
                              : prev,
                        );
                        return;
                     }
                     const _qp = selectedQtr
                        ? `&quarter=${encodeURIComponent(selectedQtr)}`
                        : "";
                     const r = await fetch(
                        `${REALESTATE_URL}/realestate/sangkwon?adm_cd=${encodeURIComponent(_admCd)}${_qp}`,
                     );
                     const j = await r.json();
                     setDongTooltip((prev) =>
                        prev?.dongNm === dongNm
                           ? { ...prev, sales: j.data || null, loading: false }
                           : prev,
                     );
                  } catch {
                     setDongTooltip((prev) =>
                        prev?.dongNm === dongNm
                           ? { ...prev, loading: false }
                           : prev,
                     );
                  }
               }, 250);
            } else {
               setDongTooltip((prev) =>
                  prev ? { ...prev, x: e.pixel[0], y: e.pixel[1] } : prev,
               );
            }
         } else {
            if (
               dongHoverFeatRef.current &&
               dongHoverFeatRef.current !== dongSelectedFeatRef.current &&
               !dongSearchFeatsRef.current.includes(dongHoverFeatRef.current)
            ) {
               dongHoverFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
            }
            dongHoverFeatRef.current = null;
            dongHoverNameRef.current = "";
            map.getTargetElement().style.cursor = "";
            setDongTooltip(null);
            clearTimeout(moveHandler._t);
         }
      };

      const clickHandler = async (e) => {
         if (dongModeRef.current !== "none") {
            const bLayer = dongBoundaryLayerRef.current;
            const feat = bLayer?.getSource?.()?.getFeatures
               ? map.forEachFeatureAtPixel(e.pixel, (f) => f, {
                    layerFilter: (l) => l === bLayer,
                    hitTolerance: 6,
                 })
               : null;

            if (feat) {
               const p = feat.getProperties();
               const _emdCd = (p.adm_cd || "").trim();
               const _admCd = (p.adm_cd || "").trim();
               const _dongNm = p.adm_nm || "";
               const _admNm = p.adm_nm || _dongNm;
               const _guNm =
                  p.gu_nm || p.sig_kor_nm || currentGuNmRef.current || "";

               if (_dongNm) {
                  if (_guNm) currentGuNmRef.current = _guNm;
                  // 이전 선택 해제 (클릭 선택)
                  if (
                     dongSelectedFeatRef.current &&
                     dongSelectedFeatRef.current !== feat
                  ) {
                     dongSelectedFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
                  }
                  // 검색 하이라이트 해제
                  dongSearchFeatsRef.current.forEach((f) => {
                     if (f !== feat) f.setStyle(DONG_STYLE_DEFAULT);
                  });
                  dongSearchFeatsRef.current = [];
                  if (
                     dongHoverFeatRef.current &&
                     dongHoverFeatRef.current !== feat
                  ) {
                     dongHoverFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
                  }
                  // 새 선택 하이라이트 유지
                  feat.setStyle(DONG_STYLE_SELECTED);
                  dongSelectedFeatRef.current = feat;
                  dongHoverFeatRef.current = feat;
                  setDongTooltip(null);
                  setDongLoading(true);
                  setDongPanel(null);

                  const _mode = dongModeRef.current;
                  try {
                     if (_mode === "store") {
                        const rr = await fetch(
                           `${REALESTATE_URL}/realestate/sangkwon-store?adm_cd=${encodeURIComponent(_admCd)}`,
                        );
                        const jj = await rr.json();
                        if (jj)
                           setDongPanel({
                              mode: _mode,
                              dongNm: _dongNm,
                              admNm: _admNm,
                              guNm: _guNm,
                              admCd: _admCd,
                              apiData: jj,
                           });
                     } else if (_mode === "sales") {
                        const qtrParam = selectedQtr
                           ? `&quarter=${encodeURIComponent(selectedQtr)}`
                           : "";
                        const url = _admCd
                           ? `${REALESTATE_URL}/realestate/sangkwon?adm_cd=${encodeURIComponent(_admCd)}${qtrParam}`
                           : `${REALESTATE_URL}/realestate/sangkwon?dong=${encodeURIComponent(_dongNm)}&gu=${encodeURIComponent(_guNm)}`;
                        const rr = await fetch(url);
                        const jj = await rr.json();
                        if (jj.data)
                           setDongPanel({
                              mode: _mode,
                              dongNm: _dongNm,
                              admNm: _admNm,
                              guNm: _guNm,
                              admCd: _admCd,
                              apiData: jj.data,
                              avg: jj.avg,
                           });
                        else
                           setDongPanel({
                              mode: _mode,
                              dongNm: _dongNm,
                              admNm: _admNm,
                              guNm: _guNm,
                              apiData: null,
                              empty: true,
                           });
                        // 업종별 매출 조회
                        if (_admCd) {
                           fetch(
                              `${REALESTATE_URL}/realestate/sangkwon-svc?adm_cd=${encodeURIComponent(_admCd)}${qtrParam}`,
                           )
                              .then((r) => r.json())
                              .then((sv) => setSvcData(sv.data || []))
                              .catch(() => setSvcData([]));
                        }
                     } else if (_mode === "realestate") {
                        const rr = await fetch(
                           `${REALESTATE_URL}/realestate/seoul-rtms?adm_cd=${encodeURIComponent(_admCd || _emdCd)}`,
                        );
                        const jj = await rr.json();
                        if (jj)
                           setDongPanel({
                              mode: _mode,
                              dongNm: _dongNm,
                              admNm: _admNm,
                              guNm: _guNm,
                              admCd: _admCd,
                              apiData: jj,
                           });
                     }
                  } catch (err) {
                     console.error("[동 클릭 패널]", err);
                  } finally {
                     setDongLoading(false);
                  }
                  return;
               }
            }
         }

         const wmsResult = await handleWmsClick(map, e.coordinate);
         if (wmsResult) {
            setPopup(null);
            setWmsPopup(wmsResult.parsed);
            setLandValue(wmsResult.landValue || null);
            if (wmsResult.parsed.sigg)
               currentGuNmRef.current = wmsResult.parsed.sigg;
            return;
         }
         setWmsPopup(null);

         const feature = map.forEachFeatureAtPixel(e.pixel, (f) => f);
         if (feature?.get("store")) {
            const store = feature.get("store");
            setPopup(store);
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
            const counts = {};
            stores.forEach((s) => {
               const key =
                  CATEGORIES.find((c) => c.key === s.상권업종대분류코드)?.key ||
                  "기타";
               counts[key] = (counts[key] || 0) + 1;
            });
            setCatCounts(counts);
            drawCircle(lng, lat, radius);
            drawMarkers(stores, visibleCatsRef.current); // ref로 최신값 보장
         } catch (err) {
            console.error("DB 조회 오류:", err);
         } finally {
            setLoading(false);
         }
      };

      map.on("pointermove", moveHandler);
      map.on("click", clickHandler);
      // ── JSX 렌더 ───────────────────────────────────────────────────
      return () => {
         map.un("pointermove", moveHandler);
         map.un("click", clickHandler);
         clearTimeout(moveHandler._t);
         if (map.getTargetElement()) map.getTargetElement().style.cursor = "";
      };
   }, []); // eslint-disable-line react-hooks/exhaustive-deps

   // ── JSX 렌더 ───────────────────────────────────────────────────
   return (
      <div className="mv-root">
         <CategoryPanel
            visibleCats={visibleCats}
            onToggle={handleToggleCat}
            onShowAll={handleShowAll}
            onHideAll={handleHideAll}
            totalCount={nearbyCount}
            catCounts={catCounts}
            onSearch={handleSearch}
         />
         <div ref={mapRef} className="mv-map" />
         <MapControls
            clickMode={clickMode}
            setClickMode={setClickMode}
            nearbyCount={nearbyCount}
            loading={loading}
            onClear={clearAll}
            dongMode={dongMode}
            onDongMode={handleDongMode}
            dongLoading={dongLoading}
            currentGuNm={currentGuNmRef.current}
         />
         <button
            className="mv-layer-btn"
            onClick={() => setShowPanel((p) => !p)}
         >
            🗂️
         </button>
         {showPanel && mapInstance.current && (
            <div className="mv-layer-panel-wrap">
               <Layerpanel
                  map={mapInstance.current}
                  vworldKey={import.meta.env.VITE_VWORLD_API_KEY}
                  wmsLayerRef={wmsLayerRef}
               />
            </div>
         )}
         <WmsPopup
            wmsPopup={wmsPopup}
            landValue={landValue}
            onClose={() => setWmsPopup(null)}
         />
         <StorePopup
            popup={popup}
            kakaoDetail={kakaoDetail}
            loadingDetail={loadingDetail}
            onClose={() => {
               setPopup(null);
               setKakaoDetail(null);
            }}
         />
         <DongTooltip tooltip={dongTooltip} mode={dongMode} />
         <DongPanel
            dongPanel={dongPanel}
            onClose={() => setDongPanel(null)}
            svcData={svcData}
            selectedSvc={selectedSvc}
            onSvcChange={setSelectedSvc}
            quarters={quarters}
            selectedQuarter={selectedQtr}
            onQuarterChange={(q) => setSelectedQtr(q)}
            onAiAnalyze={(ctx) => {
               setChatContext(ctx);
               setChatOpen(true);
               setDongPanel(null);
            }}
         />
         <ChatPanel
            isOpen={chatOpen}
            onToggle={() => setChatOpen((prev) => !prev)}
            mapContext={chatContext}
            onNavigate={handleChatNavigate}
            onHighlightArea={handleHighlightArea}
            onClearContext={() => setChatContext(null)}
         />
         <div className="coord-bar">
            📍 위도: {coords.lat} | 경도: {coords.lng}
         </div>
      </div>
   );
}
