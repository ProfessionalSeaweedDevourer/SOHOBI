import { useState } from "react";

const ITEM_LABELS = {
  C1: "질문 응답성",
  C2: "완결성",
  C3: "내부 일관성",
  C4: "톤 적절성",
  C5: "할루시네이션 징후",
  F1: "수치 제시",
  F2: "단위 표기",
  F3: "가정 전제",
  F4: "불확실성 언급",
  F5: "리스크 경고",
  G1: "근거 출처",
  G2: "법령 인용",
  G3: "조문 번호",
  G4: "면책 고지",
  A1: "지역 정보",
  A2: "업종 정보",
  A3: "수치 근거",
  A4: "기간 명시",
  A5: "출처 안내",
};

const GRADE_STYLE = {
  A: "text-green-700 bg-green-50 border-green-200",
  B: "text-amber-700 bg-amber-50 border-amber-200",
  C: "text-red-600 bg-red-50 border-red-200",
};
const GRADE_LABEL = {
  A: "A 통과",
  B: "B 경고 포함 통과",
  C: "C 반려",
};

/**
 * @param {{
 *   status: string,
 *   grade?: string,
 *   confidenceNote?: string,
 *   retryCount: number,
 *   domain: string,
 *   agentMs?: number,
 *   signoffMs?: number,
 *   rejectionHistory: Array<{attempt, passed, issues, warnings, retry_prompt}>
 * }} props
 */
export default function SignoffPanel({ status, grade, confidenceNote, retryCount, domain, agentMs, signoffMs, rejectionHistory }) {
  const [open, setOpen] = useState(false);
  const effectiveGrade = grade || (status === "approved" ? "A" : "C");
  const gradeStyle = GRADE_STYLE[effectiveGrade] || GRADE_STYLE.C;

  if (!rejectionHistory || rejectionHistory.length === 0) {
    return (
      <div className={`mt-3 border rounded-lg px-3 py-2 text-xs ${gradeStyle}`}>
        <div className="flex items-center gap-2">
          <span className="font-semibold">{GRADE_LABEL[effectiveGrade] || effectiveGrade} — 1회 통과</span>
          {agentMs != null && (
            <span className="text-slate-400 ml-auto">에이전트 {agentMs}ms / Sign-off {signoffMs}ms</span>
          )}
        </div>
        {confidenceNote && (
          <div className="mt-1 text-amber-600">{confidenceNote}</div>
        )}
      </div>
    );
  }

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-2 text-xs border rounded-lg px-3 py-2 w-full transition-colors hover:opacity-90 ${gradeStyle}`}
      >
        <span className="font-semibold">{GRADE_LABEL[effectiveGrade] || effectiveGrade}</span>
        <span className="text-slate-500">재시도 {retryCount}회</span>
        <span className="text-slate-400">거부 이력 {rejectionHistory.length}건</span>
        {agentMs != null && (
          <span className="text-slate-400 text-[10px]">{agentMs}ms / {signoffMs}ms</span>
        )}
        <span className="ml-auto">{open ? "▲" : "▼"}</span>
      </button>

      {confidenceNote && !open && (
        <div className="mt-1 text-xs text-amber-600 px-1">{confidenceNote}</div>
      )}

      {open && (
        <div className="mt-2 border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
          {confidenceNote && (
            <div className="bg-amber-50 px-4 py-2 text-xs text-amber-700">
              <span className="font-semibold">주의: </span>{confidenceNote}
            </div>
          )}
          {rejectionHistory.map((attempt) => (
            <AttemptRow key={attempt.attempt} attempt={attempt} />
          ))}
        </div>
      )}
    </div>
  );
}

function AttemptRow({ attempt }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const passed   = attempt.passed   || [];
  const issues   = attempt.issues   || [];
  const warnings = attempt.warnings || [];

  return (
    <div className="bg-white px-4 py-3 text-xs">
      <button
        onClick={() => setDetailOpen((v) => !v)}
        className="w-full flex items-center gap-2 text-left"
      >
        <span className="font-semibold text-slate-600">시도 {attempt.attempt}</span>
        <div className="flex gap-1 flex-wrap">
          {passed.map((code) => (
            <span key={code} className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-mono">
              {code}
            </span>
          ))}
          {warnings.map((w) => (
            <span key={w.code} className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-mono">
              {w.code}
            </span>
          ))}
          {issues.map((iss) => (
            <span key={iss.code} className="bg-red-100 text-red-600 px-1.5 py-0.5 rounded font-mono">
              {iss.code}
            </span>
          ))}
        </div>
        <span className="ml-auto text-slate-400">{detailOpen ? "▲" : "▼"}</span>
      </button>

      {detailOpen && (
        <div className="mt-3 space-y-2">
          {warnings.map((w) => (
            <div key={w.code} className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              <div className="font-semibold text-amber-700 mb-0.5">
                {w.code} — {ITEM_LABELS[w.code] || w.code} <span className="font-normal text-amber-500">(경고)</span>
              </div>
              <div className="text-slate-600">{w.reason}</div>
            </div>
          ))}
          {issues.map((iss) => (
            <div key={iss.code} className="bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              <div className="font-semibold text-red-700 mb-0.5">
                {iss.code} — {ITEM_LABELS[iss.code] || iss.code} <span className="font-normal text-red-400">(반려)</span>
              </div>
              <div className="text-slate-600">{iss.reason}</div>
            </div>
          ))}
          {attempt.retry_prompt && (
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
              <div className="font-semibold text-slate-500 mb-1">수정 지시문</div>
              <div className="text-slate-600 whitespace-pre-wrap leading-relaxed">
                {attempt.retry_prompt}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
