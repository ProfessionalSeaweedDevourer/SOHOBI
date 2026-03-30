import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { isDevAuthenticated } from "../utils/devAuth";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { ScrollReveal } from "../components/ScrollReveal";
import { ThemeToggle } from "../components/ThemeToggle";

const modes = [
  {
    path: "/user",
    label: "사용자 모드",
    icon: "💬",
    desc: "창업 관련 질문을 입력하면 AI 에이전트가 분석하고 답변합니다.",
    glowClass: "hover-glow-blue",
    badge: "일반",
    badgeStyle: { background: "rgba(8,145,178,0.15)", color: "var(--brand-blue)" },
  },
  {
    path: "/map",
    label: "지도 모드",
    icon: "🗺️",
    desc: "서울 행정동 지도에서 상권을 탐색하고 AI 채팅으로 분석합니다.",
    glowClass: "hover-glow-teal",
    badge: "지도",
    badgeStyle: { background: "rgba(20,184,166,0.15)", color: "var(--brand-teal)" },
  },
  {
    path: "/dev",
    label: "개발자 모드",
    icon: "🛠",
    desc: "에이전트 응답과 함께 Sign-off 판정 내역, 루브릭 통과 여부, 로그를 확인합니다.",
    glowClass: "hover-glow-orange",
    badge: "개발자",
    badgeStyle: { background: "rgba(249,115,22,0.15)", color: "var(--brand-orange)" },
  },
];

export default function Home() {
  const navigate = useNavigate();

  function handleModeClick(path) {
    if (path === "/dev" && !isDevAuthenticated()) {
      navigate("/dev/login", { state: { from: { pathname: "/dev" } } });
      return;
    }
    navigate(path);
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-background">
      <AnimatedBackground />
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>
      <ScrollReveal className="mb-10 text-center">
        <h1 className="text-3xl font-bold gradient-text mb-2">SOHOBI</h1>
        <p className="text-muted-foreground text-sm">
          소호비 — 1인 창업가를 위한 AI 상담 에이전트
        </p>
      </ScrollReveal>

      <div className="flex flex-col sm:flex-row gap-6 w-full max-w-2xl">
        {modes.map((m, idx) => (
          <ScrollReveal key={m.path} delay={idx * 0.1} className="flex-1">
            <motion.button
              onClick={() => handleModeClick(m.path)}
              whileHover={{ scale: 1.02, y: -6 }}
              whileTap={{ scale: 0.98 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
              className={`w-full text-left glass rounded-2xl p-8 shadow-elevated transition-glow cursor-pointer ${m.glowClass}`}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">{m.icon}</span>
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={m.badgeStyle}
                >
                  {m.badge}
                </span>
              </div>
              <div className="text-lg font-semibold text-foreground mb-1">
                {m.label}
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{m.desc}</p>
            </motion.button>
          </ScrollReveal>
        ))}
      </div>
    </div>
  );
}
