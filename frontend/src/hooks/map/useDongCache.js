import { useRef } from "react";

// key: `${admCd}:${mode}:${qtr}`
export function useDongCache() {
   const cache = useRef(new Map());

   function has(admCd, mode, qtr = "") {
      return cache.current.has(`${admCd}:${mode}:${qtr}`);
   }
   function get(admCd, mode, qtr = "") {
      return cache.current.get(`${admCd}:${mode}:${qtr}`) ?? null;
   }
   function set(admCd, mode, qtr = "", value) {
      cache.current.set(`${admCd}:${mode}:${qtr}`, value);
   }
   function clear() {
      cache.current.clear();
   }
   // 분기 변경 시 전체 캐시 무효화용 (clear와 동일하지만 의도를 명확히 함)
   function clearAll() {
      cache.current.clear();
   }

   return { has, get, set, clear, clearAll };
}
