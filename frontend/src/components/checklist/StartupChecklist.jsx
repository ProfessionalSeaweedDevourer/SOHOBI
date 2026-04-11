import { useState } from "react";
import ChecklistItem from "./ChecklistItem";
import ChecklistProgress from "./ChecklistProgress";
import { CHECKLIST_ITEMS } from "../../constants/checklistItems";
import { motion, AnimatePresence } from "motion/react";

/**
 * 창업 준비 체크리스트 패널
 *
 * @param {object}   props
 * @param {object}   props.items        - {[id]: {checked, source, checked_at}}
 * @param {number}   props.progress     - 완료된 항목 수
 * @param {Function} props.onToggle     - (itemId: string) => void
 * @param {Function} [props.onAskQuestion] - (question: string) => void
 */
export default function StartupChecklist({ items, progress, onToggle, onAskQuestion }) {
  const [collapsed, setCollapsed] = useState(false);
  const [expandedItemId, setExpandedItemId] = useState(() => {
    // 첫 방문 시 첫 항목 자동 펼침
    if (!localStorage.getItem("sohobi_checklist_intro_dismissed")) {
      return CHECKLIST_ITEMS[0]?.id ?? null;
    }
    return null;
  });
  const [showIntro, setShowIntro] = useState(
    () => !localStorage.getItem("sohobi_checklist_intro_dismissed"),
  );

  function handleToggleExpand(id) {
    setExpandedItemId((prev) => (prev === id ? null : id));
  }

  function dismissIntro() {
    localStorage.setItem("sohobi_checklist_intro_dismissed", "1");
    setShowIntro(false);
  }

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
          {/* 온보딩 배너 */}
          <AnimatePresence>
            {showIntro && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div
                  className="rounded-lg px-3 py-2.5 mb-1 text-[11px] leading-relaxed relative"
                  style={{
                    background: "rgba(8,145,178,0.06)",
                    border: "1px solid rgba(8,145,178,0.15)",
                    color: "var(--foreground)",
                  }}
                >
                  <button
                    onClick={dismissIntro}
                    className="absolute top-1.5 right-2 text-muted-foreground hover:text-foreground transition-colors text-xs"
                    aria-label="닫기"
                  >
                    ✕
                  </button>
                  <div className="font-semibold mb-1" style={{ color: "var(--brand-blue)" }}>
                    🧭 창업 준비 가이드
                  </div>
                  <p style={{ color: "var(--muted-foreground)" }}>
                    이 체크리스트는 소상공인 창업의 핵심 8단계를 안내합니다. 필수 사항이 아닌{" "}
                    <strong style={{ color: "var(--foreground)" }}>참고용 가이드</strong>이니,
                    대화하면서 자연스럽게 확인해 보세요.
                  </p>
                  <p className="mt-1" style={{ color: "var(--muted-foreground)" }}>
                    항목을 펼쳐 상세 내용과 추천 질문을 확인할 수 있습니다.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {CHECKLIST_ITEMS.map((item) => (
            <ChecklistItem
              key={item.id}
              id={item.id}
              checked={items[item.id]?.checked ?? false}
              source={items[item.id]?.source ?? null}
              expanded={expandedItemId === item.id}
              onToggle={onToggle}
              onToggleExpand={handleToggleExpand}
              onAskQuestion={onAskQuestion}
            />
          ))}
        </div>
      )}
    </div>
  );
}
