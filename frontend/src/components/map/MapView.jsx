// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\components\MapView.jsx
// 공식 프론트 위치: frontend\src\components\map\MapView.jsx

import { useRef, useState, useEffect, useCallback } from "react";
import { useMap } from "../../hooks/map/useMap";
import { useMapZoom } from "../../hooks/map/useMapZoom";
import { toLonLat, fromLonLat } from "ol/proj";
import {
   extend as extendExtent,
   createEmpty as createEmptyExtent,
} from "ol/extent";

// ── UI 컴포넌트 ────────────────────────────────────────────────
import Layerpanel from "./panel/Layerpanel";
import CategoryPanel from "./panel/CategoryPanel";
import MapControls from "./controls/MapControls";
import DongPanel from "./panel/DongPanel";
import WmsPopup from "./popup/WmsPopup";
import StorePopup from "./popup/StorePopup";
import ChatPanel from "./ChatPanel";
import LandmarkPopup from "./popup/LandmarkPopup";
import { useLandmarkLayer } from "../../hooks/map/useLandmarkLayer";
import { ThemeToggle } from "../ThemeToggle";

// ── 커스텀 훅 ──────────────────────────────────────────────────
import { useMarkers } from "../../hooks/map/useMarkers";
import {
   useDongLayer,
   DONG_STYLE_DEFAULT,
   DONG_STYLE_HOVER,
   DONG_STYLE_SELECTED,
} from "../../hooks/map/useDongLayer";
import { handleWmsClick } from "../../hooks/map/useWmsClick";
import { useDongPanel } from "../../hooks/map/useDongPanel";
// ── 상수/스타일 ────────────────────────────────────────────────
import { CATEGORIES } from "../../constants/categories";
import "./MapView.css";

