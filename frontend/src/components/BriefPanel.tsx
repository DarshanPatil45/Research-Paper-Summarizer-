import type { Brief } from '../types';
import { Target, FlaskConical, BarChart2, AlertTriangle, Lightbulb } from 'lucide-react';

interface BriefPanelProps {
  brief: Brief;
}

const SECTIONS = [
  {
    key: 'problem' as keyof Brief,
    label: 'Problem',
    icon: Target,
    gradient: 'from-violet-500/20 to-purple-500/10',
    border: 'border-violet-500/30',
    iconColor: 'text-violet-400',
    badge: 'bg-violet-500/10 text-violet-400',
  },
  {
    key: 'method' as keyof Brief,
    label: 'Method',
    icon: FlaskConical,
    gradient: 'from-blue-500/20 to-cyan-500/10',
    border: 'border-blue-500/30',
    iconColor: 'text-blue-400',
    badge: 'bg-blue-500/10 text-blue-400',
  },
  {
    key: 'results' as keyof Brief,
    label: 'Results',
    icon: BarChart2,
    gradient: 'from-emerald-500/20 to-teal-500/10',
    border: 'border-emerald-500/30',
    iconColor: 'text-emerald-400',
    badge: 'bg-emerald-500/10 text-emerald-400',
  },
  {
    key: 'limitations' as keyof Brief,
    label: 'Limitations',
    icon: AlertTriangle,
    gradient: 'from-amber-500/20 to-orange-500/10',
    border: 'border-amber-500/30',
    iconColor: 'text-amber-400',
    badge: 'bg-amber-500/10 text-amber-400',
  },
  {
    key: 'main_takeaway' as keyof Brief,
    label: 'Main Takeaway',
    icon: Lightbulb,
    gradient: 'from-pink-500/20 to-rose-500/10',
    border: 'border-pink-500/30',
    iconColor: 'text-pink-400',
    badge: 'bg-pink-500/10 text-pink-400',
  },
] as const;

export function BriefPanel({ brief }: BriefPanelProps) {
  return (
    <section id="brief-panel" aria-label="Paper Brief" className="space-y-4">
      <div className="flex items-center gap-3 mb-6">
        <h2 className="text-xl font-bold text-slate-100">Paper Brief</h2>
        <div className="flex-1 h-px bg-gradient-to-r from-white/10 to-transparent" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {SECTIONS.map(({ key, label, icon: Icon, gradient, border, iconColor, badge }, i) => (
          <div
            key={key}
            id={`brief-section-${key}`}
            className={`
              relative bg-gradient-to-br ${gradient} border ${border}
              rounded-2xl p-5 group hover:scale-[1.01] transition-all duration-200 cursor-default
              ${key === 'main_takeaway' ? 'sm:col-span-2' : ''}
              animate-slide-up
            `}
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="flex items-start gap-3">
              <div className={`w-8 h-8 rounded-lg bg-black/20 flex items-center justify-center flex-shrink-0 mt-0.5`}>
                <Icon className={`w-4 h-4 ${iconColor}`} />
              </div>
              <div className="flex-1 min-w-0">
                <span className={`inline-block text-xs font-semibold ${badge} px-2 py-0.5 rounded-full mb-2`}>
                  {label}
                </span>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {brief[key] || <span className="text-slate-600 italic">Not available</span>}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
