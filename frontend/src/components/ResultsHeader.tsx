import type { AnalysisResult } from '../types';
import { Download, FileText, Hash, Layers, Cpu } from 'lucide-react';

interface ResultsHeaderProps {
  result: AnalysisResult;
  onDownload: () => void;
}

export function ResultsHeader({ result, onDownload }: ResultsHeaderProps) {
  const stats = [
    { label: 'Pages', value: result.pages, icon: FileText },
    { label: 'Words', value: result.words.toLocaleString(), icon: Hash },
    { label: 'Chunks', value: result.chunks, icon: Layers },
    { label: 'Model', value: result.model, icon: Cpu },
  ];

  return (
    <div id="results-header" className="glass rounded-2xl p-5 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
            <FileText className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="min-w-0">
            <p className="text-xs text-slate-500">Analysed paper</p>
            <p className="text-sm font-semibold text-slate-200 truncate max-w-xs">{result.filename}</p>
          </div>
        </div>
        <button
          id="download-json-btn"
          onClick={onDownload}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20
            border border-indigo-500/20 hover:border-indigo-500/40 text-indigo-300 text-sm font-medium
            transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
        >
          <Download className="w-4 h-4" />
          Download JSON
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-black/20 rounded-xl px-3 py-3 flex items-center gap-2.5">
            <Icon className="w-4 h-4 text-slate-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-slate-600">{label}</p>
              <p className="text-sm font-semibold text-slate-200 truncate">{value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
