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

   return { has, get, set, clear };
}