// ── API 엔드포인트 (vite proxy: /map-api → 8681, /realestate → 8682) ──
const FASTAPI_URL = import.meta.env.VITE_MAP_URL || "";
const REALESTATE_URL = import.meta.env.VITE_REALESTATE_URL || "";
const KAKAO_REST_KEY = import.meta.env.VITE_KAKAO_API_KEY;
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _mapHeaders = _API_KEY ? { "X-API-Key": _API_KEY } : {};

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
// ── 메인 컴포넌트 ──────────────────────────────────────────────
export default function MapView() {
   const mapRef = useRef(null);
   const { mapInstance, mapReady } = useMap(mapRef);
   const wmsLayerRef = useRef(null);

   const [coords, setCoords] = useState({ lat: "37.5665", lng: "126.9780" });
   const [chatOpen, setChatOpen] = useState(false);
   const [chatContext, setChatContext] = useState(null);
   const [landmarkLoaded, setLandmarkLoaded] = useState(false);
   const [landmarkPopup, setLandmarkPopup] = useState(null);
   const [festivalLoaded, setFestivalLoaded] = useState(false);
   const [schoolLoaded, setSchoolLoaded] = useState(false);
   const [popup, setPopup] = useState(null);
   const [kakaoDetail, setKakaoDetail] = useState(null);
   const [loadingDetail, setLoadingDetail] = useState(false);
   const [nearbyCount, setNearbyCount] = useState(null);
   const [clusterPopup, setClusterPopup] = useState(null);
   const lastClusterStoresRef = useRef(null); // 뒤로가기용 클러스터 보존
   const [storeSearchOn, setStoreSearchOn] = useState(true); // 상가 전체 검색 ON/OFF
   const [buildingStores, setBuildingStores] = useState([]);
   const [loading, setLoading] = useState(false);
   const [wmsPopup, setWmsPopup] = useState(null);
   const prevStorePopupRef = useRef(null); // WmsPopup 뒤로가기용
   const catFetchTimerRef = useRef(null); // 카테고리 fetch debounce
   const [landValue, setLandValue] = useState(null);
   const [showPanel, setShowPanel] = useState(false);

   const [dongMode, setDongMode] = useState("none");

   const {
      dongLoading,
      dongPanel,
      setDongPanel,
      quarters,
      selectedQtr,
      setSelectedQtr,
      svcData,
      setSvcData,
      currentGuNmRef,
      fetchDongPanel,
   } = useDongPanel();

   const currentZoom = useMapZoom(mapInstance, mapRef, mapReady);

   const allCatKeys = new Set(CATEGORIES.map((c) => c.key));
   const [visibleCats, setVisibleCats] = useState(allCatKeys);
   const [catCounts, setCatCounts] = useState({});
   const [selectedSvc, setSelectedSvc] = useState(""); // 업종 필터 선택값
   const [selectedCatCd, setSelectedCatCd] = useState(""); // CategoryPanel 선택 대분류

   const {
      allStoresRef,
      drawMarkers,
      clearMarkers,
      selectMarker,
      markerLayerRef,
   } = useMarkers(mapInstance, visibleCats);

   const {
      landmarkLayerRef,
      festivalLayerRef,
      schoolLayerRef,
      loadLandmarks,
      loadFestivals,
      loadSchools,
      selectLandmark,
   } = useLandmarkLayer(mapInstance);

   // ── 초기 랜드마크·학교·유동인구 전체 로드 (지도 준비 후 1회) ──
   const {
      dongBoundaryLayerRef,
      dongHoverFeatRef,
      dongHoverNameRef,
      ensureDongBoundaryLayer,
      resetDongLayer,
   } = useDongLayer(mapInstance);

   const landmarkInitRef = useRef(false);
   useEffect(() => {
      if (!mapReady || !mapInstance.current || landmarkInitRef.current) return;
      landmarkInitRef.current = true;
      loadLandmarks().then(() => setLandmarkLoaded(true));
      loadFestivals().then(() => setFestivalLoaded(true));
      loadSchools().then(() => setSchoolLoaded(true));
      // 기본 폴리곤 활성화 (dongMode 기본값 sales라서 경계 표시)
      ensureDongBoundaryLayer();

      // 지적도 레이어 — mapReady 시점에 초기화 (showPanel 여부 무관)
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
                  url: `${import.meta.env.VITE_API_URL || ""}/wms/req/wms?KEY=${vKey}&DOMAIN=localhost`,
                  params: {
                     SERVICE: "WMS",
                     VERSION: "1.3.0",
                     REQUEST: "GetMap",
                     LAYERS: "lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun",
                     STYLES: ",",
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
   const dongSelectedFeatRef = useRef(null); // 현재 선택(클릭)된 폴리곤
   const dongSearchFeatsRef = useRef([]); // 검색으로 하이라이트된 폴리곤 목록

   const handleToggleCat = (key) =>
      setVisibleCats((prev) => {
         const n = new Set(prev);
         n.has(key) ? n.delete(key) : n.add(key);
         return n;
      });
   const handleShowAll = () =>
      setVisibleCats(new Set(CATEGORIES.map((c) => c.key)));
   const handleHideAll = () => setVisibleCats(new Set());

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
      if (admCodes.length === 0) {
         dongSearchFeatsRef.current = [];
         return;
      }
      const matched = features.filter((f) =>
         admSet.has(String(f.getProperties().adm_cd || "").trim()),
      );
      // 하이라이트된 feature를 dongSearchFeatsRef에 저장 → hover 시 스타일 보존
      dongSearchFeatsRef.current = matched;
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
               { headers: _mapHeaders },
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

      // 매칭된 모든 폴리곤의 상가 병렬 조회
      if (matched.length === 1) dongSelectedFeatRef.current = matched[0];
      if (storeSearchOn) {
         clearMarkers();
         setNearbyCount(null);
         const admCds = [
            ...new Set(
               matched
                  .map((f) => (f.getProperties().adm_cd || "").trim())
                  .filter(Boolean),
            ),
         ];
         Promise.all(
            admCds.map((admCd) =>
               fetch(`${FASTAPI_URL}/map/stores-by-dong?adm_cd=${admCd}`, {
                  headers: _mapHeaders,
               })
                  .then((r) => r.json())
                  .then((d) => d.stores || [])
                  .catch(() => []),
            ),
         ).then((results) => {
            const stores = results.flat();
            allStoresRef.current = stores;
            setNearbyCount(stores.length);
            const counts = {};
            stores.forEach((s) => {
               counts[s.CAT_CD || "기타"] =
                  (counts[s.CAT_CD || "기타"] || 0) + 1;
            });
            setCatCounts(counts);
            drawMarkers(stores, visibleCats);
         });
      }

      // 첫 번째 매칭 폴리곤으로 지도 이동
      const map = mapInstance.current;
      if (!map) return;
      const extent = matched.reduce((acc, f) => {
         const e = f.getGeometry().getExtent();
         return [
            Math.min(acc[0], e[0]),
            Math.min(acc[1], e[1]),
            Math.max(acc[2], e[2]),
            Math.max(acc[3], e[3]),
         ];
      }, matched[0].getGeometry().getExtent());
      map.getView().fit(extent, {
         padding: [60, 60, 60, 60],
         duration: 600,
         maxZoom: 17,
      });
   };

   // ── 동 모드 전환 핸들러 ─────────────────────────────────────────
   const handleDongMode = async (mode) => {
      const next = dongMode === mode ? "none" : mode;
      setDongMode(next);
      // none이 아닌데 선택된 폴리곤 없으면 안내
      if (next !== "none" && !dongSelectedFeatRef.current) {
         await ensureDongBoundaryLayer();
         return;
      }
      if (next === "none") {
         resetDongLayer();
         setDongPanel(null); // 패널 닫기
         dongSearchFeatsRef.current = [];
         // 마커/클러스터 유지 (모드 꺼도 상가 계속 표시)
      } else {
         await ensureDongBoundaryLayer();
         // 마커는 유지 (폴리곤 클릭 시에만 갱신)
         // ── 3번: 선택된 폴리곤 있으면 모드 전환 시 자동 재조회 ──
         const selFeat = dongSelectedFeatRef.current;
         if (selFeat) {
            const p = selFeat.getProperties();
            const _admCd = (p.adm_cd || "").trim();
            const _dongNm = p.adm_nm || "";
            const _admNm = p.adm_nm || _dongNm;
            const _guNm = p.gu_nm || currentGuNmRef.current || "";
            setDongPanel(null);
            // 모드 전환 시 스토어 이미 로드됐으면 재사용, 없으면 조회
            if (_admCd) {
               if (allStoresRef.current.length === 0) {
                  clearMarkers();
                  fetch(`${FASTAPI_URL}/map/stores-by-dong?adm_cd=${_admCd}`, {
                     headers: _mapHeaders,
                  })
                     .then((r) => r.json())
                     .then((d) => {
                        const stores = d.stores || [];
                        allStoresRef.current = stores;
                        setNearbyCount(stores.length);
                        const counts = {};
                        stores.forEach((s) => {
                           counts[s.CAT_CD || "기타"] =
                              (counts[s.CAT_CD || "기타"] || 0) + 1;
                        });
                        setCatCounts(counts);
                        drawMarkers(stores, visibleCats);
                     })
                     .catch((e) =>
                        console.error(
                           "[MapView] handleDongMode stores-by-dong 실패:",
                           e,
                        ),
                     );
               } else {
                  // 이미 로드된 마커 재활용
                  drawMarkers(allStoresRef.current, visibleCats);
               }
            }
            await fetchDongPanel(
               _admCd,
               _dongNm,
               _guNm,
               _admNm,
               next,
               selectedQtr,
            );
            if (next === "sales" && _admCd) {
               loadFestivals(_admCd).then(() => setFestivalLoaded(true));
            }
         }
      }
   };

   // fetchDongPanel을 useCallback 안에서 안전하게 호출하기 위한 ref
   const fetchDongPanelRef = useRef(null);
   fetchDongPanelRef.current = fetchDongPanel;

   // ── 1순위: 마커/랜드마크/클러스터 클릭 ─────────────────────────────
   const handleMarkerClick = useCallback(async (e) => {
      const map = mapInstance.current;
      if (!map) return false;
      const _knownLayers = [
         markerLayerRef.current,
         landmarkLayerRef.current,
         festivalLayerRef.current,
         schoolLayerRef.current,
      ].filter(Boolean);
      const markerFeat =
         _knownLayers.length > 0
            ? map.forEachFeatureAtPixel(e.pixel, (f) => f, {
                 hitTolerance: 10,
                 layerFilter: (l) => _knownLayers.includes(l),
              })
            : null;
      if (!markerFeat) return false;

      if (markerFeat.get("lmData")) {
         selectLandmark(markerFeat);
         selectMarker(null);
         setLandmarkPopup(markerFeat.get("lmData"));
         setPopup(null);
         setClusterPopup(null);
         setWmsPopup(null);
         setKakaoDetail(null);
         return true;
      }
      const clusterMembers = markerFeat.get("features");
      if (clusterMembers?.length > 1) {
         const stores = clusterMembers
            .map((f) => f.get("store"))
            .filter(Boolean);
         selectMarker(markerFeat);
         setLandmarkPopup(null);
         setPopup(null);
         setWmsPopup(null);
         setLandValue(null);
         prevStorePopupRef.current = null;
         lastClusterStoresRef.current = stores;
         setClusterPopup({ stores, x: e.pixel[0], y: e.pixel[1] });
         return true;
      }
      const realFeat =
         clusterMembers?.length === 1 ? clusterMembers[0] : markerFeat;
      if (realFeat?.get("store")) {
         const store = realFeat.get("store");
         selectMarker(markerFeat);
         setLandmarkPopup(null);
         selectLandmark(null);
         setClusterPopup(null);
         setWmsPopup(null);
         setLandValue(null);
         prevStorePopupRef.current = null;
         setPopup(store);
         setKakaoDetail(null);
         setBuildingStores([]);
         setLoadingDetail(true);
         const roadAddr = store.ROAD_ADDR || "";
         const [detail] = await Promise.all([
            fetchKakaoDetail(store.STORE_NM, roadAddr),
            roadAddr
               ? fetch(
                    `${FASTAPI_URL}/map/stores-by-building?road_addr=${encodeURIComponent(roadAddr)}&store_nm=${encodeURIComponent(store.STORE_NM || "")}&exclude_id=${encodeURIComponent(store.STORE_ID || "")}`,
                    { headers: _mapHeaders },
                 )
                    .then((r) => r.json())
                    .then((d) => setBuildingStores(d.stores || []))
                    .catch(() => setBuildingStores([]))
               : Promise.resolve(),
         ]);
         setKakaoDetail(detail);
         setLoadingDetail(false);
         return true;
      }
      return false;
   }, []); // eslint-disable-line react-hooks/exhaustive-deps — 모든 deps가 안정적(ref/setter)

   // ── 2순위: 동 폴리곤 클릭 ──────────────────────────────────────────
   const handlePolygonClick = useCallback(
      async (e) => {
         const map = mapInstance.current;
         if (!map) return false;
         if (!dongBoundaryLayerRef.current) {
            await ensureDongBoundaryLayer();
         }
         const bLayer = dongBoundaryLayerRef.current;
         const feat = bLayer?.getSource?.()?.getFeatures
            ? map.forEachFeatureAtPixel(e.pixel, (f) => f, {
                 layerFilter: (l) => l === bLayer,
                 hitTolerance: 8,
              })
            : null;
         const isMarkerClick = map.forEachFeatureAtPixel(e.pixel, () => true, {
            hitTolerance: 10,
            layerFilter: (l) => l !== dongBoundaryLayerRef.current,
         });
         if (!feat || isMarkerClick) return false;

         const p = feat.getProperties();
         const _admCd = (p.adm_cd || "").trim();
         const _dongNm = p.adm_nm || "";
         const _admNm = p.adm_nm || _dongNm;
         const _guNm = p.gu_nm || p.sig_kor_nm || currentGuNmRef.current || "";
         if (!_dongNm) return false;

         if (_guNm) currentGuNmRef.current = _guNm;
         if (
            dongSelectedFeatRef.current &&
            dongSelectedFeatRef.current !== feat
         ) {
            dongSelectedFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
         }
         dongSearchFeatsRef.current.forEach((f) => {
            if (f !== feat) f.setStyle(DONG_STYLE_DEFAULT);
         });
         dongSearchFeatsRef.current = [];
         if (dongHoverFeatRef.current && dongHoverFeatRef.current !== feat) {
            dongHoverFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
         }
         const prevAdmCd =
            dongSelectedFeatRef.current?.getProperties?.()?.adm_cd || "";
         const isSameDong =
            prevAdmCd === _admCd && allStoresRef.current.length > 0;

         feat.setStyle(DONG_STYLE_SELECTED);
         dongSelectedFeatRef.current = feat;
         dongHoverFeatRef.current = feat;
         const _mode = dongMode;

         if (!isSameDong && _admCd) {
            clearMarkers();
            setNearbyCount(null);
            const _url = `${FASTAPI_URL}/map/stores-by-dong?adm_cd=${_admCd}`;
            console.log("[stores-by-dong] 요청:", _url);
            fetch(_url, { headers: _mapHeaders })
               .then((r) => r.json())
               .then((d) => {
                  const stores = d.stores || [];
                  console.log(
                     `[stores-by-dong] 응답: count=${stores.length}, adm_cd=${_admCd}`,
                  );
                  allStoresRef.current = stores;
                  setNearbyCount(stores.length);
                  const counts = {};
                  stores.forEach((s) => {
                     counts[s.CAT_CD || "기타"] =
                        (counts[s.CAT_CD || "기타"] || 0) + 1;
                  });
                  setCatCounts(counts);
                  drawMarkers(stores, visibleCats);
               })
               .catch((err) => console.error("[stores-by-dong] 오류:", err));
         }
         if (_mode === "none") return true;
         await fetchDongPanelRef.current(
            _admCd,
            _dongNm,
            _guNm,
            _admNm,
            _mode,
            selectedQtr,
         );
         handleWmsClick(map, e.coordinate).then((wmsResult) => {
            if (wmsResult) {
               setWmsPopup(wmsResult.parsed);
               setLandValue(wmsResult.landValue || null);
               if (!wmsResult.landValue && wmsResult.parsed.pnu) {
                  fetch(
                     `${REALESTATE_URL}/realestate/land-value?pnu=${encodeURIComponent(wmsResult.parsed.pnu)}`,
                     { headers: _mapHeaders },
                  )
                     .then((r) => r.json())
                     .then((d) => {
                        if (d.data?.length) setLandValue(d.data);
                     })
                     .catch((err) =>
                        console.error("[공시지가 조회 실패]", err),
                     );
               }
            }
         });
         return true;
      },
      [dongMode, visibleCats, selectedQtr],
   ); // eslint-disable-line react-hooks/exhaustive-deps

   // ── 클릭 최상위 조정자 ──────────────────────────────────────────────
   const clickHandler = useCallback(
      async (e) => {
         const map = mapInstance.current;
         if (!map) return;
         if (await handleMarkerClick(e)) return;
         if (await handlePolygonClick(e)) return;

         // ── 3순위: WMS 공시지가 클릭 ──────────────────────────────
         const wmsResult = await handleWmsClick(map, e.coordinate);
         if (wmsResult) {
            setPopup(null);
            setWmsPopup(wmsResult.parsed);
            setLandValue(wmsResult.landValue || null);
            setKakaoDetail(null);
            setLandmarkPopup(null);
            setClusterPopup(null);
            if (wmsResult.parsed.sigg)
               currentGuNmRef.current = wmsResult.parsed.sigg;
            if (!wmsResult.landValue && wmsResult.parsed.pnu) {
               fetch(
                  `${REALESTATE_URL}/realestate/land-value?pnu=${encodeURIComponent(wmsResult.parsed.pnu)}`,
                  { headers: _mapHeaders },
               )
                  .then((r) => r.json())
                  .then((d) => {
                     if (d.data?.length) setLandValue(d.data);
                  })
                  .catch((err) => console.error("[공시지가 조회 실패]", err));
            }
            return;
         }
         setWmsPopup(null);

         const feature = map.forEachFeatureAtPixel(e.pixel, (f) => f, {
            hitTolerance: 6,
            layerFilter: (l) => l !== dongBoundaryLayerRef.current,
         });
         if (feature?.get("lmData")) {
            selectLandmark(feature);
            setLandmarkPopup(feature.get("lmData"));
            setPopup(null);
            setKakaoDetail(null);
         }
         // 빈 영역 클릭 시 아무것도 안 함 (폴리곤 선택으로만 상가 검색)
      },
      [handleMarkerClick, handlePolygonClick],
   ); // eslint-disable-line react-hooks/exhaustive-deps

   // ── 지도 초기화 + pointermove 등록 (마운트 1회) ────────────────────
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

      let _lastMove = 0;
      const moveHandler = (e) => {
         if (Date.now() - _lastMove < 50) return;
         _lastMove = Date.now();
         const [lng, lat] = toLonLat(e.coordinate);
         setCoords({ lat: lat.toFixed(6), lng: lng.toFixed(6) });

         const bLayer = dongBoundaryLayerRef.current;
         if (!bLayer?.getSource?.()?.getFeatures) return;

         const feat = map.forEachFeatureAtPixel(e.pixel, (f) => f, {
            layerFilter: (l) => l === bLayer,
            hitTolerance: 4,
         });

         if (feat === dongHoverFeatRef.current) {
            if (feat) return;
         }
         if (
            dongHoverFeatRef.current &&
            dongHoverFeatRef.current !== dongSelectedFeatRef.current &&
            !dongSearchFeatsRef.current.includes(dongHoverFeatRef.current)
         ) {
            dongHoverFeatRef.current.setStyle(DONG_STYLE_DEFAULT);
         }

         if (feat) {
            // 분석 하이라이트(SELECTED) 폴리곤은 hover 스타일로 덮어쓰지 않음
            if (!dongSearchFeatsRef.current.includes(feat)) {
               feat.setStyle(DONG_STYLE_HOVER);
            }
            dongHoverFeatRef.current = feat;
            map.getTargetElement().style.cursor = "pointer";

            const p = feat.getProperties();
            const dongNm = p.adm_nm || p.name || "";
            const guNm = p.sig_kor_nm || p.sig_nm || p.sgg_nm || "";
            if (guNm) currentGuNmRef.current = guNm;

            if (dongNm !== dongHoverNameRef.current) {
               dongHoverNameRef.current = dongNm;
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
         }
      };

      map.on("pointermove", moveHandler);
      return () => {
         map.un("pointermove", moveHandler);
         if (map.getTargetElement()) map.getTargetElement().style.cursor = "";
      };
   }, []); // eslint-disable-line react-hooks/exhaustive-deps

   // ── click 이벤트 등록 (clickHandler 변경 시 재등록) ───────────────
   useEffect(() => {
      const map = mapInstance.current;
      if (!map) return;
      map.on("click", clickHandler);
      return () => map.un("click", clickHandler);
   }, [clickHandler]);

   // ── JSX 렌더 ───────────────────────────────────────────────────
   return (
      <div className="mv-root">
         <CategoryPanel
            visibleCats={visibleCats}
            selectedCatCd={selectedCatCd}
            onCatSelect={(catCd) => {
               setSelectedCatCd(catCd);
               // 동 패널 열려있으면 해당 대분류 소분류 매출 조회 (200ms debounce)
               clearTimeout(catFetchTimerRef.current);
               catFetchTimerRef.current = setTimeout(() => {
                  if (dongPanel?.admCd && catCd) {
                     const qtrParam = selectedQtr
                        ? `&quarter=${encodeURIComponent(selectedQtr)}`
                        : "";
                     fetch(
                        `${REALESTATE_URL}/realestate/sangkwon-svc-by-cat?adm_cd=${encodeURIComponent(dongPanel.admCd)}&cat_cd=${encodeURIComponent(catCd)}${qtrParam}`,
                        { headers: _mapHeaders },
                     )
                        .then((r) => r.json())
                        .then((d) => setSvcData(d.data || []))
                        .catch((e) =>
                           console.error(
                              "[MapView] sangkwon-svc-by-cat 실패:",
                              e,
                           ),
                        );
                  } else if (!catCd && dongPanel?.admCd) {
                     // 전체 선택 시 기존 대분류 기준으로 복원
                     const qtrParam = selectedQtr
                        ? `&quarter=${encodeURIComponent(selectedQtr)}`
                        : "";
                     fetch(
                        `${REALESTATE_URL}/realestate/sangkwon-svc?adm_cd=${encodeURIComponent(dongPanel.admCd)}${qtrParam}`,
                        { headers: _mapHeaders },
                     )
                        .then((r) => r.json())
                        .then((d) => setSvcData(d.data || []))
                        .catch((e) =>
                           console.error(
                              "[MapView] sangkwon-svc 전체 복원 실패:",
                              e,
                           ),
                        );
                  }
               }, 200);
            }}
            onToggle={handleToggleCat}
            onShowAll={handleShowAll}
            onHideAll={handleHideAll}
            totalCount={nearbyCount}
            catCounts={catCounts}
            onSearch={handleSearch}
         />
         <div ref={mapRef} className="mv-map" />
         <MapControls
            nearbyCount={nearbyCount}
            loading={loading}
            dongMode={dongMode}
            onDongMode={handleDongMode}
            dongLoading={dongLoading}
            currentGuNm={currentGuNmRef.current}
            storeSearchOn={storeSearchOn}
            onStoreSearchToggle={() => {
               const next = !storeSearchOn;
               setStoreSearchOn(next);
               if (!next) {
                  clearMarkers();
                  setNearbyCount(null);
               }
            }}
            onStoreSearch={() => {
               const feat = dongSelectedFeatRef.current;
               if (!feat) {
                  alert("먼저 폴리곤(동)을 클릭해서 선택해주세요.");
                  return;
               }
               const admCd = (feat.getProperties().adm_cd || "").trim();
               if (!admCd) return;
               setLoading(true);
               clearMarkers();
               setNearbyCount(null);
               fetch(`${FASTAPI_URL}/map/stores-by-dong?adm_cd=${admCd}`, {
                  headers: _mapHeaders,
               })
                  .then((r) => r.json())
                  .then((d) => {
                     const stores = d.stores || [];
                     allStoresRef.current = stores;
                     setNearbyCount(stores.length);
                     const counts = {};
                     stores.forEach((s) => {
                        counts[s.CAT_CD || "기타"] =
                           (counts[s.CAT_CD || "기타"] || 0) + 1;
                     });
                     setCatCounts(counts);
                     drawMarkers(stores, visibleCats);
                  })
                  .catch((e) =>
                     console.error(
                        "[MapView] onStoreSearch stores-by-dong 실패:",
                        e,
                     ),
                  )
                  .finally(() => setLoading(false));
            }}
         />
         <div className="mv-top-right-controls">
            <a href="/user" className="mv-nav-btn">
               ← 상담
            </a>
            <a href="/features" className="mv-nav-btn">
               기능
            </a>
            <ThemeToggle />
            <button
               className="mv-layer-btn"
               onClick={() => setShowPanel((p) => !p)}
            >
               🗂️
            </button>
         </div>
         {showPanel && mapInstance.current && (
            <div className="mv-layer-panel-wrap">
               <Layerpanel
                  map={mapInstance.current}
                  mapReady={mapReady}
                  vworldKey={import.meta.env.VITE_VWORLD_API_KEY}
                  wmsLayerRef={wmsLayerRef}
                  currentZoom={currentZoom}
                  dongModeOn={dongMode}
                  landmarkLayerRef={landmarkLayerRef}
                  festivalLayerRef={festivalLayerRef}
                  schoolLayerRef={schoolLayerRef}
                  landmarkLoaded={landmarkLoaded}
                  festivalLoaded={festivalLoaded}
                  schoolLoaded={schoolLoaded}
               />
            </div>
         )}
         <WmsPopup
            wmsPopup={wmsPopup}
            landValue={landValue}
            onBack={
               prevStorePopupRef.current
                  ? () => {
                       const prev = prevStorePopupRef.current;
                       setWmsPopup(null);
                       setLandValue(null);
                       setPopup(prev.popup);
                       setKakaoDetail(prev.kakaoDetail);
                       lastClusterStoresRef.current =
                          prev.clusterStores || null;
                       prevStorePopupRef.current = null;
                    }
                  : null
            }
            onClose={() => {
               setWmsPopup(null);
               prevStorePopupRef.current = null;
            }}
         />
         {/* 클러스터 팝업 */}
         <StorePopup
            hasDongPanel={!!dongPanel}
            popup={popup}
            kakaoDetail={kakaoDetail}
            loadingDetail={loadingDetail}
            nearbyStores={buildingStores}
            onStoreSelect={(s) => {
               // 모든 팝업 닫고 해당 상가로 이동
               setClusterPopup(null);
               setWmsPopup(null);
               setLandmarkPopup(null);
               lastClusterStoresRef.current = null;
               setPopup(s);
               setKakaoDetail(null);
               setBuildingStores([]);
               setLoadingDetail(true);
               // 해당 위치로 지도 이동
               if (s.LNG && s.LAT) {
                  const map = mapInstance.current;
                  if (map) {
                     map.getView().animate({
                        center: fromLonLat([
                           parseFloat(s.LNG),
                           parseFloat(s.LAT),
                        ]),
                        zoom: Math.max(map.getView().getZoom() || 17, 17),
                        duration: 500,
                     });
                  }
               }
               fetchKakaoDetail(s.STORE_NM, s.ROAD_ADDR).then((d) => {
                  setKakaoDetail(d);
                  setLoadingDetail(false);
               });
               // 건물 상가 조회
               if (s.ROAD_ADDR) {
                  fetch(
                     `${FASTAPI_URL}/map/stores-by-building?road_addr=${encodeURIComponent(s.ROAD_ADDR)}&store_nm=${encodeURIComponent(s.STORE_NM || "")}&exclude_id=${encodeURIComponent(s.STORE_ID || "")}`,
                     { headers: _mapHeaders },
                  )
                     .then((r) => r.json())
                     .then((d) => setBuildingStores(d.stores || []))
                     .catch(() => setBuildingStores([]));
               }
            }}
            clusterStores={clusterPopup?.stores || lastClusterStoresRef.current}
            onLandValue={() => {
               if (!popup?.LNG || !popup?.LAT) return;
               // 모든 팝업 닫기
               prevStorePopupRef.current = {
                  popup,
                  kakaoDetail,
                  clusterStores: lastClusterStoresRef.current,
               };
               setPopup(null);
               setKakaoDetail(null);
               setLandmarkPopup(null);
               setClusterPopup(null);
               setBuildingStores([]);
               lastClusterStoresRef.current = null;
               // 좌표 → PNU 조회 → 공시지가 표시
               const lng = parseFloat(popup.LNG);
               const lat = parseFloat(popup.LAT);
               const addr = popup.ROAD_ADDR || "";
               // 1단계: 백엔드 /map/pnu-by-coord 로 좌표 → PNU 취득
               fetch(`${FASTAPI_URL}/map/pnu-by-coord?lng=${lng}&lat=${lat}`, {
                  headers: _mapHeaders,
               })
                  .then((r) => r.json())
                  .then((d) => {
                     const pnu = d.pnu || "";
                     setWmsPopup({
                        type: "cadastral",
                        pnu,
                        addr,
                        sido: popup.SIDO_NM,
                        sigg: popup.SGG_NM,
                        dong: popup.ADM_NM,
                     });
                     // 2단계: PNU 있으면 백엔드 공시지가 이력 조회
                     if (pnu) {
                        fetch(
                           `${REALESTATE_URL}/realestate/land-value?pnu=${encodeURIComponent(pnu)}`,
                           { headers: _mapHeaders },
                        )
                           .then((r) => r.json())
                           .then((lv) => {
                              if (lv.data?.length) setLandValue(lv.data);
                           })
                           .catch((err) =>
                              console.error("[공시지가 조회 실패]", err),
                           );
                     }
                  })
                  .catch(() => {
                     setWmsPopup({ type: "cadastral", pnu: "", addr });
                  });
            }}
            onClusterSelect={(s) => {
               setClusterPopup(null);
               setWmsPopup(null);
               setLandmarkPopup(null);
               setPopup(s);
               setKakaoDetail(null);
               setBuildingStores([]);
               setLoadingDetail(true);
               if (s.LNG && s.LAT) {
                  const map = mapInstance.current;
                  if (map) {
                     map.getView().animate({
                        center: fromLonLat([
                           parseFloat(s.LNG),
                           parseFloat(s.LAT),
                        ]),
                        zoom: Math.max(map.getView().getZoom() || 17, 17),
                        duration: 500,
                     });
                  }
               }
               fetchKakaoDetail(s.STORE_NM, s.ROAD_ADDR).then((d) => {
                  setKakaoDetail(d);
                  setLoadingDetail(false);
               });
               if (s.ROAD_ADDR) {
                  fetch(
                     `${FASTAPI_URL}/map/stores-by-building?road_addr=${encodeURIComponent(s.ROAD_ADDR)}&store_nm=${encodeURIComponent(s.STORE_NM || "")}&exclude_id=${encodeURIComponent(s.STORE_ID || "")}`,
                     { headers: _mapHeaders },
                  )
                     .then((r) => r.json())
                     .then((d) => setBuildingStores(d.stores || []))
                     .catch(() => setBuildingStores([]));
               }
            }}
            onClose={() => {
               setPopup(null);
               setKakaoDetail(null);
               setClusterPopup(null);
               setBuildingStores([]);
               lastClusterStoresRef.current = null;
               selectMarker(null);
            }}
         />
         <DongPanel
            dongPanel={dongPanel}
            onClose={() => {
               setDongPanel(null);
               setSvcData([]);
               setSelectedSvc("");
            }}
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
         <LandmarkPopup
            popup={landmarkPopup}
            onClose={() => {
               setLandmarkPopup(null);
               selectLandmark(null);
            }}
         />
         <ChatPanel
            isOpen={chatOpen}
            onToggle={() => setChatOpen((prev) => !prev)}
            mapContext={chatContext}
            onNavigate={handleChatNavigate}
            onHighlightArea={handleHighlightArea}
            onClearContext={() => setChatContext(null)}
            onSearchArea={handleSearch}
         />
         <div className="coord-bar">
            📍 위도: {coords.lat} | 경도: {coords.lng} | 줌: {currentZoom}
         </div>
      </div>
   );
}
