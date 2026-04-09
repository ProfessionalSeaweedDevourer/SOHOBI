import { useState } from 'react';
import { FileText, MapPin, Calculator, Scale, Receipt, Users, UtensilsCrossed, ShieldCheck, ChevronDown } from 'lucide-react';
import { motion } from 'motion/react';

const iconMap = {
  FileText,
  MapPin,
  Calculator,
  Scale,
  Receipt,
  Users,
  UtensilsCrossed,
  ShieldCheck,
};

export function AgentCard({ agent, index = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = iconMap[agent.icon];
  const isComingSoon = !!agent.comingSoon;

  const glowClass = isComingSoon ? '' :
    agent.id === 'admin' ? 'hover-glow-blue' :
    agent.id === 'legal' ? 'hover-glow-blue' :
    agent.id === 'commercial' ? 'hover-glow-teal' :
    'hover-glow-orange';

  const handleClick = () => {
    if (!isComingSoon && agent.detailKo) {
      setExpanded((prev) => !prev);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className={`group h-full${isComingSoon ? ' opacity-60' : ''}`}
    >
      <div
        onClick={handleClick}
        className={`glass rounded-2xl p-6 border-2 border-white/20 shadow-elevated h-full flex flex-col ${isComingSoon ? '' : `transition-glow ${glowClass} cursor-pointer`} relative overflow-hidden`}
      >
        {!isComingSoon && (
          <div
            className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-2xl"
            style={{ background: `linear-gradient(135deg, ${agent.color}40, transparent)` }}
          />
        )}

        {isComingSoon && (
          <span className="absolute top-4 right-4 text-xs font-semibold px-2 py-0.5 rounded-full z-20" style={{ background: 'var(--muted)', color: 'var(--muted-foreground)' }}>
            출시 예정
          </span>
        )}

        <div className="flex items-start gap-4 relative z-10 flex-1">
          <div
            className="p-3 rounded-xl shrink-0 shadow-lg relative"
            style={{ backgroundColor: `${agent.color}20` }}
          >
            <div
              className="absolute inset-0 rounded-xl blur-md opacity-30"
              style={{ backgroundColor: agent.color }}
            />
            <Icon size={28} style={{ color: agent.color }} className="relative z-10" />
          </div>

          <div className="flex-1 min-w-0 flex flex-col">
            <h3 className="mb-1 transition-colors" style={{ color: agent.color }}>
              {agent.nameKo}
            </h3>
            <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
              {agent.descriptionKo}
            </p>
            <div className="space-y-1.5 mt-auto">
              {(agent.features || []).map((feature, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm">
                  <span
                    className="mt-0.5 transition-colors group-hover:opacity-100 opacity-60"
                    style={{ color: agent.color }}
                  >
                    ✓
                  </span>
                  <span className="text-foreground/80">{feature}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Expand toggle hint */}
        {!isComingSoon && agent.detailKo && (
          <div className="flex items-center justify-center gap-1 mt-4 relative z-10">
            <span className="text-xs text-muted-foreground">
              {expanded ? '접기' : '자세히 보기'}
            </span>
            <ChevronDown
              size={14}
              className={`text-muted-foreground transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
            />
          </div>
        )}

        {/* Expandable detail — CSS grid trick for smooth height animation */}
        {!isComingSoon && agent.detailKo && (
          <div
            className="relative z-10 transition-[grid-template-rows] duration-300 ease-in-out grid"
            style={{ gridTemplateRows: expanded ? '1fr' : '0fr' }}
          >
            <div className="overflow-hidden">
              <div className="pt-4 mt-4 border-t border-white/10">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {agent.detailKo}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
