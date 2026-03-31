import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { AgentCard } from '../components/AgentCard';
import { AnimatedBackground } from '../components/AnimatedBackground';
import { ThemeToggle } from '../components/ThemeToggle';
import { ScrollReveal } from '../components/ScrollReveal';
import { agentData } from '../data/mockData';
import { MessageSquare, Shield, Zap, TrendingUp, Sparkles, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';

export default function Landing() {
  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />

      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <motion.div
              className="w-10 h-10 bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] rounded-xl flex items-center justify-center shadow-lg relative"
              whileHover={{ scale: 1.1, rotate: 360 }}
              transition={{ duration: 0.6 }}
            >
              <div className="absolute inset-0 bg-[var(--brand-blue)] rounded-xl blur-lg opacity-40" />
              <MessageSquare size={24} className="text-white relative z-10" />
            </motion.div>
            <div>
              <h1 className="text-xl leading-none mb-0.5 gradient-text">SOHOBI</h1>
              <p className="text-xs text-muted-foreground">소호비</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to="/user">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button className="shadow-lg hover-glow-blue transition-glow">
                  지금 시작하기
                </Button>
              </motion.div>
            </Link>
          </div>
        </div>
      </motion.header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-32 md:py-40">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 glass px-5 py-2.5 rounded-full text-sm mb-8 shadow-elevated"
          >
            <Sparkles size={16} className="text-[var(--brand-blue)]" />
            <span className="gradient-text font-semibold">AI 기반 창업 컨설팅 플랫폼</span>
          </motion.div>

          <motion.h1
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-5xl md:text-6xl lg:text-7xl mb-8 leading-tight tracking-tight"
          >
            외식업 창업,<br />
            <span className="gradient-text inline-block">AI 전문가</span>와 함께<br className="md:hidden" /> 시작하세요
          </motion.h1>

          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed"
          >
            행정, 상권분석, 재무까지. 세 명의 전문 AI 에이전트가
            당신의 성공적인 창업을 도와드립니다.
          </motion.p>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <Link to="/user">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button size="lg" className="px-10 py-6 text-lg shadow-elevated-lg hover-glow-blue transition-glow">
                  무료로 상담 시작하기
                </Button>
              </motion.div>
            </Link>
            <Link to="/map">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button size="lg" variant="outline" className="px-10 py-6 text-lg glass border-2 shadow-elevated">
                  지도·상권분석 보기
                </Button>
              </motion.div>
            </Link>
            <Link to="/dev/logs">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button size="lg" variant="outline" className="px-10 py-6 text-lg glass border-2 shadow-elevated">
                  데모 로그 보기
                </Button>
              </motion.div>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-32">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm mb-4 shadow-elevated">
              <Shield size={14} className="text-[var(--brand-blue)]" />
              <span className="text-muted-foreground">신뢰할 수 있는</span>
            </div>
            <h2 className="text-4xl md:text-5xl mb-4 gradient-text">핵심 기능</h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8 mb-24">
            {[
              {
                icon: Shield,
                title: 'SignOff 품질 검증',
                description: '모든 답변은 자동 품질 검증 파이프라인을 거쳐 신뢰성을 보장합니다',
                color: 'var(--brand-blue)',
                delay: 0,
              },
              {
                icon: MessageSquare,
                title: '자연스러운 대화',
                description: '복잡한 메뉴 없이 편하게 한국어로 질문하세요. 적합한 전문가가 자동 배정됩니다',
                color: 'var(--brand-teal)',
                delay: 0.1,
              },
              {
                icon: TrendingUp,
                title: '실시간 데이터',
                description: '1,440개 정부지원금 정보와 서울 상권 데이터를 실시간으로 활용합니다',
                color: 'var(--brand-orange)',
                delay: 0.2,
              },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: feature.delay }}
                whileHover={{ y: -8 }}
                className="group"
              >
                <div className="glass rounded-2xl p-8 text-center shadow-elevated transition-glow hover-lift relative overflow-hidden">
                  <div
                    className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300"
                    style={{ backgroundColor: feature.color }}
                  />

                  <motion.div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg relative"
                    style={{ backgroundColor: `${feature.color}15` }}
                    whileHover={{ rotate: [0, -10, 10, -10, 0], scale: 1.1 }}
                    transition={{ duration: 0.5 }}
                  >
                    <div
                      className="absolute inset-0 rounded-2xl blur-xl opacity-30 group-hover:opacity-50 transition-opacity"
                      style={{ backgroundColor: feature.color }}
                    />
                    <feature.icon size={32} style={{ color: feature.color }} className="relative z-10" />
                  </motion.div>

                  <h3 className="mb-3 text-xl">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Agent Cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm mb-4 shadow-elevated">
              <Zap size={14} className="text-[var(--brand-blue)]" />
              <span className="text-muted-foreground">전문가 에이전트</span>
            </div>
            <h2 className="text-4xl md:text-5xl gradient-text">세 명의 AI 전문가</h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {agentData.map((agent, idx) => (
              <AgentCard key={agent.id} agent={agent} index={idx} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-32">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl mx-auto relative"
        >
          <div className="glass rounded-3xl p-16 text-center shadow-elevated-lg relative overflow-hidden">
            <div
              className="absolute inset-0 bg-gradient-to-r from-[var(--brand-blue)] via-[var(--brand-teal)] to-[var(--brand-blue)] opacity-10 animate-shimmer"
              style={{ backgroundSize: '200% 100%' }}
            />

            <div className="absolute top-0 left-1/4 w-64 h-64 bg-[var(--brand-blue)] rounded-full blur-3xl opacity-20 animate-float" />
            <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-[var(--brand-teal)] rounded-full blur-3xl opacity-20 animate-float" style={{ animationDelay: '1s' }} />

            <div className="relative z-10">
              <h2 className="text-4xl md:text-5xl mb-6 gradient-text">지금 바로 시작해보세요</h2>
              <p className="text-xl mb-10 text-muted-foreground">
                무료로 모든 기능을 사용할 수 있습니다
              </p>
              <Link to="/user">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button size="lg" className="px-12 py-7 text-lg shadow-elevated-lg hover-glow-blue transition-glow">
                    상담 시작하기
                  </Button>
                </motion.div>
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="glass border-t border-white/20 py-12 backdrop-blur-xl">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p className="mb-2">© 2026 SOHOBI.</p>
          <p>소상공인을 위한 AI 컨설팅 플랫폼</p>
        </div>
      </footer>
    </div>
  );
}
