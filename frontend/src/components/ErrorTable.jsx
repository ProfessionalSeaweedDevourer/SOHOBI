import { useState } from "react";

const DOMAIN_KR = { finance: "재무", admin: "행정", legal: "법무", unknown: "미분류" };
const DOMAIN_COLOR = {
  finance: "bg-emerald-100 text-emerald-700",
  admin: "bg-sky-100 text-sky-700",
  legal: "bg-amber-100 text-amber-700",
  unknown: "bg-slate-100 text-slate-500",
};

function fmtTs(ts) {
  if (!ts) return "-";
  try {
    const normalized = ts.replace(/(\.\d{3})\d+/, "$1");
    return new Date(normalized).toLocaleString("ko-KR", {
      month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch {
    return ts;
  }
}

export default function ErrorTable({ entries = [], loading = false }) {
  const [selected, setSelected] = useState(null);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
        불러오는 중...
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
        기록된 오류가 없습니다.
      </div>
    );
  }

  const selectedEntry = selected !== null ? entries[selected] : null;

  return (
    <div className="flex gap-4 h-full">
      {/* 목록 */}
      <div className="flex flex-col gap-1 overflow-y-auto w-full md:w-80 shrink-0">
        {entries.map((entry, idx) => {
          const domain = entry.domain || "unknown";
          const isSelected = selected === idx;
          return (
            <button
              key={entry.request_id || idx}
              onClick={() => setSelected(isSelected ? null : idx)}
              className={`
                text-left rounded-xl px-3 py-2.5 border transition-colors
                ${isSelected
                  ? "border-red-300 bg-red-50"
                  : "border-slate-100 bg-white hover:bg-slate-50"}
              `}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-red-600 bg-red-100 rounded px-1.5 py-0.5">
                  오류
                </span>
                <span className={`text-xs rounded px-1.5 py-0.5 font-medium ${DOMAIN_COLOR[domain] || DOMAIN_COLOR.unknown}`}>
                  {DOMAIN_KR[domain] || domain}
                </span>
                <span className="ml-auto text-xs text-slate-400">
                  {fmtTs(entry.ts)}
                </span>
              </div>
              <p className="text-xs text-slate-700 line-clamp-2 leading-relaxed">
                {entry.question || "(질문 없음)"}
              </p>
              <p className="text-xs text-red-500 mt-1 truncate">
                {entry.error || ""}
              </p>
            </button>
          );
        })}
      </div>

      {/* 상세 패널 */}
      {selectedEntry && (
        <div className="hidden md:flex flex-col flex-1 overflow-y-auto bg-white border border-slate-100 rounded-2xl p-5 gap-4">
          {/* 메타 */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className={`rounded-lg px-2 py-1 font-medium ${DOMAIN_COLOR[selectedEntry.domain] || DOMAIN_COLOR.unknown}`}>
              {DOMAIN_KR[selectedEntry.domain] || selectedEntry.domain || "미분류"}
            </span>
            <span className="text-slate-400">{fmtTs(selectedEntry.ts)}</span>
            {selectedEntry.latency_ms > 0 && (
              <span className="text-slate-400">{selectedEntry.latency_ms.toLocaleString()}ms</span>
            )}
          </div>

          {/* 질문 */}
          <div>
            <p className="text-xs font-semibold text-slate-500 mb-1">질문</p>
            <p className="text-sm text-slate-800 leading-relaxed bg-slate-50 rounded-xl px-3 py-2">
              {selectedEntry.question || "(없음)"}
            </p>
          </div>

          {/* 오류 메시지 */}
          <div>
            <p className="text-xs font-semibold text-red-500 mb-1">오류 내용</p>
            <pre className="text-xs text-red-700 bg-red-50 border border-red-100 rounded-xl px-3 py-2 whitespace-pre-wrap break-all leading-relaxed">
              {selectedEntry.error || "(오류 메시지 없음)"}
            </pre>
          </div>

          {/* IDs */}
          {(selectedEntry.request_id || selectedEntry.session_id) && (
            <div className="text-xs text-slate-400 space-y-0.5">
              {selectedEntry.request_id && <p>request: {selectedEntry.request_id}</p>}
              {selectedEntry.session_id && <p>session: {selectedEntry.session_id}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
