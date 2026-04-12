import { useRef } from "react";

const TTL_MS = 5 * 60 * 1000; // 5분

// key: `${admCd}:${mode}:${qtr}`
export function useDongCache() {
  const cache = useRef(new Map());

  function has(admCd, mode, qtr = "") {
    const entry = cache.current.get(`${admCd}:${mode}:${qtr}`);
    if (!entry) return false;
    if (Date.now() - entry.ts > TTL_MS) {
      cache.current.delete(`${admCd}:${mode}:${qtr}`);
      return false;
    }
    return true;
  }
  function get(admCd, mode, qtr = "") {
    const entry = cache.current.get(`${admCd}:${mode}:${qtr}`);
    if (!entry) return null;
    if (Date.now() - entry.ts > TTL_MS) {
      cache.current.delete(`${admCd}:${mode}:${qtr}`);
      return null;
    }
    return entry.value;
  }
  function set(admCd, mode, qtr = "", value) {
    cache.current.set(`${admCd}:${mode}:${qtr}`, { value, ts: Date.now() });
  }
  function clear() {
    cache.current.clear();
  }
  // 분기 변경 시 해당 분기 키만 삭제
  function clearByQtr(qtr) {
    for (const key of cache.current.keys()) {
      if (key.endsWith(`:${qtr}`)) cache.current.delete(key);
    }
  }
  // 전체 무효화
  function clearAll() {
    cache.current.clear();
  }

  return { has, get, set, clear, clearByQtr, clearAll };
}
