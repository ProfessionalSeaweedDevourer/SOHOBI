import { FileText, MapPin, Calculator } from 'lucide-react';
import { motion } from 'motion/react';

const iconMap = {
  FileText,
  MapPin,
  Calculator,
};

export function AgentCard({ agent, index = 0 }) {
  const Icon = iconMap[agent.icon];

  const glowClass =
    agent.id === 'admin' ? 'hover-glow-blue' :
    agent.id === 'commercial' ? 'hover-glow-teal' :
    'hover-glow-orange';

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      whileHover={{ scale: 1.02, y: -8 }}
      className="group"
    >
      <div className={`glass rounded-2xl p-6 border-2 border-white/20 transition-glow hover-lift shadow-elevated ${glowClass} relative overflow-hidden`}>
        <div
          className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-2xl"
          style={{ background: `linear-gradient(135deg, ${agent.color}40, transparent)` }}
        />

        <div className="flex items-start gap-4 relative z-10">
          <motion.div
            className="p-3 rounded-xl shrink-0 shadow-lg relative"
            style={{ backgroundColor: `${agent.color}20` }}
            whileHover={{ rotate: [0, -10, 10, -10, 0] }}
            transition={{ duration: 0.5 }}
          >
            <div
              className="absolute inset-0 rounded-xl blur-xl opacity-40 group-hover:opacity-60 transition-opacity"
              style={{ backgroundColor: agent.color }}
            />
            <Icon size={28} style={{ color: agent.color }} className="relative z-10" />
          </motion.div>

          <div className="flex-1 min-w-0">
            <h3 className="mb-1 transition-colors" style={{ color: agent.color }}>
              {agent.nameKo}
            </h3>
            <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
              {agent.descriptionKo}
            </p>
            <div className="space-y-1.5">
              {agent.plugins.slice(0, 4).map((plugin, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 + idx * 0.05 }}
                  className="flex items-start gap-2 text-sm"
                >
                  <span
                    className="mt-0.5 transition-colors group-hover:opacity-100 opacity-60"
                    style={{ color: agent.color }}
                  >
                    •
                  </span>
                  <span className="text-foreground/80">{plugin}</span>
                </motion.div>
              ))}
              {agent.plugins.length > 4 && (
                <div className="text-sm text-muted-foreground pl-4">
                  +{agent.plugins.length - 4} more...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
