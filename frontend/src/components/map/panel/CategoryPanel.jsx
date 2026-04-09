import { useState, useEffect } from "react";
import { CATEGORIES } from "../../../constants/categories";
import { Store, ChevronLeft, ChevronRight, Search, BarChart2 } from "lucide-react";
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
      className={`cp-sidebar ${isMobile && !collapsed ? "cp-sidebar--mobile-overlay" : ""}`}
      style={{
        width: collapsed ? 48 : isMobile ? "min(220px, 80vw)" : 220,
        position: isMobile && !collapsed ? "absolute" : "relative",
      }}
    >
      {/* 헤더 */}
      <div className={`cp-header ${collapsed ? "cp-header--collapsed" : ""}`}>
        {!collapsed && (
          <div className="cp-header__left">
            <div className="cp-header__icon">
              <Store size={16} />
            </div>
            <span>상권 분석</span>
          </div>
        )}
        <button
          className="cp-collapse-btn"
          onClick={() => setCollapsed((v) => !v)}
          title={collapsed ? "패널 열기" : "패널 접기"}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {!collapsed && (
        <>
          {/* 검색 */}
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
            <button className="cp-search-btn" onClick={handleSearch} title="검색">
              <Search size={14} />
            </button>
          </div>

          {/* 통계 배지 */}
          {totalCount !== null && (
            <div className="cp-total-badge">
              <BarChart2 size={13} />
              반경 내 총 <b>{totalCount}</b>건
            </div>
          )}

          {/* Hide / Show */}
          <div className="cp-all-btns">
            <button className="cp-hide-all-btn" onClick={onHideAll}>
              Hide all
            </button>
            <button className="cp-show-all-btn" onClick={onShowAll}>
              Show all
            </button>
          </div>

          <div className="cp-divider" />

          {/* 카테고리 목록 */}
          <div className="cp-cat-list">
            {CATEGORIES.map((cat) => {
              const isOn = visibleCats.has(cat.key);
              const count = catCounts?.[cat.key] || 0;
              return (
                <div
                  key={cat.label || cat.key}
                  className="cp-cat-row"
                  style={{
                    background: selectedCatCd === cat.key ? `${cat.color}12` : undefined,
                    borderColor: selectedCatCd === cat.key ? cat.color : undefined,
                  }}
                >
                  <div className="cp-cat-left">
                    <div
                      className="cp-cat-dot"
                      style={{ background: isOn ? `${cat.color}20` : "var(--secondary)" }}
                    >
                      <span style={{ color: isOn ? cat.color : "var(--muted-foreground)" }}>
                        {cat.icon}
                      </span>
                    </div>
                    <span
                      onClick={() => onCatSelect?.(selectedCatCd === cat.key ? "" : cat.key)}
                      className="cp-cat-name"
                      style={{
                        color: isOn ? "var(--foreground)" : "var(--muted-foreground)",
                        textDecoration: selectedCatCd === cat.key ? "underline" : "none",
                      }}
                    >
                      {cat.label || cat.key}
                    </span>
                    {count > 0 && (
                      <span
                        className="cp-count-chip"
                        style={{
                          background: isOn ? `${cat.color}15` : "var(--secondary)",
                          color: isOn ? cat.color : "var(--muted-foreground)",
                          border: `1px solid ${isOn ? `${cat.color}40` : "var(--glass-border)"}`,
                        }}
                      >
                        {count}
                      </span>
                    )}
                  </div>
                  <button
                    className="cp-toggle-btn"
                    style={{
                      background: isOn
                        ? `linear-gradient(135deg, ${cat.color}, ${cat.color}cc)`
                        : "var(--secondary)",
                      color: isOn ? "#fff" : "var(--muted-foreground)",
                      boxShadow: isOn ? `0 2px 6px ${cat.color}30` : "none",
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
