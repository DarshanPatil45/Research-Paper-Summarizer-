import { useState } from 'react';
import type { ClaimCheck } from '../types';
import { ChevronDown, ChevronUp, CheckCircle2, AlertCircle, XCircle, MinusCircle, BookOpen, ShieldAlert } from 'lucide-react';

interface EvidencePanelProps {
  claims: ClaimCheck[];
}

const VERDICT_CONFIG = {
  'Supported': {
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
    badge: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/20',
    dot: 'bg-emerald-400',
    emoji: '✅',
  },
  'Partly supported': {
    icon: AlertCircle,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
    badge: 'bg-amber-500/15 text-amber-300 border border-amber-500/20',
    dot: 'bg-amber-400',
    emoji: '⚠️',
  },
  'Unsupported': {
    icon: MinusCircle,
    color: 'text-slate-400',
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/20',
    badge: 'bg-slate-500/15 text-slate-300 border border-slate-500/20',
    dot: 'bg-slate-400',
    emoji: '❓',
  },
  'Contradicted': {
    icon: XCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
    badge: 'bg-red-500/15 text-red-300 border border-red-500/20',
    dot: 'bg-red-400',
    emoji: '❌',
  },
} as const;

function ClaimRow({ claim, index }: { claim: ClaimCheck; index: number }) {
  const [expanded, setExpanded] = useState(claim.verdict !== 'Supported');
  const cfg = VERDICT_CONFIG[claim.verdict] || VERDICT_CONFIG['Unsupported'];
  const Icon = cfg.icon;
  const hasEvidence = Boolean(claim.evidence_quote);
  const isUnverified = hasEvidence && !claim.quote_verified;

  return (
    <div
      id={`claim-${index}`}
      className={`border ${cfg.border} rounded-xl overflow-hidden transition-all duration-200 animate-slide-up`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Header row */}
      <button
        id={`claim-toggle-${index}`}
        onClick={() => setExpanded(v => !v)}
        className={`w-full flex items-start gap-3 px-4 py-3.5 ${cfg.bg} hover:bg-white/5 transition-colors text-left`}
      >
        <Icon className={`w-4 h-4 ${cfg.color} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-400 mb-0.5">Claim {index + 1}</p>
          <p className="text-sm text-slate-200 leading-snug line-clamp-2">{claim.claim}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${cfg.badge}`}>
            {claim.verdict}
          </span>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-slate-500" />
            : <ChevronDown className="w-4 h-4 text-slate-500" />
          }
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-4 py-4 space-y-3 bg-black/20 border-t border-white/5">
          {/* Explanation */}
          {claim.explanation && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Explanation</p>
              <p className="text-sm text-slate-300 leading-relaxed">{claim.explanation}</p>
            </div>
          )}

          {/* Evidence */}
          {hasEvidence && (
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                <p className="text-xs font-semibold text-slate-400">
                  Evidence
                  {claim.page_number > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-xs">
                      p.{claim.page_number}
                    </span>
                  )}
                </p>
                {claim.quote_verified
                  ? <span className="ml-auto text-xs text-emerald-400 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> verified</span>
                  : <span className="ml-auto text-xs text-amber-400 flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> not verbatim</span>
                }
              </div>
              <blockquote className={`border-l-2 pl-3 text-sm italic leading-relaxed
                ${isUnverified ? 'border-amber-500/40 text-amber-200/60' : 'border-indigo-500/40 text-slate-300'}`}>
                "{claim.evidence_quote.replace(' [⚠ quote not verified in source text]', '')}"
              </blockquote>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function EvidencePanel({ claims }: EvidencePanelProps) {
  const counts = {
    Supported: claims.filter(c => c.verdict === 'Supported').length,
    'Partly supported': claims.filter(c => c.verdict === 'Partly supported').length,
    Unsupported: claims.filter(c => c.verdict === 'Unsupported').length,
    Contradicted: claims.filter(c => c.verdict === 'Contradicted').length,
  };

  return (
    <section id="evidence-panel" aria-label="Faithfulness Check" className="space-y-4">
      <div className="flex items-center gap-3 mb-2">
        <h2 className="text-xl font-bold text-slate-100">Faithfulness Check</h2>
        <div className="flex-1 h-px bg-gradient-to-r from-white/10 to-transparent" />
      </div>

      <p className="text-xs text-slate-500 -mt-1">
        Key claims from the brief verified against source passages.
        Quotes marked as verified were found verbatim in the extracted text.
      </p>

      {/* Summary badges */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(counts).map(([verdict, count]) => {
          if (count === 0) return null;
          const cfg = VERDICT_CONFIG[verdict as keyof typeof VERDICT_CONFIG];
          return (
            <span key={verdict} className={`text-xs px-2.5 py-1 rounded-full font-medium ${cfg.badge}`}>
              {count} {verdict}
            </span>
          );
        })}
      </div>

      {/* Claim rows */}
      <div className="space-y-2">
        {claims.map((claim, i) => (
          <ClaimRow key={i} claim={claim} index={i} />
        ))}
      </div>

      {/* Disclaimer */}
      <div className="glass rounded-xl px-4 py-3 border border-amber-500/10">
        <p className="text-xs text-slate-500">
          <span className="text-amber-400 font-semibold">⚠️ Disclaimer:</span> This check is probabilistic, not deterministic.
          It can miss subtle numerical errors or misleading paraphrasing.
          Always inspect the cited source passages for important claims.
        </p>
      </div>
    </section>
  );
}
