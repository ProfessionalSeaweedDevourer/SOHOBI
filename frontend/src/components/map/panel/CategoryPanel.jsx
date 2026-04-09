// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\panel\CategoryPanel.jsx
// 공식 프론트 위치: frontend\src\components\map\panel\CategoryPanel.jsx

import { useState, useEffect } from "react";
import { CATEGORIES } from "../../../constants/categories";
import "./CategoryPanel.css";

export default function CategoryPanel({
   visibleCats,
   onToggle,
   onShowAll,
   onHideAll,
   totalCount,
   catCounts,
   onSearch,
   selectedCatCd,
   onCatSelect,
}) {
   const [isMobile, setIsMobile] = useState(
      typeof window !== "undefined" && window.innerWidth <= 640
   );
   useEffect(() => {
      const handler = () => setIsMobile(window.innerWidth <= 640);
      window.addEventListener("resize", handler);
      return () => window.removeEventListener("resize", handler);
   }, []);
   const [collapsed, setCollapsed] = useState(
      typeof window !== "undefined" && window.innerWidth <= 640
   ); // 모바일: 기본 접힘
   const [searchQuery, setSearchQuery] = useState("");

   // ── 검색 실행 ────────────────────────────────────────────────
   const handleSearch = () => {
      if (searchQuery.trim()) onSearch?.(searchQuery.trim());
   };

   return (
      <div
         className="cp-sidebar"
         style={{
            width: collapsed ? 48 : (isMobile ? "min(220px, 80vw)" : 220),
            position: isMobile && !collapsed ? "absolute" : "relative",
            zIndex: isMobile && !collapsed ? 300 : 200,
         }}
      >
         {/* ── 헤더 ──────────────────────────────────────────── */}
         <div className="cp-header">
            {!collapsed && <span className="cp-header__title">🏪 상권 분석</span>}
            <button
               className="cp-collapse-btn"
               onClick={() => setCollapsed((v) => !v)}
            >
               {collapsed ? "▶" : "◀"}
            </button>
         </div>

         {!collapsed && (
            <>
               {/* ── 구/동 검색 ────────────────────────────── */}
               <div className="cp-search-box">
                  <input
                     type="text"
                     placeholder="행정동/법정동 검색..."
                     value={searchQuery}
                     autoComplete="off"
                     onChange={(e) => setSearchQuery(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                     className="cp-search-input"
                  />
                  <button className="cp-search-btn" onClick={handleSearch}>
                     🔍
                  </button>
               </div>

               {/* ── 전체 통계 ─────────────────────────────── */}
               {totalCount !== null && (
                  <div className="cp-total-badge">
                     반경 내 총 <b>{totalCount}</b>건
                  </div>
               )}

               {/* ── Hide all / Show all ───────────────────── */}
               <div className="cp-all-btns">
                  <button className="cp-hide-all-btn" onClick={onHideAll}>
                     Hide all
                  </button>
                  <button className="cp-show-all-btn" onClick={onShowAll}>
                     Show all
                  </button>
               </div>

               <div className="cp-divider" />

               {/* ── 카테고리 목록 (스크롤) ────────────────── */}
               <div className="cp-cat-list">
                  {CATEGORIES.map((cat) => {
                     const isOn = visibleCats.has(cat.key);
                     const count = catCounts?.[cat.key] || 0;
                     return (
                        <div
                           key={cat.label || cat.key}
                           className="cp-cat-row"
                           style={{
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
                           <div className="cp-cat-left">
                              <div
                                 className="cp-cat-dot"
                                 style={{
                                    background: isOn ? cat.color : "var(--muted)",
                                 }}
                              >
                                 <span className="cp-cat-icon">
                                    {cat.icon}
                                 </span>
                              </div>
                              <span
                                 onClick={() =>
                                    onCatSelect?.(
                                       selectedCatCd === cat.key ? "" : cat.key,
                                    )
                                 }
                                 className="cp-cat-name"
                                 style={{
                                    color: isOn ? "var(--foreground)" : "var(--muted-foreground)",
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
                                    className="cp-count-chip"
                                    style={{
                                       background: isOn ? cat.bg : "var(--secondary)",
                                       color: isOn ? cat.color : "var(--muted-foreground)",
                                       border: `1px solid ${isOn ? cat.color : "var(--border)"}`,
                                    }}
                                 >
                                    {count}
                                 </span>
                              )}
                           </div>
                           <button
                              className={`cp-toggle-btn ${isOn ? "" : "cp-toggle-btn--off"}`}
                              style={isOn ? { background: cat.color, color: "#fff" } : undefined}
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
