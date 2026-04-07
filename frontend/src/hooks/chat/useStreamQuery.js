import { useState, useCallback } from "react";
import { streamQuery } from "../../api";
import { interpretError } from "../../utils/errorInterpreter";

/**
 * SSE 스트리밍 쿼리 로직을 캡슐화하는 훅.
 * submit: 신규 질문 전송
 * regenerate: 기존 인덱스의 메시지를 재생성
 *
 * @param {object} params
 * @param {string|null}   params.sessionId
 * @param {object|null}   params.latestParams    - 재무 파라미터 캐시
 * @param {function}      params.onMessage       - (msg) => void  신규 메시지 추가 콜백
 * @param {function}      params.onUpdateAt      - (index, updates) => void  메시지 업데이트 콜백
 * @param {function}      params.onSessionId     - (id) => void  세션 ID 수신 콜백
 * @param {function}      params.onParams        - (params) => void  updated_params 수신 콜백
 * @param {function}      [params.onCheckedItems] - (items) => void  체크리스트 싱크 콜백 (UserChat 전용)
 */
export function useStreamQuery({
  sessionId,
  latestParams,
  onMessage,
  onUpdateAt,
  onSessionId,
  onParams,
  onCheckedItems,
}) {
  const [loading, setLoading] = useState(false);
  const [activeEvents, setActiveEvents] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);

  const _runStream = useCallback(
    async (question, onEvent, onError) => {
      setLoading(true);
      setActiveEvents([]);

      let finalResult = null;

      try {
        await streamQuery(
          question,
          3,
          sessionId,
          (eventName, data) => {
            if (eventName === "error") {
              onError(question, data.message || data.error || "");
              return;
            }
            setActiveEvents((prev) => [...prev, { event: eventName, ...data }]);
            if (eventName === "domain_classified" && data.session_id) {
              onSessionId(data.session_id);
            }
            if (eventName === "complete") {
              finalResult = data;
              if (data.checked_items?.length && onCheckedItems) {
                onCheckedItems(data.checked_items);
              }
            }
          },
          latestParams
        );
      } catch (e) {
        onError(question, e.message);
        setActiveEvents([]);
        setLoading(false);
        return;
      }

      onEvent(finalResult);
      setActiveEvents([]);
      setLoading(false);
    },
    [sessionId, latestParams, onSessionId, onCheckedItems]
  );

  const submit = useCallback(
    async (question, inputRef) => {
      setPendingQuestion(question);

      await _runStream(
        question,
        (finalResult) => {
          setPendingQuestion(null);
          if (!finalResult) return;
          onMessage(_buildMsg(question, finalResult));
          if (finalResult.updated_params) onParams(finalResult.updated_params);
          inputRef?.current?.clear();
        },
        (q, errMsg) => {
          setPendingQuestion(null);
          onMessage({ question: q, status: "error", draft: interpretError(errMsg) });
          inputRef?.current?.clear();
        }
      );
    },
    [_runStream, onMessage, onParams]
  );

  const regenerate = useCallback(
    async (index, question) => {
      await _runStream(
        question,
        (finalResult) => {
          if (!finalResult) return;
          onUpdateAt(index, { ..._buildMsg(question, finalResult), regenerated: true });
          if (finalResult.updated_params) onParams(finalResult.updated_params);
        },
        (_q, errMsg) => {
          onUpdateAt(index, { status: "error", draft: interpretError(errMsg) });
        }
      );
    },
    [_runStream, onUpdateAt, onParams]
  );

  return { loading, activeEvents, pendingQuestion, submit, regenerate };
}

function _buildMsg(question, result) {
  return {
    question,
    domain:           result.domain,
    status:           result.status,
    grade:            result.grade,
    confidenceNote:   result.confidence_note,
    draft:            result.draft,
    retryCount:       result.retry_count,
    agentMs:          result.agent_ms,
    signoffMs:        result.signoff_ms,
    rejectionHistory: result.rejection_history || [],
    chart:            result.chart || null,
    charts:           result.charts || [],
    requestId:        result.request_id || null,
    sessionId:        result.session_id || null,
    suggestedActions: result.suggested_actions || [],
    isPartial:        result.is_partial || false,
  };
}
