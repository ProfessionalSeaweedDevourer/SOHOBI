import { useState } from "react";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const _API_KEY = import.meta.env.VITE_API_KEY || "";
const _AUTH_HEADERS = {
  "Content-Type": "application/json",
  ...(_API_KEY ? { "X-API-Key": _API_KEY } : {}),
};

export function useFeedbackSubmit() {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitFeedback = async ({
    sessionId,
    agentType,
    messageId,
    feedbackType,
    tags,
    conversationContext,
  }) => {
    setIsSubmitting(true);
    try {
      await fetch(`${BASE_URL}/api/feedback`, {
        method: "POST",
        headers: _AUTH_HEADERS,
        body: JSON.stringify({
          session_id: sessionId,
          agent_type: agentType,
          message_id: messageId,
          feedback_type: feedbackType,
          tags: tags,
          conversation_context: conversationContext || null,
          timestamp: new Date().toISOString(),
        }),
      });
    } catch (error) {
      console.warn("피드백 전송 실패 (사용자 경험에 영향 없음):", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return { submitFeedback, isSubmitting };
}
