import { CHECKLIST_ITEMS } from "../../constants/checklistItems";

/**
 * 단일 체크리스트 항목 버튼
 *
 * @param {object}  props
 * @param {string}  props.id       - item id
 * @param {boolean} props.checked
 * @param {"auto"|"manual"|null} props.source
 * @param {(id: string) => void} props.onToggle
 */
export default function ChecklistItem({ id, checked, source, onToggle }) {
  const item = CHECKLIST_ITEMS.find((i) => i.id === id);
  if (!item) return null;

  return (
    <button
      type="button"
      onClick={() => onToggle(id)}
      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-200 text-left"
      style={{
        background: checked ? "rgba(16,185,129,0.08)" : "transparent",
        border: `1px solid ${checked ? "rgba(16,185,129,0.25)" : "var(--border)"}`,
      }}
      aria-label={`${item.label} ${checked ? "완료" : "미완료"} — 클릭하여 토글`}
    >
      {/* 체크 아이콘 */}
      <span
        className="shrink-0 flex items-center justify-center transition-all duration-200"
        style={{
          width: 18,
          height: 18,
          borderRadius: "50%",
          border: `2px solid ${checked ? "#10b981" : "var(--border)"}`,
          background: checked ? "#10b981" : "transparent",
        }}
      >
        {checked && (
          <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
            <path
              d="M1 3.5L3.5 6L8 1"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </span>

      {/* 아이콘 + 라벨 */}
      <span
        className="text-xs font-medium flex-1 leading-tight"
        style={{ color: checked ? "var(--foreground)" : "var(--muted-foreground)" }}
      >
        {item.icon} {item.label}
      </span>

      {/* 자동 체크 배지 */}
      {checked && source === "auto" && (
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0"
          style={{ background: "rgba(16,185,129,0.15)", color: "#10b981" }}
        >
          자동
        </span>
      )}
    </button>
  );
}
