import { useEffect } from "react";
import { motion } from "motion/react";
import { X } from "lucide-react";
import StartupChecklist from "./StartupChecklist";

/**
 * 모바일 체크리스트 바텀시트
 *
 * @param {object}   props
 * @param {object}   props.items
 * @param {number}   props.progress
 * @param {Function} props.onToggle
 * @param {Function} props.onAskQuestion
 * @param {Function} props.onClose
 */
export default function ChecklistDrawer({ items, progress, onToggle, onAskQuestion, onClose }) {
  // body 스크롤 잠금
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  return (
    <div className="fixed inset-0 z-[100] lg:hidden">
      {/* 배경 오버레이 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="absolute inset-0"
        style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(2px)" }}
        onClick={onClose}
      />

      {/* 바텀시트 */}
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 350 }}
        drag="y"
        dragConstraints={{ top: 0 }}
        dragElastic={0.1}
        onDragEnd={(_, info) => {
          if (info.offset.y > 100 || info.velocity.y > 300) onClose();
        }}
        className="absolute bottom-0 left-0 right-0 rounded-t-2xl overflow-hidden"
        style={{
          maxHeight: "80vh",
          background: "var(--card)",
          borderTop: "1px solid var(--border)",
          boxShadow: "0 -4px 32px rgba(0,0,0,0.15)",
        }}
      >
        {/* 드래그 핸들 + 닫기 */}
        <div className="flex items-center justify-center pt-3 pb-1 relative">
          <div
            className="w-10 h-1 rounded-full"
            style={{ background: "var(--border)" }}
          />
          <button
            onClick={onClose}
            className="absolute right-3 top-2.5 w-7 h-7 flex items-center justify-center rounded-full transition-colors hover:bg-[var(--muted)]"
            aria-label="닫기"
          >
            <X size={14} style={{ color: "var(--muted-foreground)" }} />
          </button>
        </div>

        {/* 체크리스트 본문 (스크롤) */}
        <div className="overflow-y-auto px-2 pb-6" style={{ maxHeight: "calc(80vh - 3rem)" }}>
          <StartupChecklist
            items={items}
            progress={progress}
            onToggle={onToggle}
            onAskQuestion={(q) => { onClose(); onAskQuestion(q); }}
          />
        </div>
      </motion.div>
    </div>
  );
}
