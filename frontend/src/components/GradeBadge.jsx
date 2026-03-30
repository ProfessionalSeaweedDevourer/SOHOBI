import { motion } from 'motion/react';

const colors = {
  A: { bg: '#10b981', glow: '0 0 15px rgba(16,185,129,0.5)' },
  B: { bg: '#eab308', glow: '0 0 15px rgba(234,179,8,0.5)' },
  C: { bg: '#ef4444', glow: '0 0 15px rgba(239,68,68,0.5)' },
};

const sizes = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export function GradeBadge({ grade, size = 'md' }) {
  const c = colors[grade] || colors.C;
  return (
    <motion.span
      initial={{ scale: 0, rotate: -180 }}
      animate={{ scale: 1, rotate: 0 }}
      whileHover={{ scale: 1.1 }}
      className={`inline-flex items-center justify-center rounded-md font-semibold text-white transition-all ${sizes[size]}`}
      style={{ background: c.bg, boxShadow: c.glow }}
    >
      Grade {grade}
    </motion.span>
  );
}

export default GradeBadge;
