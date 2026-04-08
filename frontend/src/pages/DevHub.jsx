import { useNavigate, Link } from "react-router-dom";
import { motion } from "motion/react";
import { clearDevAuth } from "../utils/devAuth";
import { ThemeToggle } from "../components/ThemeToggle";
import { AnimatedBackground } from "../components/AnimatedBackground";
import { ArrowLeft, Wrench, ClipboardList, BarChart3 } from "lucide-react";

const TOOLS = [
  {
    path: "/dev/logs",
    icon: ClipboardList,
    color: "var(--brand-blue)",
    label: "로그 뷰어",
    desc: "전체 요청·거부 이력·응답 오류·투표 집계를 확인합니다.",
  },
  {
    path: "/dev/stats",
    icon: BarChart3,
    color: "var(--brand-teal)",
    label: "성능 통계",
    desc: "에이전트별 응답 시간, 등급 분포, 상태 현황을 모니터링합니다.",
  },
];

export default function DevHub() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />

      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            홈
          </Link>

          <div className="flex items-center gap-2">
            <motion.div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: "rgba(8,145,178,0.15)" }}
              whileHover={{ scale: 1.1, rotate: 360 }}
              transition={{ duration: 0.6 }}
            >
              <Wrench size={18} className="text-[var(--brand-blue)]" />
            </motion.div>
            <span className="font-semibold gradient-text">개발자 도구</span>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              onClick={() => { clearDevAuth(); navigate("/"); }}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              로그아웃
            </button>
          </div>
        </div>
      </motion.header>

      {/* Hero */}
      <section className="container mx-auto px-4 pt-16 pb-10 text-center">
        <motion.div
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 glass px-5 py-2.5 rounded-full text-sm mb-6 shadow-elevated"
        >
          <Wrench size={15} className="text-[var(--brand-blue)]" />
          <span className="gradient-text font-semibold">내부 도구</span>
        </motion.div>

        <motion.h1
          initial={{ y: 18, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-3xl md:text-4xl font-bold mb-3 leading-tight tracking-tight"
        >
          개발자 <span className="gradient-text">도구</span>
        </motion.h1>

        <motion.p
          initial={{ y: 12, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="text-muted-foreground max-w-md mx-auto text-sm"
        >
          내부 모니터링 및 디버깅 도구입니다.
        </motion.p>
      </section>

      {/* Tool Cards */}
      <section className="container mx-auto px-4 pb-16">
        <div className="max-w-2xl mx-auto grid md:grid-cols-2 gap-6">
          {TOOLS.map((tool, idx) => {
            const Icon = tool.icon;
            return (
              <motion.div
                key={tool.path}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                whileHover="cardHover"
                variants={{ cardHover: { y: -8 } }}
                className="group cursor-pointer"
                onClick={() => navigate(tool.path)}
              >
                <div className="glass rounded-2xl p-8 text-center shadow-elevated transition-glow hover-lift relative overflow-hidden h-full">
                  <div
                    className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300"
                    style={{ backgroundColor: tool.color }}
                  />

                  <motion.div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg relative"
                    style={{ backgroundColor: `${tool.color}15` }}
                    variants={{ cardHover: { rotate: [0, -10, 10, -10, 0], scale: 1.1 } }}
                    transition={{ duration: 0.5 }}
                  >
                    <div
                      className="absolute inset-0 rounded-2xl blur-xl opacity-30 group-hover:opacity-50 transition-opacity"
                      style={{ backgroundColor: tool.color }}
                    />
                    <Icon size={32} style={{ color: tool.color }} className="relative z-10" />
                  </motion.div>

                  <h3 className="mb-3 text-xl font-semibold">{tool.label}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {tool.desc}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <footer className="glass border-t border-white/20 py-8 backdrop-blur-xl">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>SOHOBI 개발자 도구</p>
        </div>
      </footer>
    </div>
  );
}
