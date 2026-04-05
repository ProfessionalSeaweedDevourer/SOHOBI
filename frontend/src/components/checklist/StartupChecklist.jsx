import { useState } from "react";
import ChecklistItem from "./ChecklistItem";
import ChecklistProgress from "./ChecklistProgress";
import { CHECKLIST_ITEMS } from "../../constants/checklistItems";

/**
 * 창업 준비 체크리스트 패널
 *
 * @param {object}   props
 * @param {object}   props.items    - {[id]: {checked, source, checked_at}}
 * @param {number}   props.progress - 완료된 항목 수
 * @param {Function} props.onToggle - (itemId: string) => void
 */
export default function StartupChecklist({ items, progress, onToggle }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className="rounded-2xl border overflow-hidden"
      style={{
        background: "var(--card)",
        borderColor: "var(--border)",
        boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
      }}
    >
      {/* 헤더 (접기/펼치기) */}
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className="w-full flex items-center gap-2 px-3 pt-3 pb-2 text-left"
      >
        <span className="text-sm font-semibold text-foreground flex-1">📋 창업 체크리스트</span>
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          {collapsed ? "▼" : "▲"}
        </span>
      </button>

      <ChecklistProgress progress={progress} total={CHECKLIST_ITEMS.length} />

      {!collapsed && (
        <div className="px-2 pb-2 flex flex-col gap-1">
          {CHECKLIST_ITEMS.map((item) => (
            <ChecklistItem
              key={item.id}
              id={item.id}
              checked={items[item.id]?.checked ?? false}
              source={items[item.id]?.source ?? null}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}
