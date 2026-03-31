import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { streamQuery } from "../api";
import { interpretError } from "../utils/errorInterpreter";
import ChatInput from "../components/ChatInput";
import ResponseCard from "../components/ResponseCard";
import ProgressPanel from "../components/ProgressPanel";
import { ThemeToggle } from "../components/ThemeToggle";

export default function UserChat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [latestParams, setLatestParams] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeEvents, setActiveEvents] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(question) {
    setPendingQuestion(question);
    setLoading(true);
    setActiveEvents([]);

    let finalResult = null;

    try {
      await streamQuery(question, 3, sessionId, (eventName, data) => {
        if (eventName === "error") {
          setPendingQuestion(null);
          setMessages(prev => [
            ...prev,
            { question, status: "error", draft: interpretError(data.message || data.error || "") },
          ]);
          return;
        }
        setActiveEvents(prev => [...prev, { event: eventName, ...data }]);
        if (eventName === "domain_classified" && data.session_id) {
          setSessionId(data.session_id);
        }
        if (eventName === "complete") {
          finalResult = data;
        }
      }, latestParams);
    } catch (e) {
      setPendingQuestion(null);
      setMessages(prev => [
        ...prev,
        { question, status: "error", draft: interpretError(e.message) },
      ]);
      setActiveEvents([]);
      setLoading(false);
      inputRef.current?.clear();
      return;
    }

    setPendingQuestion(null);

    if (finalResult) {
      setMessages(prev => [
        ...prev,
        {
          question,
          domain:         finalResult.domain,
          status:         finalResult.status,
          grade:          finalResult.grade,
          confidenceNote: finalResult.confidence_note,
          draft:          finalResult.draft,
          retryCount:     finalResult.retry_count,
          chart:          finalResult.chart || null,
        },
      ]);
      if (finalResult.updated_params) setLatestParams(finalResult.updated_params);
    }

    setActiveEvents([]);
    setLoading(false);
    inputRef.current?.clear();
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-10 glass border-b border-[var(--border)] px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="text-muted-foreground hover:text-foreground text-sm transition-colors"
        >
          ← 홈
        </button>
        <span className="font-semibold text-foreground">SOHOBI 상담</span>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: "rgba(8,145,178,0.15)", color: "var(--brand-blue)" }}
        >
          사용자
        </span>
        <ThemeToggle />
      </header>

      {/* 대화 영역 */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 && !loading && !pendingQuestion && (
          <div className="text-center mt-20 text-muted-foreground">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-sm">창업 관련 질문을 입력해 보세요.</p>
            <div className="mt-4 flex flex-col gap-2 items-center">
              {[
                "월매출 700만원, 재료비 200만원, 직원 1명 월급 250만원으로 분식집 창업 시 수익성은?",
                "홍대 카페 상권 분석해 줘",
                "임대차 계약 시 권리금 보호 규정이 있나요?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => handleSubmit(q)}
                  className="text-xs text-muted-foreground glass rounded-full px-4 py-1.5 hover:shadow-elevated transition-glow max-w-xs text-left"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {messages.map((msg, i) => (
            <ResponseCard
              key={i}
              question={msg.question}
              domain={msg.domain}
              status={msg.status}
              grade={msg.grade}
              confidenceNote={msg.confidenceNote}
              draft={msg.draft}
              retryCount={msg.retryCount}
              chart={msg.chart}
              showMeta={false}
            />
          ))}

          {pendingQuestion && (
            <div
              className="self-end max-w-[80%] text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed"
              style={{ background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))" }}
            >
              {pendingQuestion}
            </div>
          )}

          {loading && (
            <div className="self-start glass rounded-xl px-4 py-3 text-sm w-full max-w-md shadow-elevated">
              <ProgressPanel events={activeEvents} detailed={false} />
              {activeEvents.length === 0 && (
                <div className="flex items-center gap-2 text-muted-foreground text-xs">
                  <span className="inline-block w-3 h-3 border-2 border-[var(--border)] border-t-[var(--brand-blue)] rounded-full animate-spin" />
                  분석 준비 중…
                </div>
              )}
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </main>

      {/* 입력창 */}
      <footer className="sticky bottom-0 bg-background border-t border-[var(--border)] px-4 py-3 max-w-3xl mx-auto w-full">
        <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} />
      </footer>
    </div>
  );
}
