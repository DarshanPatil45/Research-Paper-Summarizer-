import { useState, useEffect, useCallback } from 'react';
import { Microscope, Wifi, WifiOff, RotateCcw, AlertOctagon, ExternalLink } from 'lucide-react';
import { DropZone, FileCard } from './components/UploadZone';
import { ProgressPanel } from './components/ProgressPanel';
import { BriefPanel } from './components/BriefPanel';
import { EvidencePanel } from './components/EvidencePanel';
import { ResultsHeader } from './components/ResultsHeader';
import { useAnalysis } from './hooks/useAnalysis';
import type { BackendStatus } from './types';

function StatusPill({ status }: { status: BackendStatus | null }) {
  if (!status) return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <div className="w-2 h-2 rounded-full bg-slate-600 animate-pulse" />
      Checking backend…
    </div>
  );

  return status.ok ? (
    <div className="flex items-center gap-2 text-xs text-emerald-400">
      <Wifi className="w-3.5 h-3.5" />
      <span>Ollama running · <span className="font-mono">{status.model}</span></span>
    </div>
  ) : (
    <div className="flex items-center gap-2 text-xs text-red-400">
      <WifiOff className="w-3.5 h-3.5" />
      <span>Ollama offline</span>
    </div>
  );
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);
  const { state, events, result, error, currentStep, totalSteps, analyze, reset } = useAnalysis();

  // Poll backend health
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        setBackendStatus(data);
      } catch {
        setBackendStatus({ ok: false, model: '', error: 'Cannot reach backend' });
      }
    };
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);

  const handleFile = useCallback((f: File) => {
    reset();
    setFile(f);
  }, [reset]);

  const handleRemove = useCallback(() => {
    reset();
    setFile(null);
  }, [reset]);

  const handleAnalyze = () => {
    if (file) analyze(file);
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.filename.replace('.pdf', '')}_analysis.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const fileStatus = state === 'uploading' || state === 'analyzing' ? 'processing'
    : state === 'done' ? 'done'
    : state === 'error' ? 'error'
    : 'ready';

  const isProcessing = state === 'uploading' || state === 'analyzing';
  const canAnalyze = file !== null && !isProcessing && state !== 'done' && backendStatus?.ok;

  return (
    <div className="min-h-screen bg-[#0a0a14] text-slate-200">
      {/* Background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden>
        <div className="absolute top-[-20%] left-[20%] w-[600px] h-[600px] rounded-full bg-indigo-900/20 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[10%] w-[500px] h-[500px] rounded-full bg-violet-900/20 blur-[120px]" />
      </div>

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Header */}
        <header className="mb-10">
          <div className="flex items-center justify-between flex-wrap gap-4 mb-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Microscope className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gradient leading-none">PaperLens</h1>
                <p className="text-xs text-slate-500 mt-0.5">AI Research Summarizer</p>
              </div>
            </div>
            <StatusPill status={backendStatus} />
          </div>

          <div className="space-y-2">
            <h2 className="text-3xl sm:text-4xl font-extrabold leading-tight">
              Understand any{' '}
              <span className="text-gradient">research paper</span>{' '}
              in minutes
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed max-w-xl">
              Upload a PDF and get a structured brief — Problem, Method, Results, Limitations, and Takeaway —
              with every key claim verified against the source text. Runs entirely on your machine.
            </p>
          </div>
        </header>

        {/* Backend offline banner */}
        {backendStatus && !backendStatus.ok && (
          <div className="mb-6 flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 animate-fade-in">
            <AlertOctagon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold text-red-300 mb-1">Ollama is not running</p>
              <p className="text-red-400/70 text-xs font-mono">
                {backendStatus.error || 'Start Ollama with: ollama serve'}
              </p>
              <p className="text-red-400/70 text-xs mt-1">
                Then pull the model:{' '}
                <code className="bg-black/30 px-1 rounded">ollama pull llama3.2:3b</code>
              </p>
            </div>
          </div>
        )}

        {/* Upload section */}
        {state === 'idle' || state === 'error' ? (
          <section className="space-y-4 mb-6">
            {!file ? (
              <DropZone onFile={handleFile} disabled={isProcessing} />
            ) : (
              <FileCard
                filename={file.name}
                fileSize={file.size}
                status={fileStatus}
                onRemove={handleRemove}
              />
            )}

            {file && (state === 'idle' || state === 'error') && (
              <button
                id="analyze-btn"
                onClick={handleAnalyze}
                disabled={!canAnalyze}
                className={`
                  w-full py-3.5 rounded-xl font-semibold text-sm transition-all duration-200
                  ${canAnalyze
                    ? 'bg-gradient-to-r from-indigo-500 via-violet-500 to-purple-600 hover:from-indigo-400 hover:via-violet-400 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 hover:scale-[1.01] active:scale-[0.99]'
                    : 'bg-white/5 text-slate-600 cursor-not-allowed border border-white/5'
                  }
                `}
              >
                {isProcessing ? 'Analysing…' : '✨ Analyse Paper'}
              </button>
            )}

            {/* Error state */}
            {state === 'error' && error && (
              <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 animate-fade-in">
                <AlertOctagon className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-red-300 font-medium mb-1">Analysis failed</p>
                  <p className="text-xs text-red-400/70 whitespace-pre-wrap break-words">{error}</p>
                </div>
                <button
                  id="retry-btn"
                  onClick={handleRemove}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors flex-shrink-0"
                >
                  <RotateCcw className="w-3 h-3" /> Reset
                </button>
              </div>
            )}

            {/* Sample PDF hint */}
            {!file && (
              <p className="text-center text-xs text-slate-600">
                No paper? Try the{' '}
                <a
                  id="sample-pdf-link"
                  href="/api/sample"
                  download
                  className="text-indigo-400 hover:text-indigo-300 transition-colors inline-flex items-center gap-1"
                >
                  synthetic sample PDF
                  <ExternalLink className="w-3 h-3" />
                </a>
                {' '}(labelled as synthetic)
              </p>
            )}
          </section>
        ) : null}

        {/* Processing state */}
        {isProcessing && (
          <div className="mb-6">
            <ProgressPanel
              events={events}
              currentStep={currentStep}
              totalSteps={totalSteps}
            />
          </div>
        )}

        {/* Results */}
        {state === 'done' && result && (
          <div className="space-y-6">
            {/* File card still shown at top */}
            {file && (
              <FileCard
                filename={file.name}
                fileSize={file.size}
                status="done"
                onRemove={handleRemove}
              />
            )}

            <ResultsHeader result={result} onDownload={handleDownload} />
            <BriefPanel brief={result.brief} />
            <EvidencePanel claims={result.claim_checks} />

            {/* Analyse another */}
            <div className="flex justify-center pt-2">
              <button
                id="analyse-another-btn"
                onClick={handleRemove}
                className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Analyse another paper
              </button>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-white/5 text-center">
          <p className="text-xs text-slate-700">
            Runs locally · No data leaves your machine · Powered by Ollama + ChromaDB + Sentence Transformers
          </p>
        </footer>
      </div>
    </div>
  );
}
