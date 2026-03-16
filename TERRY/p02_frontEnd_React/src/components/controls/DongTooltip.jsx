// components/DongTooltip.jsx

// ── 메인 컴포넌트: 행정동 호버 시 툴팁 ──────────────────────
export default function DongTooltip({ tooltip, mode }) {
   if (!tooltip || mode === "none") return null;

   return (
      <div style={{
         position: "absolute",
         left: tooltip.x + 14,
         top:  tooltip.y - 10,
         zIndex: 500,
         pointerEvents: "none",
         background: "#fff",
         border: "1px solid #e5e7eb",
         borderRadius: 10,
         padding: "8px 12px",
         boxShadow: "0 4px 16px rgba(0,0,0,0.13)",
         minWidth: 140,
         maxWidth: 200,
      }}>
         <div style={{ fontSize: 13, fontWeight: 700, color: "#111", marginBottom: 2 }}>
            {tooltip.dongNm}
         </div>
         <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>
            {tooltip.guNm}
         </div>

         {mode === "sales" && (
            tooltip.loading
               ? <div style={{ fontSize: 11, color: "#aaa" }}>매출 조회 중...</div>
               : tooltip.sales
                  ? <>
                     <div style={{ fontSize: 11, color: "#059669", fontWeight: 700 }}>
                        💰 {tooltip.sales.sales
                           ? `${(tooltip.sales.sales / 1e8).toFixed(1)}억`
                           : "-"}
                     </div>
                     <div style={{ fontSize: 10, color: "#888" }}>
                        점포 {tooltip.sales.selng_co?.toLocaleString() || "-"}개
                     </div>
                  </>
                  : <div style={{ fontSize: 11, color: "#ccc" }}>데이터 없음</div>
         )}

         {mode === "realestate" && (
            <div style={{ fontSize: 11, color: "#2563eb" }}>클릭하여 조회 →</div>
         )}
      </div>
   );
}