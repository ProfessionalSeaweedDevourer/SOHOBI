/**
 * 창업 준비 진행률 바
 *
 * @param {object} props
 * @param {number} props.progress - 완료된 항목 수 (0~total)
 * @param {number} [props.total]  - 전체 항목 수 (기본값 8)
 */
export default function ChecklistProgress({ progress, total = 8, onClick }) {
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;
  const allDone = progress === total;

  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper className={`px-3 pb-2 w-full${onClick ? " text-left" : ""}`} onClick={onClick}>
      <div className="flex items-center justify-between mb-1.5">
        <span
          className="text-xs font-semibold"
          style={{ color: allDone ? "#10b981" : "var(--foreground)" }}
        >
          {allDone ? "🎉 창업 준비 완료!" : "창업 준비 현황"}
        </span>
        <span className="text-xs font-semibold tabular-nums" style={{ color: "var(--muted-foreground)" }}>
          {progress}/{total}
        </span>
      </div>
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ background: "var(--muted)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: allDone
              ? "#10b981"
              : "linear-gradient(90deg, var(--brand-blue, #0891b2), var(--brand-teal, #14b8a6))",
          }}
        />
      </div>
    </Wrapper>
  );
}
