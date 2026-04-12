import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { GlowCTA } from "../GlowCTA";

export default function EmptyStateCTA({
  icon,
  title,
  message,
  actionLabel,
  actionHref,
  onAction,
  orbSize = "w-40 h-40",
  iconBg = "rgba(8,145,178,0.15)",
  iconSize = "w-16 h-16",
  emojiSize = "text-3xl",
}) {
  const gradientStyle = {
    background: "linear-gradient(135deg, var(--brand-blue), var(--brand-teal))",
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      <GlowCTA orbSize={orbSize} className="p-12 text-center shadow-elevated-lg">
        <div className="flex flex-col items-center gap-4">
          <div
            className={`${iconSize} rounded-2xl flex items-center justify-center shadow-lg`}
            style={{ backgroundColor: iconBg }}
          >
            <span className={emojiSize}>{icon}</span>
          </div>

          {(title || message) && (
            <div>
              {title && (
                <p className="font-semibold mb-1" style={{ color: "var(--foreground)" }}>
                  {title}
                </p>
              )}
              {message && (
                <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  {message}
                </p>
              )}
            </div>
          )}

          {actionLabel &&
            (actionHref ? (
              <a
                href={actionHref}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-lg transition-transform hover:scale-105"
                style={gradientStyle}
              >
                {actionLabel}
                <ArrowRight size={14} />
              </a>
            ) : (
              <motion.button
                onClick={onAction}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-lg hover-glow-blue transition-glow"
                style={gradientStyle}
              >
                {actionLabel}
                <ArrowRight size={14} />
              </motion.button>
            ))}
        </div>
      </GlowCTA>
    </motion.div>
  );
}
