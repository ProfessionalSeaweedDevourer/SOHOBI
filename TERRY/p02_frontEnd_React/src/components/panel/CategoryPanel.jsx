// 위치: src/components/panel/CategoryPanel.jsx
import { useState } from "react";
import { CATEGORIES } from "../../constants/categories";

export default function CategoryPanel({
   visibleCats,
   onToggle,
   onShowAll,
   onHideAll,
   totalCount,
   catCounts,
}) {
   const [collapsed, setCollapsed] = useState(false);

   return (
      <div style={{ ...S.sidebar, width: collapsed ? 48 : 220 }}>
         {/* 헤더 */}
         <div style={S.header}>
            {!collapsed && <span style={S.headerTitle}>🗺️ 카테고리</span>}
            <button
               style={S.collapseBtn}
               onClick={() => setCollapsed((v) => !v)}
            >
               {collapsed ? "▶" : "◀"}
            </button>
         </div>

         {!collapsed && (
            <>
               {/* 전체 통계 */}
               {totalCount !== null && (
                  <div style={S.totalBadge}>
                     반경 500m 내 총 <b>{totalCount}</b>건
                  </div>
               )}

               {/* Hide all / Show all */}
               <div style={S.allBtns}>
                  <button style={S.hideAllBtn} onClick={onHideAll}>
                     Hide all
                  </button>
                  <button style={S.showAllBtn} onClick={onShowAll}>
                     Show all
                  </button>
               </div>

               <div style={S.divider} />

               {/* 카테고리 목록 */}
               <div style={S.catList}>
                  {CATEGORIES.map((cat) => {
                     const isOn = visibleCats.has(cat.key);
                     const count = catCounts?.[cat.key] || 0;
                     return (
                        <div key={cat.key} style={S.catRow}>
                           {/* 아이콘 + 이름 */}
                           <div style={S.catLeft}>
                              <div
                                 style={{
                                    ...S.catDot,
                                    background: isOn ? cat.color : "#ccc",
                                 }}
                              >
                                 <span style={{ fontSize: 12 }}>
                                    {cat.icon}
                                 </span>
                              </div>
                              <span
                                 style={{
                                    ...S.catName,
                                    color: isOn ? "#111" : "#aaa",
                                 }}
                              >
                                 {cat.key}
                              </span>
                              {count > 0 && (
                                 <span
                                    style={{
                                       ...S.countChip,
                                       background: isOn ? cat.bg : "#f5f5f5",
                                       color: isOn ? cat.color : "#aaa",
                                       border: `1px solid ${isOn ? cat.color : "#ddd"}`,
                                    }}
                                 >
                                    {count}
                                 </span>
                              )}
                           </div>

                           {/* ON/OFF 토글 */}
                           <button
                              style={{
                                 ...S.toggleBtn,
                                 background: isOn ? cat.color : "#e5e7eb",
                                 color: isOn ? "#fff" : "#999",
                              }}
                              onClick={() => onToggle(cat.key)}
                           >
                              {isOn ? "ON" : "OFF"}
                           </button>
                        </div>
                     );
                  })}
               </div>
            </>
         )}
      </div>
   );
}

const S = {
   sidebar: {
      position: "relative",
      height: "100%",
      background: "rgba(255,255,255,0.97)",
      borderRight: "1px solid #e5e7eb",
      boxShadow: "2px 0 12px rgba(0,0,0,0.08)",
      zIndex: 200,
      display: "flex",
      flexDirection: "column",
      transition: "width 0.2s ease",
      overflow: "hidden",
   },
   header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "14px 12px 10px",
      borderBottom: "1px solid #f0f0f0",
      flexShrink: 0,
   },
   headerTitle: {
      fontSize: 13,
      fontWeight: 700,
      color: "#111",
   },
   collapseBtn: {
      background: "transparent",
      border: "none",
      cursor: "pointer",
      fontSize: 12,
      color: "#888",
      padding: "2px 4px",
      marginLeft: "auto",
   },
   totalBadge: {
      margin: "10px 12px 0",
      padding: "7px 10px",
      background: "#EFF6FF",
      borderRadius: 8,
      fontSize: 12,
      color: "#1971C2",
      textAlign: "center",
   },
   allBtns: {
      display: "flex",
      gap: 6,
      padding: "10px 12px 0",
   },
   hideAllBtn: {
      flex: 1,
      padding: "5px 0",
      background: "#f5f5f5",
      border: "1px solid #ddd",
      borderRadius: 6,
      fontSize: 11,
      fontWeight: 600,
      color: "#666",
      cursor: "pointer",
   },
   showAllBtn: {
      flex: 1,
      padding: "5px 0",
      background: "#2563EB",
      border: "none",
      borderRadius: 6,
      fontSize: 11,
      fontWeight: 600,
      color: "#fff",
      cursor: "pointer",
   },
   divider: {
      height: 1,
      background: "#f0f0f0",
      margin: "10px 0 4px",
      flexShrink: 0,
   },
   catList: {
      flex: 1,
      overflowY: "auto",
      padding: "0 8px 16px",
   },
   catRow: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "6px 4px",
      borderRadius: 8,
      cursor: "pointer",
      transition: "background 0.1s",
   },
   catLeft: {
      display: "flex",
      alignItems: "center",
      gap: 7,
      flex: 1,
      minWidth: 0,
   },
   catDot: {
      width: 28,
      height: 28,
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
      transition: "background 0.2s",
   },
   catName: {
      fontSize: 12,
      fontWeight: 600,
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
      transition: "color 0.2s",
   },
   countChip: {
      fontSize: 10,
      fontWeight: 700,
      padding: "1px 6px",
      borderRadius: 10,
      flexShrink: 0,
      transition: "all 0.2s",
   },
   toggleBtn: {
      border: "none",
      borderRadius: 6,
      padding: "3px 8px",
      fontSize: 10,
      fontWeight: 700,
      cursor: "pointer",
      flexShrink: 0,
      transition: "all 0.2s",
   },
};
