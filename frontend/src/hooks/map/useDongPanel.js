import { useState, useRef, useEffect } from "react";
import { useDongCache } from "./useDongCache";

const REALESTATE_URL = import.meta.env.VITE_REALESTATE_URL || "";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _mapHeaders = _API_KEY ? { "X-API-Key": _API_KEY } : {};

export function useDongPanel() {
  const dongCache = useDongCache();

  const [dongLoading, setDongLoading] = useState(false);
  const [dongPanel, setDongPanel] = useState(null);
  const dongPanelRef = useRef(null); // selectedQtr useEffect의 stale closure 방지용
  const [quarters, setQuarters] = useState([]);
  const [selectedQtr, setSelectedQtr] = useState("");
  const currentGuNmRef = useRef("");
  const [svcData, setSvcData] = useState([]);

  // ── dongPanel 변경 시 ref 동기화 ───────────────────────────────
  useEffect(() => {
    dongPanelRef.current = dongPanel;
  }, [dongPanel]);

  // ── 분기 목록 초기 로드 ──────────────────────────────────────────
  useEffect(() => {
    fetch(`${REALESTATE_URL}/realestate/sangkwon-quarters`, { headers: _mapHeaders })
      .then((r) => r.json())
      .then((d) => {
        if (d.quarters?.length) {
          const sorted = [...d.quarters].sort((a, b) => b.localeCompare(a));
          setQuarters(sorted);
          setSelectedQtr(sorted[0]); // 최신 분기 기본 선택
        }
      })
      .catch((e) => console.error("[useDongPanel] 분기 목록 로드 실패:", e));
  }, []);

  // ── 분기 변경 시 현재 패널 자동 재조회 ─────────────────────────────
  useEffect(() => {
    // 분기가 바뀌면 구 분기 캐시가 히트되지 않도록 전체 무효화
    dongCache.clearAll();
    const panel = dongPanelRef.current;
    if (!selectedQtr || !panel || panel.mode !== "sales" || !panel.admCd) return;
    const qtrParam = `&quarter=${encodeURIComponent(selectedQtr)}`;
    fetch(
      `${REALESTATE_URL}/realestate/sangkwon?adm_cd=${encodeURIComponent(panel.admCd)}${qtrParam}`,
      { headers: _mapHeaders },
    )
      .then((r) => r.json())
      .then((jj) => {
        if (jj.data)
          setDongPanel((prev) => (prev ? { ...prev, apiData: jj.data, avg: jj.avg } : prev));
      })
      .catch((e) => console.error("[useDongPanel] selectedQtr sangkwon 재조회 실패:", e));
  }, [selectedQtr]); // eslint-disable-line

  // ── 동 패널 데이터 fetch (sales / realestate / store 공통) ─────────
  const fetchDongPanel = async (admCd, dongNm, guNm, admNm, mode, qtr) => {
    // 캐시 히트 시 즉시 반환
    if (dongCache.has(admCd, mode, qtr)) {
      const cached = dongCache.get(admCd, mode, qtr);
      setDongPanel(cached.panel);
      if (cached.svcData !== undefined) setSvcData(cached.svcData);
      return;
    }
    setDongLoading(true);
    try {
      if (mode === "sales") {
        const qtrParam = qtr ? `&quarter=${encodeURIComponent(qtr)}` : "";
        const url = admCd
          ? `${REALESTATE_URL}/realestate/sangkwon?adm_cd=${encodeURIComponent(admCd)}${qtrParam}`
          : `${REALESTATE_URL}/realestate/sangkwon?dong=${encodeURIComponent(dongNm)}&gu=${encodeURIComponent(guNm)}`;
        const jj = await fetch(url, { headers: _mapHeaders }).then((r) => r.json());
        const panel = jj.data
          ? { mode, dongNm, admNm, guNm, admCd, apiData: jj.data, avg: jj.avg }
          : { mode, dongNm, admNm, guNm, apiData: null, empty: true };
        setDongPanel(panel);
        // sangkwon-svc는 fire-and-forget — 패널 표시를 블로킹하지 않음
        if (admCd) {
          fetch(
            `${REALESTATE_URL}/realestate/sangkwon-svc?adm_cd=${encodeURIComponent(admCd)}${qtrParam}`,
            { headers: _mapHeaders },
          )
            .then((r) => r.json())
            .then((sv) => {
              const svcData = sv.data || [];
              setSvcData(svcData);
              dongCache.set(admCd, mode, qtr, { panel, svcData });
            })
            .catch(() => setSvcData([]));
        } else {
          dongCache.set(admCd, mode, qtr, { panel, svcData: [] });
        }
      } else if (mode === "realestate") {
        const jj = await fetch(
          `${REALESTATE_URL}/realestate/seoul-rtms?adm_cd=${encodeURIComponent(admCd)}`,
          { headers: _mapHeaders },
        ).then((r) => r.json());
        if (jj) {
          const panel = { mode, dongNm, admNm, guNm, admCd, apiData: jj };
          setDongPanel(panel);
          dongCache.set(admCd, mode, qtr, { panel });
        }
      } else if (mode === "store") {
        const jj = await fetch(
          `${REALESTATE_URL}/realestate/sangkwon-store?adm_cd=${encodeURIComponent(admCd)}`,
          { headers: _mapHeaders },
        ).then((r) => r.json());
        if (jj) {
          const panel = { mode, dongNm, admNm, guNm, admCd, apiData: jj };
          setDongPanel(panel);
          dongCache.set(admCd, mode, qtr, { panel });
        }
      }
    } catch (err) {
      console.error("[fetchDongPanel] 오류:", err);
    } finally {
      setDongLoading(false);
    }
  };

  return {
    dongLoading,
    dongPanel,
    setDongPanel,
    dongPanelRef,
    quarters,
    selectedQtr,
    setSelectedQtr,
    svcData,
    setSvcData,
    currentGuNmRef,
    fetchDongPanel,
    dongCache,
  };
}
