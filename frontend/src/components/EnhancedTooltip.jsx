import * as React from 'react';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { motion, AnimatePresence } from 'motion/react';

export function EnhancedTooltip({
  children,
  content,
  side = 'top',
  delayDuration = 200,
  className = '',
}) {
  const [open, setOpen] = React.useState(false);

  return (
    <TooltipPrimitive.Provider delayDuration={delayDuration}>
      <TooltipPrimitive.Root open={open} onOpenChange={setOpen}>
        <TooltipPrimitive.Trigger asChild>
          {children}
        </TooltipPrimitive.Trigger>
        <AnimatePresence>
          {open && (
            <TooltipPrimitive.Portal forceMount>
              <TooltipPrimitive.Content side={side} sideOffset={5} asChild>
                <motion.div
                  initial={{ opacity: 0, scale: 0.96, y: side === 'top' ? 5 : -5 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className={`glass-card rounded-lg px-3 py-2 text-sm shadow-elevated z-50 ${className}`}
                >
                  {content}
                  <TooltipPrimitive.Arrow className="fill-[var(--glass-border)]" />
                </motion.div>
              </TooltipPrimitive.Content>
            </TooltipPrimitive.Portal>
          )}
        </AnimatePresence>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

export default EnhancedTooltip;
