import { Bot, User } from 'lucide-react';
import { GradeBadge } from './GradeBadge';
import { motion } from 'motion/react';

/**
 * @param {{ message: { role, content, timestamp, grade? }, showGrade?: boolean }} props
 */
export function MessageBubble({ message, showGrade = false }) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      <motion.div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-lg relative ${
          isUser ? 'bg-secondary' : 'bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)]'
        }`}
        whileHover={{ scale: 1.1, rotate: 360 }}
        transition={{ duration: 0.4 }}
      >
        {!isUser && (
          <div className="absolute inset-0 bg-[var(--brand-blue)] rounded-full blur-lg opacity-40" />
        )}
        {isUser ? (
          <User size={18} className="text-foreground" />
        ) : (
          <Bot size={18} className="text-white relative z-10" />
        )}
      </motion.div>

      <div className={`flex-1 max-w-[80%] ${isUser ? 'flex flex-col items-end' : ''}`}>
        <motion.div
          className={`rounded-2xl px-4 py-3 shadow-elevated relative overflow-hidden ${
            isUser
              ? 'text-white'
              : 'glass border border-white/30 text-foreground'
          }`}
          style={isUser ? { background: 'linear-gradient(135deg, var(--brand-blue), var(--brand-teal))' } : {}}
          whileHover={{ scale: 1.01 }}
          transition={{ duration: 0.2 }}
        >
          <div className="whitespace-pre-wrap break-words relative z-10">{message.content}</div>
        </motion.div>

        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-xs text-muted-foreground">
            {message.timestamp instanceof Date
              ? message.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
              : message.timestamp}
          </span>
          {showGrade && message.grade && (
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2 }}>
              <GradeBadge grade={message.grade} size="sm" />
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default MessageBubble;
