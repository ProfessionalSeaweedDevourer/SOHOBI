import { useState } from "react";

const ITEM_LABELS = {
  C1: "질문 응답성",
  C2: "완결성",
  C3: "내부 일관성",
  C4: "톤 적절성",
  C5: "할루시네이션 부재",
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

/**
 * @param {{
 *   status: string,
 *   retryCount: number,
 *   domain: string,
 *   rejectionHistory: Array<{attempt, approved, passed, issues, retry_prompt}>
 * }} props
 */
export default function SignoffPanel({ status, retryCount, domain, rejectionHistory }) {
  const [open, setOpen] = useState(false);
  const isApproved = status === "approved";

  if (!rejectionHistory || rejectionHistory.length === 0) {
    return (
      <div className="mt-3 flex items-center gap-2 text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
        <span className="font-semibold">✅ 1회 통과</span>
        <span className="text-green-600">모든 루브릭 항목 통과</span>
      </div>
    );
  }

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-xs text-violet-700 bg-violet-50 border border-violet-200 rounded-lg px-3 py-2 hover:bg-violet-100 transition-colors w-full"
      >
        <span className={`font-semibold ${isApproved ? "text-green-700" : "text-red-600"}`}>
          {isApproved ? "✅ approved" : "❌ escalated"}
        </span>
        <span className="text-slate-500">재시도 {retryCount}회</span>
        <span className="text-slate-400">거부 이력 {rejectionHistory.length}건</span>
        <span className="ml-auto">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-2 border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
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
  const passed = attempt.passed || [];
  const issues = attempt.issues || [];

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
          {issues.map((iss) => (
            <div key={iss.code} className="bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              <div className="font-semibold text-red-700 mb-0.5">
                {iss.code} — {ITEM_LABELS[iss.code] || iss.code}
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
