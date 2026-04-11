import { useState } from "react";
import FeedbackTags from "./FeedbackTags";
import { useFeedbackSubmit } from "./useFeedbackSubmit";
import { FEEDBACK_MESSAGES } from "./feedbackConstants";

// state: 'idle' | 'tagging' | 'submitting' | 'complete' | 'done'
export default function InlineFeedback({ sessionId, agentType, messageId, conversationContext }) {
  const [state, setState] = useState("idle");
  const [selectedTags, setSelectedTags] = useState([]);
  const { submitFeedback } = useFeedbackSubmit();

  const handlePositive = async () => {
    setState("submitting");
    await submitFeedback({
      sessionId,
      agentType,
      messageId,
      feedbackType: "positive",
      tags: [],
      conversationContext,
    });
    setState("complete");
    setTimeout(() => setState("done"), 1500);
  };

  const handleNegative = () => {
    setState("tagging");
  };

  const handleTagToggle = (tagId) => {
    setSelectedTags((prev) =>
      prev.includes(tagId) ? prev.filter((t) => t !== tagId) : [...prev, tagId],
    );
  };

  const handleSubmitNegative = async () => {
    setState("submitting");
    await submitFeedback({
      sessionId,
      agentType,
      messageId,
      feedbackType: "negative",
      tags: selectedTags,
      conversationContext,
    });
    setState("complete");
    setTimeout(() => setState("done"), 1500);
  };

  if (state === "done") {
    return (
      <div
        className="mt-3 pt-3 text-xs text-muted-foreground"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        {FEEDBACK_MESSAGES.done}
      </div>
    );
  }

  if (state === "complete") {
    return (
      <div
        className="mt-3 pt-3 text-xs"
        style={{ borderTop: "1px solid var(--border)", color: "var(--brand-teal)" }}
      >
        {FEEDBACK_MESSAGES.thankYou}
      </div>
    );
  }

  return (
    <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground">{FEEDBACK_MESSAGES.prompt}</span>
        <button
          type="button"
          onClick={handlePositive}
          disabled={state === "submitting"}
          aria-label="도움이 됐어요"
          className="text-base leading-none px-2 py-1 rounded-lg border transition-colors duration-150 disabled:opacity-40"
          style={
            state === "submitting"
              ? { background: "var(--muted)", borderColor: "var(--border)" }
              : { background: "transparent", borderColor: "var(--border)" }
          }
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(16,185,129,0.12)";
            e.currentTarget.style.borderColor = "var(--grade-a)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.borderColor = "var(--border)";
          }}
        >
          👍
        </button>
        <button
          type="button"
          onClick={handleNegative}
          disabled={state === "submitting" || state === "tagging"}
          aria-label="아쉬워요"
          className="text-base leading-none px-2 py-1 rounded-lg border transition-colors duration-150 disabled:opacity-40"
          style={
            state === "tagging"
              ? { background: "rgba(244,67,54,0.12)", borderColor: "#F44336" }
              : { background: "transparent", borderColor: "var(--border)" }
          }
          onMouseEnter={(e) => {
            if (state !== "tagging") {
              e.currentTarget.style.background = "rgba(244,67,54,0.12)";
              e.currentTarget.style.borderColor = "#F44336";
            }
          }}
          onMouseLeave={(e) => {
            if (state !== "tagging") {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.borderColor = "var(--border)";
            }
          }}
        >
          👎
        </button>
      </div>

      {state === "tagging" && (
        <div style={{ overflow: "hidden", transition: "max-height 150ms ease" }}>
          <FeedbackTags
            selectedTags={selectedTags}
            onTagToggle={handleTagToggle}
            onSubmit={handleSubmitNegative}
            isSubmitDisabled={selectedTags.length === 0}
          />
        </div>
      )}
    </div>
  );
}
