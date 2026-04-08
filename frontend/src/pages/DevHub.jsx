import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { clearDevAuth } from "../utils/devAuth";
import { ThemeToggle } from "../components/ThemeToggle";
import { ArrowLeft } from "lucide-react";

const TOOLS = [
  {
    path: "/dev/logs",
    icon: "📋",
    label: "로그 뷰어",
    desc: "전체 요청·거부 이력·응답 오류·투표 집계를 확인합니다.",
  },
  {
    path: "/dev/stats",
    icon: "📊",
    label: "성능 통계",
    desc: "에이전트별 응답 시간, 등급 분포, 상태 현황을 모니터링합니다.",
  },
];

export default function DevHub() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="sticky top-0 z-10 glass border-b border-[var(--border)] px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
        >
          <ArrowLeft size={16} />
          홈
        </button>
        <div className="w-px h-4" style={{ background: "var(--border)" }} />
        <span className="font-semibold text-foreground">개발자 도구</span>
        <span className="ml-auto" />
        <ThemeToggle />
        <button
          onClick={() => { clearDevAuth(); navigate("/"); }}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          로그아웃
        </button>
      </header>

      <main className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="text-4xl mb-3">🛠</div>
            <h1 className="text-xl font-bold text-foreground">개발자 도구</h1>
            <p className="text-sm text-muted-foreground mt-1">
              내부 모니터링 및 디버깅 도구입니다.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            {TOOLS.map((tool) => (
              <motion.button
                key={tool.path}
                onClick={() => navigate(tool.path)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="glass-card rounded-2xl p-5 text-left hover:shadow-elevated transition-all"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{tool.icon}</span>
                  <span className="font-semibold text-foreground">{tool.label}</span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {tool.desc}
                </p>
              </motion.button>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
