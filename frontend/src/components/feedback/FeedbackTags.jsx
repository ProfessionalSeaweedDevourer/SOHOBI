import { NEGATIVE_FEEDBACK_TAGS, FEEDBACK_MESSAGES } from "./feedbackConstants";

export default function FeedbackTags({ selectedTags, onTagToggle, onSubmit, isSubmitDisabled }) {
  return (
    <div className="mt-3">
      <p className="text-xs text-muted-foreground mb-2">{FEEDBACK_MESSAGES.tagPrompt}</p>
      <div className="flex flex-wrap gap-2 mb-3">
        {NEGATIVE_FEEDBACK_TAGS.map((tag) => {
          const isSelected = selectedTags.includes(tag.id);
          return (
            <button
              key={tag.id}
              type="button"
              onClick={() => onTagToggle(tag.id)}
              className="text-xs px-3 py-1.5 rounded-full border transition-colors duration-150"
              style={
                isSelected
                  ? {
                      background: "var(--brand-blue)",
                      color: "#fff",
                      borderColor: "var(--brand-blue)",
                    }
                  : {
                      background: "var(--muted)",
                      color: "var(--muted-foreground)",
                      borderColor: "var(--border)",
                    }
              }
            >
              {tag.label}
            </button>
          );
        })}
      </div>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitDisabled}
          className="text-xs px-4 py-1.5 rounded-full font-semibold transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: isSubmitDisabled ? "var(--muted)" : "var(--brand-blue)",
            color: isSubmitDisabled ? "var(--muted-foreground)" : "#fff",
          }}
        >
          {FEEDBACK_MESSAGES.submitButton}
        </button>
      </div>
    </div>
  );
}
