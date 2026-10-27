import { CheckCircle, Circle, Loader2 } from 'lucide-react';
import type { ProgressEvent } from '../types';

interface ProgressPanelProps {
  events: ProgressEvent[];
  currentStep: number;
  totalSteps: number;
}

const STEPS = [
  { id: 1, label: 'Extract text', description: 'Reading PDF pages' },
  { id: 2, label: 'Chunk & index', description: 'Embedding & storing chunks' },
  { id: 3, label: 'Write brief', description: 'Summarising with LLM' },
  { id: 4, label: 'Extract claims', description: 'Finding key statements' },
  { id: 5, label: 'Verify claims', description: 'Cross-checking against source' },
];

export function ProgressPanel({ events, currentStep, totalSteps }: ProgressPanelProps) {
  const progressPct = Math.round((currentStep / totalSteps) * 100);
  const latestEvent = events[events.length - 1];

  return (
    <div id="progress-panel" className="glass rounded-2xl p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center">
          <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Analysing paper…</h3>
          <p className="text-xs text-slate-500">This may take a few minutes</p>
        </div>
        <span className="ml-auto text-2xl font-bold text-gradient">{progressPct}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full progress-shimmer rounded-full transition-all duration-700 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {STEPS.map(step => {
          const isDone = currentStep > step.id;
          const isActive = currentStep === step.id;
          const isPending = currentStep < step.id;

          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300
                ${isActive ? 'bg-indigo-500/10 border border-indigo-500/20' : ''}
                ${isDone ? 'opacity-60' : ''}
                ${isPending ? 'opacity-30' : ''}
              `}
            >
              <div className="flex-shrink-0">
                {isDone && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                {isActive && <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
                {isPending && <Circle className="w-4 h-4 text-slate-600" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium ${isActive ? 'text-indigo-300' : isDone ? 'text-slate-300' : 'text-slate-500'}`}>
                  {step.label}
                </p>
                <p className="text-xs text-slate-600 truncate">{step.description}</p>
              </div>
              <span className={`text-xs px-1.5 py-0.5 rounded-md flex-shrink-0
                ${isDone ? 'bg-emerald-500/10 text-emerald-400' : isActive ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-700'}`}>
                {isDone ? 'done' : isActive ? 'active' : `step ${step.id}`}
              </span>
            </div>
          );
        })}
      </div>

      {/* Latest log */}
      {latestEvent && (
        <div className="bg-black/20 rounded-xl px-3 py-2 border border-white/5">
          <p className="text-xs text-slate-400 font-mono truncate">
            ▶ {latestEvent.message}
          </p>
        </div>
      )}
    </div>
  );
}
