import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { streamQuery } from "../api";
import { clearDevAuth } from "../utils/devAuth";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";
import SignoffPanel from "../components/SignoffPanel";
import ProgressPanel from "../components/ProgressPanel";

export default function DevChat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [latestParams, setLatestParams] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeEvents, setActiveEvents] = useState([]); // 스트리밍 중인 이벤트 목록
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeEvents, loading]);

  async function handleSubmit(question) {
    setError(null);
    setLoading(true);
    setActiveEvents([]);

    let finalResult = null;
    let resolvedSessionId = sessionId;

    try {
      await streamQuery(question, 3, sessionId, (eventName, data) => {
        setActiveEvents(prev => [...prev, { event: eventName, ...data }]);

        if (eventName === "domain_classified" && data.session_id) {
          resolvedSessionId = data.session_id;
          setSessionId(data.session_id);
        }
        if (eventName === "complete") {
          finalResult = data;
        }
      }, latestParams);
    } catch (e) {
      setError(e.message);
      setLoading(false);
      return;
    }

    if (finalResult) {
      setMessages(prev => [
        ...prev,
        {
          question,
          domain:           finalResult.domain,
          status:           finalResult.status,
          grade:            finalResult.grade,
          confidenceNote:   finalResult.confidence_note,
          draft:            finalResult.draft,
          retryCount:       finalResult.retry_count,
          agentMs:          finalResult.agent_ms,
          signoffMs:        finalResult.signoff_ms,
          rejectionHistory: finalResult.rejection_history || [],
          chart:            finalResult.chart || null,
        },
      ]);
      if (finalResult.updated_params) setLatestParams(finalResult.updated_params);
    }

    setActiveEvents([]);
    setLoading(false);
    inputRef.current?.clear();
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="text-slate-400 hover:text-slate-700 text-sm"
        >
          ← 홈
        </button>
        <span className="font-semibold text-slate-800">SOHOBI 개발자</span>
        <span className="ml-auto text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">
          개발자
        </span>
        <button
          onClick={() => navigate("/dev/logs")}
          className="text-xs text-slate-500 border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-100 transition-colors"
        >
          📋 로그 뷰어
        </button>
        <button
          onClick={() => { clearDevAuth(); navigate("/"); }}
          className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
        >
          로그아웃
        </button>
      </header>

      {/* 대화 영역 */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 && !loading && (
          <div className="text-center mt-20 text-slate-400">
            <div className="text-4xl mb-3">🛠</div>
            <p className="text-sm">질문 입력 시 실시간 진행 상황과 Sign-off 판정 결과가 표시됩니다.</p>
            <p className="text-xs mt-1 text-slate-300">에이전트 단계, A/B/C 등급, 반려 이유, 수정 지시문을 실시간으로 확인할 수 있습니다.</p>
          </div>
        )}

        <div className="flex flex-col gap-8">
          {messages.map((msg, i) => (
            <div key={i}>
              <ResponseCard
                question={msg.question}
                domain={msg.domain}
                status={msg.status}
                grade={msg.grade}
                confidenceNote={msg.confidenceNote}
                draft={msg.draft}
                retryCount={msg.retryCount}
                chart={msg.chart}
                showMeta={true}
              />
              <SignoffPanel
                status={msg.status}
                grade={msg.grade}
                confidenceNote={msg.confidenceNote}
                retryCount={msg.retryCount}
                domain={msg.domain}
                agentMs={msg.agentMs}
                signoffMs={msg.signoffMs}
                rejectionHistory={msg.rejectionHistory}
              />
            </div>
          ))}

          {/* 스트리밍 진행 중 */}
          {loading && (
            <div className="border border-slate-200 rounded-xl bg-white px-4 py-3">
              <div className="text-xs text-slate-400 mb-2 font-medium">처리 중</div>
              <ProgressPanel events={activeEvents} detailed={true} />
              {activeEvents.length === 0 && (
                <div className="flex items-center gap-2 text-slate-400 text-xs">
                  <span className="inline-block w-3 h-3 border-2 border-slate-200 border-t-blue-400 rounded-full animate-spin" />
                  도메인 분류 중…
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
              오류: {error}
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </main>

      {/* 입력창 */}
      <footer className="sticky bottom-0 bg-slate-50 border-t border-slate-100 px-4 py-3 max-w-3xl mx-auto w-full">
        <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} />
      </footer>
    </div>
  );
}
