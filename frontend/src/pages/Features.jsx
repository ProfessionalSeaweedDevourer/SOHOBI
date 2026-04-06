import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { AnimatedBackground } from '../components/AnimatedBackground';
import { ThemeToggle } from '../components/ThemeToggle';
import { ScrollReveal } from '../components/ScrollReveal';
import {
  MessageSquare, ArrowLeft, ArrowRight, FileText, MapPin, Calculator,
  Landmark, Gift, CheckCircle2, Sparkles,
} from 'lucide-react';
import { motion } from 'motion/react';
import { trackEvent } from '../utils/trackEvent';

const features = [
  {
    id: 'admin',
    icon: FileText,
    color: '#0891b2',
    title: '행정 절차 안내',
    description: '영업신고·위생교육·사업자등록 등 식품업 창업에 필요한 모든 행정 절차를 법령 기반으로 단계별 안내합니다.',
    examples: [
      '카페 창업 영업신고는 어디서 어떻게 하나요?',
      '위생교육 언제, 어디서 받아야 하나요?',
      '사업자등록증 발급 절차가 어떻게 되나요?',
    ],
  },
  {
    id: 'finance',
    icon: Calculator,
    color: '#f97316',
    title: '재무 시뮬레이션',
    description: '몬테카를로 시뮬레이션(10,000회)으로 창업 수익성을 분석합니다. 손익분기점, 손실 확률, 투자 회수 시나리오를 차트로 확인하세요.',
    examples: [
      '월매출 2,000만, 임대료 200만이면 수익이 얼마나 될까요?',
      '초기투자 5,000만이면 몇 달 만에 회수할 수 있나요?',
      '인건비 350만, 원가율 30%로 손익분기점 계산해주세요.',
    ],
  },
  {
    id: 'legal',
    icon: Landmark,
    color: '#8b5cf6',
    title: '법무 정보',
    description: '임대차 계약·권리금·상가건물임대차보호법 등 창업자가 꼭 알아야 할 법적 정보를 법령 조항 인용과 함께 제공합니다.',
    examples: [
      '권리금 계약할 때 주의할 점이 뭔가요?',
      '임대인이 계약 갱신을 거부할 수 있나요?',
      '상가 임대차보호법 적용 요건이 뭔가요?',
    ],
  },
  {
    id: 'location',
    icon: MapPin,
    color: '#14b8a6',
    title: '상권 분석',
    description: '서울 2025년 4분기 데이터 기반 상권 분석. 월매출·유동인구·경쟁업체·개폐업률을 분석하고, 복수 지역 비교도 가능합니다.',
    examples: [
      '홍대 카페 상권 어떤가요?',
      '연남동 vs 합정동, 한식당 어디가 더 나은가요?',
      '강남역 주변 분식집 월매출 평균이 얼마예요?',
    ],
  },
  {
    id: 'gov',
    icon: Gift,
    color: '#ec4899',
    title: '정부 지원 추천',
    description: '5,600건 이상의 정부 지원 사업 중 내 상황에 맞는 보조금·창업패키지·대출·신용보증을 자동으로 찾아드립니다.',
    examples: [
      '청년 창업자가 받을 수 있는 지원금이 있나요?',
      '소상공인 창업 대출 어디서 신청하나요?',
      '음식점 창업 관련 정부 지원 사업 추천해주세요.',
    ],
  },
];

const steps = [
  {
    number: '01',
    title: '자유롭게 질문하세요',
    description: '메뉴 선택 없이 상황을 편하게 한국어로 설명하세요. 지역, 업종, 자본금을 알려주시면 더 정확한 답변을 드립니다.',
    color: 'var(--brand-blue)',
  },
  {
    number: '02',
    title: 'AI가 전문가를 배정합니다',
    description: '질문 내용에 따라 행정·재무·법무·상권 에이전트 중 가장 적합한 전문가가 자동으로 배정됩니다.',
    color: 'var(--brand-teal)',
  },
  {
    number: '03',
    title: '검증된 답변을 받으세요',
    description: 'Sign-off 루브릭이 모든 답변의 법령·수치·절차를 자동 검증합니다. 미흡하면 자동으로 재작성합니다.',
    color: 'var(--brand-orange)',
  },
];

