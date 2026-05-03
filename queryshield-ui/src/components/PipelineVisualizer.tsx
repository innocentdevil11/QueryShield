import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, CircleDashed, Loader2, AlertCircle, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

export type PipelineStep = 'idle' | 'generating' | 'schema_check' | 'deterministic_fix' | 'semantic_loop' | 'done' | 'error';

export interface ThinkingLog {
  step: PipelineStep;
  message: string;
  timestamp: number;
}

interface PipelineVisualizerProps {
  currentStep: PipelineStep;
  thinkingLogs: ThinkingLog[];
}

const steps = [
  { id: 'generating', label: 'LLM Generation' },
  { id: 'schema_check', label: 'Schema Pruner' },
  { id: 'deterministic_fix', label: 'Cognitive Planner' },
  { id: 'semantic_loop', label: 'Correction Loop' },
];

export function PipelineVisualizer({ currentStep, thinkingLogs }: PipelineVisualizerProps) {
  const [expanded, setExpanded] = React.useState(true);

  if (currentStep === 'idle') return null;

  const currentIndex = steps.findIndex(s => s.id === currentStep);
  const isDone = currentStep === 'done';
  const isError = currentStep === 'error';

  return (
    <motion.div 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel rounded-2xl p-6 w-full mb-6"
    >
      <div className="flex items-center justify-between relative">
        {/* Connecting Line */}
        <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-0.5 bg-neutral-800 -z-10" />
        
        {/* Active Line Fill */}
        <motion.div 
          className="absolute left-6 top-1/2 -translate-y-1/2 h-0.5 bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)] -z-10"
          initial={{ width: '0%' }}
          animate={{ 
            width: isDone || isError ? '100%' : `${Math.max(0, (currentIndex / (steps.length - 1)) * 100)}%` 
          }}
          transition={{ duration: 0.5, ease: 'easeInOut' }}
        />

        {steps.map((step, idx) => {
          const isActive = step.id === currentStep;
          const isPast = isDone || isError || (currentIndex > idx && currentStep !== 'idle');

          return (
            <div key={step.id} className="flex flex-col items-center gap-3 bg-neutral-950/50 p-2 rounded-xl backdrop-blur-sm">
              <motion.div
                animate={
                  isActive ? { scale: [1, 1.2, 1], rotate: [0, 180, 360] } : 
                  isPast ? { scale: 1 } : { scale: 1 }
                }
                transition={{ duration: 2, repeat: isActive ? Infinity : 0, ease: "linear" }}
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors duration-300",
                  isActive ? "border-indigo-400 bg-indigo-500/20 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.4)]" :
                  isPast ? "border-emerald-500 bg-emerald-500/20 text-emerald-500" :
                  "border-neutral-700 bg-neutral-800/50 text-neutral-500"
                )}
              >
                {isActive ? <Loader2 className="w-5 h-5" /> :
                 isPast ? <CheckCircle2 className="w-5 h-5" /> :
                 <CircleDashed className="w-5 h-5" />}
              </motion.div>
              <span className={cn(
                "text-xs font-medium tracking-wide uppercase transition-colors duration-300",
                isActive ? "text-indigo-400 text-glow" :
                isPast ? "text-emerald-500" :
                "text-neutral-500"
              )}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
      
      {/* Thinking Logs Terminal */}
      {thinkingLogs.length > 0 && (
        <div className="mt-5">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-2 text-xs font-semibold text-neutral-400 uppercase tracking-wider hover:text-neutral-200 transition-colors mb-2"
          >
            <ChevronDown className={cn("w-4 h-4 transition-transform", expanded ? "rotate-0" : "-rotate-90")} />
            Pipeline Thinking ({thinkingLogs.length} events)
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4 max-h-48 overflow-y-auto font-mono text-xs space-y-1 scroll-smooth" id="thinking-log-container">
                  {thinkingLogs.map((log, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.05 }}
                      className="flex items-start gap-2"
                    >
                      <span className={cn(
                        "shrink-0 mt-0.5 w-1.5 h-1.5 rounded-full",
                        log.message.startsWith('✓') ? 'bg-emerald-500' :
                        log.message.startsWith('✗') ? 'bg-rose-500' :
                        log.message.startsWith('⚠') ? 'bg-amber-500' :
                        'bg-indigo-500'
                      )} />
                      <span className={cn(
                        log.message.startsWith('✓') ? 'text-emerald-400' :
                        log.message.startsWith('✗') ? 'text-rose-400' :
                        log.message.startsWith('⚠') ? 'text-amber-400' :
                        'text-neutral-400'
                      )}>
                        {log.message}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Status Text below */}
      <motion.div 
        key={currentStep}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-4 text-center text-sm font-medium"
      >
        {currentStep === 'done' && <span className="text-emerald-400">Pipeline complete!</span>}
        {currentStep === 'error' && <span className="text-rose-400 flex items-center justify-center gap-2"><AlertCircle className="w-4 h-4"/> Pipeline failed.</span>}
      </motion.div>
    </motion.div>
  );
}
