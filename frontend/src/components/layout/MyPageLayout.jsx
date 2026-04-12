import { motion } from "motion/react";
import { ArrowLeft, MessageSquare } from "lucide-react";
import { AnimatedBackground } from "../AnimatedBackground";
import { ThemeToggle } from "../ThemeToggle";

export default function MyPageLayout({
  heroBadge,
  heroTitle,
  heroSubtitle,
  heroExtra,
  mainGap = "gap-8",
  children,
}) {
  const BadgeIcon = heroBadge?.icon;

  return (
    <div className="min-h-screen flex flex-col relative">
      <AnimatedBackground />

      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <a
            href="/user"
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
            style={{ textDecoration: "none" }}
          >
            <ArrowLeft size={16} />
            <span className="text-sm">상담으로</span>
          </a>
          <div className="flex items-center gap-2">
            <motion.div
              className="w-8 h-8 bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] rounded-lg flex items-center justify-center shadow-lg"
              whileHover={{ scale: 1.1, rotate: 360 }}
              transition={{ duration: 0.6 }}
            >
              <MessageSquare size={16} className="text-white" />
            </motion.div>
            <span className="gradient-text font-semibold">SOHOBI</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
      </motion.header>

      <main
        className={`relative z-10 flex-1 max-w-2xl w-full mx-auto px-4 py-10 flex flex-col ${mainGap}`}
      >
        <div className="flex flex-col items-center text-center gap-4">
          {heroBadge && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm shadow-elevated"
            >
              {BadgeIcon && <BadgeIcon size={14} className="text-[var(--brand-blue)]" />}
              <span className="text-muted-foreground">{heroBadge.label}</span>
            </motion.div>
          )}

          {heroTitle && (
            <motion.h1
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.15 }}
              className="text-3xl font-bold gradient-text"
            >
              {heroTitle}
            </motion.h1>
          )}

          {heroSubtitle && (
            <motion.p
              initial={{ y: 15, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.25 }}
              className="text-sm"
              style={{ color: "var(--muted-foreground)" }}
            >
              {heroSubtitle}
            </motion.p>
          )}

          {heroExtra && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.35 }}
            >
              {heroExtra}
            </motion.div>
          )}
        </div>

        {children}
      </main>
    </div>
  );
}
