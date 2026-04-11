import { CHECKLIST_ITEMS } from "../../constants/checklistItems";
import * as Collapsible from "@radix-ui/react-collapsible";
import { motion, AnimatePresence } from "motion/react";
import { ChevronRight, MessageSquare } from "lucide-react";

/**
 * 단일 체크리스트 항목 — 아코디언 확장형
 *
 * @param {object}  props
 * @param {string}  props.id
 * @param {boolean} props.checked
 * @param {"auto"|"manual"|null} props.source
 * @param {boolean} props.expanded
 * @param {(id: string) => void} props.onToggle
 * @param {(id: string) => void} props.onToggleExpand
 * @param {(question: string) => void} [props.onAskQuestion]
 */
export default function ChecklistItem({
  id,
  checked,
  source,
  expanded,
  onToggle,
  onToggleExpand,
  onAskQuestion,
}) {
  const item = CHECKLIST_ITEMS.find((i) => i.id === id);
  if (!item) return null;

  return (
    <Collapsible.Root open={expanded} onOpenChange={() => onToggleExpand(id)}>
      <div
        className="rounded-xl transition-all duration-200 overflow-hidden"
        style={{
          background: checked ? "rgba(16,185,129,0.06)" : "transparent",
          border: `1px solid ${checked ? "rgba(16,185,129,0.2)" : "var(--border)"}`,
        }}
      >
        {/* 헤더 행 */}
        <div className="flex items-start gap-2.5 px-3 py-2.5">
          {/* 체크 토글 버튼 */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggle(id);
            }}
            className="shrink-0 mt-0.5 flex items-center justify-center transition-all duration-200"
            style={{
              width: 18,
              height: 18,
              borderRadius: "50%",
              border: `2px solid ${checked ? "#10b981" : "var(--border)"}`,
              background: checked ? "#10b981" : "transparent",
            }}
            aria-label={`${item.label} ${checked ? "완료" : "미완료"} — 클릭하여 토글`}
          >
            <AnimatePresence>
              {checked && (
                <motion.svg
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                  transition={{ type: "spring", stiffness: 500, damping: 25 }}
                  width="9"
                  height="7"
                  viewBox="0 0 9 7"
                  fill="none"
                >
                  <path
                    d="M1 3.5L3.5 6L8 1"
                    stroke="white"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </motion.svg>
              )}
            </AnimatePresence>
          </button>

          {/* 라벨 + 설명 (클릭 → 확장) */}
          <Collapsible.Trigger asChild>
            <button type="button" className="flex-1 text-left min-w-0">
              <div className="flex items-center gap-1.5">
                <span
                  className="text-xs font-medium leading-tight"
                  style={{ color: checked ? "var(--foreground)" : "var(--muted-foreground)" }}
                >
                  {item.icon} {item.label}
                </span>

                {/* 대화 완료 배지 */}
                {checked && source === "auto" && (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0 inline-flex items-center gap-0.5"
                    style={{ background: "rgba(8,145,178,0.12)", color: "var(--brand-blue)" }}
                  >
                    <MessageSquare size={8} />
                    대화 완료
                  </span>
                )}
              </div>
              <div
                className="text-[11px] mt-0.5 leading-relaxed"
                style={{ color: "var(--muted-foreground)" }}
              >
                {item.shortDesc}
              </div>
            </button>
          </Collapsible.Trigger>

          {/* 펼침 화살표 */}
          <Collapsible.Trigger asChild>
            <button
              type="button"
              className="shrink-0 mt-0.5 w-5 h-5 flex items-center justify-center rounded transition-colors hover:bg-[var(--muted)]"
              aria-label={expanded ? "접기" : "펼치기"}
            >
              <motion.span
                animate={{ rotate: expanded ? 90 : 0 }}
                transition={{ duration: 0.15 }}
                className="flex items-center justify-center"
              >
                <ChevronRight size={12} style={{ color: "var(--muted-foreground)" }} />
              </motion.span>
            </button>
          </Collapsible.Trigger>
        </div>

        {/* 확장 콘텐츠 */}
        <Collapsible.Content asChild forceMount>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div
                  className="mx-2 mb-2 rounded-lg px-3 py-3 flex flex-col gap-2.5"
                  style={{
                    background: "var(--glass-bg, rgba(255,255,255,0.03))",
                    borderLeft: `2px solid ${item.color}`,
                  }}
                >
                  {/* 상세 설명 */}
                  <p className="text-[11px] leading-relaxed" style={{ color: "var(--foreground)" }}>
                    {item.detail}
                  </p>

                  {/* 왜 중요한가 */}
                  <div
                    className="text-[11px] leading-relaxed px-2.5 py-2 rounded-md"
                    style={{ background: `${item.color}10`, color: "var(--foreground)" }}
                  >
                    <span style={{ color: item.color }}>💡</span> {item.whyItMatters}
                  </div>

                  {/* 준비 단계 */}
                  {item.subSteps?.length > 0 && (
                    <div>
                      <div
                        className="text-[10px] font-semibold mb-1"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        준비 단계
                      </div>
                      <ul className="flex flex-col gap-1">
                        {item.subSteps.map((step, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-1.5 text-[11px] leading-relaxed"
                            style={{ color: "var(--foreground)" }}
                          >
                            <span
                              className="shrink-0 mt-1 w-1 h-1 rounded-full"
                              style={{ background: item.color }}
                            />
                            {step}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* AI에게 물어보기 */}
                  {item.suggestedQuestions?.length > 0 && onAskQuestion && (
                    <div>
                      <div
                        className="text-[10px] font-semibold mb-1 flex items-center gap-1"
                        style={{ color: "var(--muted-foreground)" }}
                      >
                        <MessageSquare size={10} />
                        AI에게 물어보기
                      </div>
                      <div className="flex flex-col gap-1">
                        {item.suggestedQuestions.map((q) => (
                          <button
                            key={q}
                            type="button"
                            onClick={() => onAskQuestion(q)}
                            className="text-left text-[11px] px-2.5 py-1.5 rounded-lg leading-relaxed transition-colors duration-150"
                            style={{
                              background: "var(--glass-bg, rgba(255,255,255,0.03))",
                              color: "var(--foreground)",
                              borderLeft: `2px solid transparent`,
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.borderLeftColor = item.color;
                              e.currentTarget.style.background = `${item.color}12`;
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.borderLeftColor = "transparent";
                              e.currentTarget.style.background =
                                "var(--glass-bg, rgba(255,255,255,0.03))";
                            }}
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Collapsible.Content>
      </div>
    </Collapsible.Root>
  );
}
