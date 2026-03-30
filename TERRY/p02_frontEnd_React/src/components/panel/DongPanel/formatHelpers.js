// ── 금액 포맷 헬퍼 ─────────────────────────────────────────────
// formatAmt: 원 단위 → 억/만원 (매출 등)
export function formatAmt(v) {
   if (!v || v === 0) return "-";
   if (v >= 1e8) {
      const uk = Math.floor(v / 1e8);
      const man = Math.round((v % 1e8) / 1e4);
      return man > 0 ? `${uk}억 ${man.toLocaleString()}만` : `${uk}억`;
   }
   if (v >= 1e4) return `${Math.round(v / 1e4).toLocaleString()}만`;
   return `${v.toLocaleString()}`;
}

// formatManwon: 만원 단위 → 억/만 (실거래가 등)
export function formatManwon(v) {
   if (!v || v === 0) return "-";
   if (v >= 10000) {
      const uk = Math.floor(v / 10000);
      const man = v % 10000;
      return man > 0 ? `${uk}억 ${man.toLocaleString()}만` : `${uk}억`;
   }
   return `${v.toLocaleString()}만`;
}