export default function Features() {
  useEffect(() => {
    trackEvent('feature_discovery', { page: 'features' });
  }, []);

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
          <Link to="/">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft size={18} />
              <span className="text-sm">홈으로</span>
            </motion.div>
          </Link>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <motion.div
                className="w-8 h-8 bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)] rounded-lg flex items-center justify-center"
                whileHover={{ scale: 1.1, rotate: 360 }}
                transition={{ duration: 0.6 }}
              >
                <MessageSquare size={18} className="text-white" />
              </motion.div>
              <span className="gradient-text font-semibold">SOHOBI</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to="/user">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button size="sm" className="shadow-lg hover-glow-blue transition-glow">
                  상담 시작하기
                </Button>
              </motion.div>
            </Link>
          </div>
        </div>
      </motion.header>

      {/* Hero */}
      <section className="container mx-auto px-4 pt-20 pb-12 text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 glass px-5 py-2.5 rounded-full text-sm mb-8 shadow-elevated"
        >
          <Sparkles size={16} className="text-[var(--brand-blue)]" />
          <span className="gradient-text font-semibold">이런 걸 물어볼 수 있어요</span>
        </motion.div>
        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-4xl md:text-5xl lg:text-6xl mb-6 leading-tight tracking-tight"
        >
          외식업 창업,<br />
          <span className="gradient-text">어떤 질문이든</span> 괜찮아요
        </motion.h1>
        <motion.p
          initial={{ y: 15, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.35 }}
          className="text-lg text-muted-foreground max-w-xl mx-auto"
        >
          행정부터 상권, 재무, 법무, 정부지원까지 — 5개 전문 에이전트가 법령과 데이터를 기반으로 답합니다.
        </motion.p>
      </section>

      {/* Feature Cards */}
      <section className="container mx-auto px-4 py-12">
        <div className="max-w-5xl mx-auto space-y-8">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.5, delay: idx * 0.05 }}
                className="group"
              >
                <div className="glass rounded-2xl p-8 shadow-elevated relative overflow-hidden">
                  <div
                    className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300"
                    style={{ backgroundColor: feature.color }}
                  />
                  <div className="flex flex-col md:flex-row gap-6 relative z-10">
                    {/* Icon + Title */}
                    <div className="flex items-start gap-4 md:w-56 shrink-0">
                      <motion.div
                        className="p-3 rounded-xl shrink-0 shadow-lg relative"
                        style={{ backgroundColor: `${feature.color}20` }}
                        whileHover={{ rotate: [0, -10, 10, -10, 0] }}
                        transition={{ duration: 0.5 }}
                      >
                        <div
                          className="absolute inset-0 rounded-xl blur-xl opacity-40 group-hover:opacity-60 transition-opacity"
                          style={{ backgroundColor: feature.color }}
                        />
                        <Icon size={26} style={{ color: feature.color }} className="relative z-10" />
                      </motion.div>
                      <div>
                        <h3 className="text-lg mb-1" style={{ color: feature.color }}>
                          {feature.title}
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed md:hidden">
                          {feature.description}
                        </p>
                      </div>
                    </div>

                    {/* Description + Examples */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-muted-foreground leading-relaxed mb-4 hidden md:block">
                        {feature.description}
                      </p>
                      <div className="space-y-2">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">예시 질문</p>
                        {feature.examples.map((ex, i) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -10 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: idx * 0.05 + i * 0.06 }}
                            className="flex items-start gap-2 text-sm"
                          >
                            <CheckCircle2
                              size={14}
                              className="mt-0.5 shrink-0 opacity-70"
                              style={{ color: feature.color }}
                            />
                            <span className="text-foreground/80">{ex}</span>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* 3-Step Flow */}
      <section className="container mx-auto px-4 py-20">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-14"
          >
            <h2 className="text-3xl md:text-4xl gradient-text">이렇게 사용하세요</h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {steps.map((step, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                whileHover={{ y: -6 }}
              >
                <div className="glass rounded-2xl p-8 text-center shadow-elevated h-full">
                  <div
                    className="text-5xl font-bold mb-4 opacity-20"
                    style={{ color: step.color }}
                  >
                    {step.number}
                  </div>
                  <h3 className="text-lg mb-3">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 pb-24">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto"
        >
          <div className="glass rounded-3xl p-14 text-center shadow-elevated-lg relative overflow-hidden">
            <div
              className="absolute inset-0 bg-gradient-to-r from-[var(--brand-blue)] via-[var(--brand-teal)] to-[var(--brand-blue)] opacity-10 animate-shimmer"
              style={{ backgroundSize: '200% 100%' }}
            />
            <div className="absolute top-0 left-1/4 w-48 h-48 bg-[var(--brand-blue)] rounded-full blur-3xl opacity-20 animate-float" />
            <div className="absolute bottom-0 right-1/4 w-48 h-48 bg-[var(--brand-teal)] rounded-full blur-3xl opacity-20 animate-float" style={{ animationDelay: '1s' }} />
            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl mb-4 gradient-text">지금 바로 시작해보세요</h2>
              <p className="text-muted-foreground mb-8">무료로 모든 기능을 이용할 수 있습니다</p>
              <Link to="/user">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="inline-block"
                >
                  <Button size="lg" className="px-10 py-6 text-lg shadow-elevated-lg hover-glow-blue transition-glow">
                    무료 상담 시작하기
                    <ArrowRight size={18} className="ml-2" />
                  </Button>
                </motion.div>
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="glass border-t border-white/20 py-10 backdrop-blur-xl">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p className="mb-2">© 2026 SOHOBI. 소상공인을 위한 AI 컨설팅 플랫폼</p>
          <Link to="/privacy" className="hover:text-[var(--brand-blue)] transition-colors underline underline-offset-2">
            개인정보처리방침
          </Link>
        </div>
      </footer>
    </div>
  );
}
