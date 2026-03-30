import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { GradeBadge } from "./GradeBadge";
import { CheckCircle2, XCircle } from "lucide-react";

const ITEM_LABELS = {
  C1: "질문 응답성", C2: "완결성", C3: "내부 일관성", C4: "톤 적절성", C5: "할루시네이션 징후",
  F1: "수치 제시", F2: "단위 표기", F3: "가정 전제", F4: "불확실성 언급", F5: "리스크 경고",
  G1: "근거 출처", G2: "법령 인용", G3: "조문 번호", G4: "면책 고지",
  A1: "지역 정보", A2: "업종 정보", A3: "수치 근거", A4: "기간 명시", A5: "출처 안내",
};

const GRADE_LABEL = {
  A: "A 통과",
  B: "B 경고 포함 통과",
  C: "C 반려",
};

export default function SignoffPanel({ status, grade, confidenceNote, retryCount, domain, agentMs, signoffMs, rejectionHistory }) {
  const [open, setOpen] = useState(false);
  const effectiveGrade = grade || (status === "approved" ? "A" : "C");

  if (!rejectionHistory || rejectionHistory.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-3 glass rounded-lg px-3 py-2 text-xs"
      >
        <div className="flex items-center gap-2">
          <GradeBadge grade={effectiveGrade} size="sm" />
          <span className="text-foreground font-medium">{GRADE_LABEL[effectiveGrade] || effectiveGrade} — 1회 통과</span>
          {agentMs != null && (
            <span className="text-muted-foreground ml-auto">에이전트 {agentMs}ms / Sign-off {signoffMs}ms</span>
          )}
        </div>
        {confidenceNote && (
          <div className="mt-1" style={{ color: "var(--grade-b)" }}>{confidenceNote}</div>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-xs glass rounded-lg px-3 py-2 w-full transition-glow hover:shadow-elevated text-left"
      >
        <GradeBadge grade={effectiveGrade} size="sm" />
        <span className="text-muted-foreground">재시도 {retryCount}회</span>
        <span className="text-muted-foreground">거부 이력 {rejectionHistory.length}건</span>
        {agentMs != null && (
          <span className="text-muted-foreground text-[10px]">{agentMs}ms / {signoffMs}ms</span>
        )}
        <span className="ml-auto text-muted-foreground">{open ? "▲" : "▼"}</span>
      </button>

      {confidenceNote && !open && (
        <div className="mt-1 text-xs px-1" style={{ color: "var(--grade-b)" }}>{confidenceNote}</div>
      )}

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 glass rounded-xl overflow-hidden"
          >
            {confidenceNote && (
              <div className="px-4 py-2 text-xs border-b border-[var(--border)]" style={{ color: "var(--grade-b)" }}>
                <span className="font-semibold">주의: </span>{confidenceNote}
              </div>
            )}
            {rejectionHistory.map((attempt, idx) => (
              <AttemptRow key={attempt.attempt} attempt={attempt} idx={idx} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function AttemptRow({ attempt, idx }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const passed   = attempt.passed   || [];
  const issues   = attempt.issues   || [];
  const warnings = attempt.warnings || [];

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: idx * 0.05 }}
      className="px-4 py-3 text-xs border-b border-[var(--border)] last:border-b-0"
    >
      <button
        onClick={() => setDetailOpen((v) => !v)}
        className="w-full flex items-center gap-2 text-left"
      >
        <span className="font-semibold text-foreground">시도 {attempt.attempt}</span>
        <div className="flex gap-1 flex-wrap">
          {passed.map((code) => (
            <span key={code} className="px-1.5 py-0.5 rounded font-mono" style={{ background: "rgba(16,185,129,0.15)", color: "var(--grade-a)" }}>
              {code}
            </span>
          ))}
          {warnings.map((w) => (
            <span key={w.code} className="px-1.5 py-0.5 rounded font-mono" style={{ background: "rgba(234,179,8,0.15)", color: "var(--grade-b)" }}>
              {w.code}
            </span>
          ))}
          {issues.map((iss) => (
            <span key={iss.code} className="px-1.5 py-0.5 rounded font-mono" style={{ background: "rgba(239,68,68,0.15)", color: "var(--grade-c)" }}>
              {iss.code}
            </span>
          ))}
        </div>
        <span className="ml-auto text-muted-foreground">{detailOpen ? "▲" : "▼"}</span>
      </button>

      <AnimatePresence>
        {detailOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 space-y-2"
          >
            {warnings.map((w) => (
              <div key={w.code} className="rounded-lg px-3 py-2 border" style={{ background: "rgba(234,179,8,0.08)", borderColor: "rgba(234,179,8,0.2)" }}>
                <div className="font-semibold mb-0.5" style={{ color: "var(--grade-b)" }}>
                  {w.code} — {ITEM_LABELS[w.code] || w.code} <span className="font-normal opacity-70">(경고)</span>
                </div>
                <div className="text-foreground opacity-80">{w.reason}</div>
              </div>
            ))}
            {issues.map((iss) => (
              <div key={iss.code} className="rounded-lg px-3 py-2 border" style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.2)" }}>
                <div className="font-semibold mb-0.5" style={{ color: "var(--grade-c)" }}>
                  {iss.code} — {ITEM_LABELS[iss.code] || iss.code} <span className="font-normal opacity-70">(반려)</span>
                </div>
                <div className="text-foreground opacity-80">{iss.reason}</div>
              </div>
            ))}
            {attempt.retry_prompt && (
              <div className="glass rounded-lg px-3 py-2">
                <div className="font-semibold text-muted-foreground mb-1">수정 지시문</div>
                <div className="text-foreground opacity-80 whitespace-pre-wrap leading-relaxed">
                  {attempt.retry_prompt}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
