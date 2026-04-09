// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\panel\CategoryPanel.jsx
// 공식 프론트 위치: frontend\src\components\map\panel\CategoryPanel.jsx

import { useState, useEffect } from "react";
import { CATEGORIES } from "../../../constants/categories";

export default function CategoryPanel({
   visibleCats,
   onToggle,
   onShowAll,
   onHideAll,
   catCounts,
   onSearch,
   selectedCatCd,
   onCatSelect,
}) {
   const [isMobile, setIsMobile] = useState(
      typeof window !== "undefined" && window.innerWidth <= 640,
   );
   useEffect(() => {
      const handler = () => setIsMobile(window.innerWidth <= 640);
      window.addEventListener("resize", handler);
      return () => window.removeEventListener("resize", handler);
   }, []);
   const [collapsed, setCollapsed] = useState(
      typeof window !== "undefined" && window.innerWidth <= 640,
   );
   const [searchQuery, setSearchQuery] = useState("");

   const handleSearch = () => {
      if (searchQuery.trim()) onSearch?.(searchQuery.trim());
   };

   return (
      <div
         style={{
            ...S.sidebar,
            width: collapsed ? 48 : isMobile ? "min(240px, 80vw)" : 240,
            position: isMobile && !collapsed ? "absolute" : "relative",
            zIndex: isMobile && !collapsed ? 300 : 200,
         }}
      >
         {/* ── 헤더 ──────────────────────────────────────────── */}
         <div style={S.header}>
            {!collapsed && <span style={S.headerTitle}>🏪 상권 분석</span>}
            <button
               style={S.collapseBtn}
               onClick={() => setCollapsed((v) => !v)}
            >
               {collapsed ? "▶" : "◀"}
            </button>
         </div>

         {!collapsed && (
            <>
               {/* ── 구/동 검색 ────────────────────────────── */}
               <div style={S.searchBox}>
                  <input
                     type="text"
                     placeholder="행정동/법정동 검색..."
                     value={searchQuery}
                     autoComplete="off"
                     onChange={(e) => setSearchQuery(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                     style={S.searchInput}
                  />
                  <button style={S.searchBtn} onClick={handleSearch}>
                     🔍
                  </button>
               </div>

               {/* ── Hide all / Show all ───────────────────── */}
               <div style={S.allBtns}>
                  <button style={S.hideAllBtn} onClick={onHideAll}>
                     Hide all
                  </button>
                  <button style={S.showAllBtn} onClick={onShowAll}>
                     Show all
                  </button>
               </div>

               <div style={S.divider} />

               {/* ── 카테고리 목록 (스크롤) ────────────────── */}
               <div style={S.catList}>
                  {CATEGORIES.map((cat) => {
                     const isOn = visibleCats.has(cat.key);
                     const count = catCounts?.[cat.key] || 0;
                     return (
                        <div
                           key={cat.label || cat.key}
                           style={{
                              ...S.catRow,
                              background:
                                 selectedCatCd === cat.key
                                    ? `${cat.color}18`
                                    : "transparent",
                              border:
                                 selectedCatCd === cat.key
                                    ? `1px solid ${cat.color}`
                                    : "1px solid transparent",
                           }}
                        >
                           <div style={S.catLeft}>
                              <div
                                 style={{
                                    ...S.catDot,
                                    background: isOn ? cat.color : "#e5e7eb",
                                 }}
                              >
                                 <span style={{ fontSize: 12 }}>
                                    {cat.icon}
                                 </span>
                              </div>
                              <span
                                 onClick={() =>
                                    onCatSelect?.(
                                       selectedCatCd === cat.key ? "" : cat.key,
                                    )
                                 }
                                 style={{
                                    ...S.catName,
                                    color: isOn
                                       ? "var(--foreground)"
                                       : "var(--muted-foreground)",
                                    cursor: "pointer",
                                    textDecoration:
                                       selectedCatCd === cat.key
                                          ? "underline"
                                          : "none",
                                 }}
                              >
                                 {cat.label || cat.key}
                                 {selectedCatCd === cat.key && " 📊"}
                              </span>
                              {count > 0 && (
                                 <span
                                    style={{
                                       ...S.countChip,
                                       background: isOn
                                          ? cat.bg
                                          : "var(--secondary)",
                                       color: isOn
                                          ? cat.color
                                          : "var(--muted-foreground)",
                                       border: `1px solid ${isOn ? cat.color : "var(--border)"}`,
                                    }}
                                 >
                                    {count}
                                 </span>
                              )}
                           </div>
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
      background: "linear-gradient(160deg, #f0fdfa 0%, #e0f2fe 100%)",
      borderRight: "1px solid rgba(8,145,178,0.15)",
      borderRadius: "0 16px 16px 0",
      boxShadow: "2px 0 16px rgba(8,145,178,0.10)",
      zIndex: 200,
      display: "flex",
      flexDirection: "column",
      transition: "width 0.2s ease",
      overflow: "hidden",
      isolation: "isolate",
      flexShrink: 0,
      minWidth: 0,
   },
   header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "14px 12px 10px",
      borderBottom: "1px solid rgba(8,145,178,0.12)",
      flexShrink: 0,
      background: "rgba(255,255,255,0.6)",
      backdropFilter: "blur(8px)",
   },
   headerTitle: {
      fontSize: 13,
      fontWeight: 700,
      color: "#0891B2",
   },
   collapseBtn: {
      background: "transparent",
      border: "none",
      cursor: "pointer",
      fontSize: 12,
      color: "#0891B2",
      padding: "2px 4px",
      marginLeft: "auto",
   },
   searchBox: {
      display: "flex",
      gap: 4,
      padding: "10px 12px 0",
      flexShrink: 0,
      position: "relative",
      zIndex: 1,
   },
   searchInput: {
      flex: 1,
      padding: "6px 10px",
      border: "1px solid rgba(8,145,178,0.25)",
      borderRadius: 20,
      fontSize: 12,
      outline: "none",
      background: "rgba(255,255,255,0.85)",
      color: "var(--foreground)",
      minWidth: 0,
      boxSizing: "border-box",
   },
   searchBtn: {
      padding: "6px 10px",
      background: "#0891B2",
      border: "none",
      borderRadius: 20,
      cursor: "pointer",
      fontSize: 13,
      color: "#fff",
      flexShrink: 0,
   },
   totalBadge: {
      margin: "10px 12px 0",
      padding: "7px 10px",
      background: "rgba(8,145,178,0.10)",
      borderRadius: 20,
      fontSize: 12,
      color: "#0891B2",
      textAlign: "center",
      fontWeight: 500,
   },
   allBtns: { display: "flex", gap: 6, padding: "10px 12px 0" },
   hideAllBtn: {
      flex: 1,
      padding: "6px 0",
      background: "rgba(255,255,255,0.8)",
      border: "1px solid rgba(8,145,178,0.2)",
      borderRadius: 20,
      fontSize: 11,
      fontWeight: 600,
      color: "#555",
      cursor: "pointer",
   },
   showAllBtn: {
      flex: 1,
      padding: "6px 0",
      background: "#0891B2",
      border: "none",
      borderRadius: 20,
      fontSize: 11,
      fontWeight: 600,
      color: "#fff",
      cursor: "pointer",
   },
   divider: {
      height: 1,
      background: "rgba(8,145,178,0.12)",
      margin: "10px 0 4px",
      flexShrink: 0,
   },
   catList: {
      overflowY: "scroll",
      height: 0,
      flex: "1 1 0",
      padding: "0 8px 16px",
      scrollbarWidth: "thin",
      scrollbarColor: "rgba(8,145,178,0.2) transparent",
   },
   catRow: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "6px 6px",
      borderRadius: 10,
      cursor: "pointer",
      transition: "background 0.1s",
      marginBottom: 2,
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
      borderRadius: 20,
      flexShrink: 0,
      transition: "all 0.2s",
   },
   toggleBtn: {
      border: "none",
      borderRadius: 20,
      padding: "3px 10px",
      fontSize: 10,
      fontWeight: 700,
      cursor: "pointer",
      flexShrink: 0,
      transition: "all 0.2s",
   },
};
