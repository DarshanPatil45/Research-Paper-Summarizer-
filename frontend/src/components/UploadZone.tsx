import React, { useState, useCallback, useRef } from 'react';
import { Upload, FileText, X, CheckCircle, AlertTriangle } from 'lucide-react';

interface DropZoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function DropZone({ onFile, disabled }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please upload a PDF file.');
      return;
    }
    onFile(file);
  }, [onFile]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);

  const onClick = () => !disabled && inputRef.current?.click();

  return (
    <div
      id="pdf-dropzone"
      onClick={onClick}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      className={`
        relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 cursor-pointer
        ${dragging ? 'border-indigo-400 bg-indigo-500/10' : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/[0.02]'}
        ${disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        id="pdf-file-input"
        accept=".pdf"
        className="hidden"
        onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        disabled={disabled}
      />
      <div className="flex flex-col items-center gap-4">
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-200
          ${dragging ? 'bg-indigo-500/20 scale-110' : 'bg-white/5'}`}>
          <Upload className={`w-8 h-8 ${dragging ? 'text-indigo-400' : 'text-slate-400'}`} />
        </div>
        <div>
          <p className="text-lg font-medium text-slate-200 mb-1">
            Drop your PDF here
          </p>
          <p className="text-sm text-slate-500">
            or{' '}
            <span className="text-indigo-400 font-medium hover:text-indigo-300 transition-colors">
              browse to upload
            </span>
          </p>
        </div>
        <p className="text-xs text-slate-600 bg-white/[0.03] px-4 py-2 rounded-full border border-white/5">
          PDF with selectable text • Scanned PDFs not supported
        </p>
      </div>
    </div>
  );
}

interface FileCardProps {
  filename: string;
  fileSize?: number;
  status?: 'ready' | 'processing' | 'done' | 'error';
  onRemove: () => void;
}

export function FileCard({ filename, fileSize, status = 'ready', onRemove }: FileCardProps) {
  const statusConfig = {
    ready: { icon: <FileText className="w-5 h-5 text-indigo-400" />, text: 'Ready', color: 'text-indigo-400' },
    processing: { icon: <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />, text: 'Analyzing…', color: 'text-indigo-300' },
    done: { icon: <CheckCircle className="w-5 h-5 text-emerald-400" />, text: 'Complete', color: 'text-emerald-400' },
    error: { icon: <AlertTriangle className="w-5 h-5 text-red-400" />, text: 'Error', color: 'text-red-400' },
  };
  const cfg = statusConfig[status];

  return (
    <div id="file-card" className="flex items-center gap-4 glass rounded-xl px-4 py-3 animate-fade-in">
      <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
        {cfg.icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">{filename}</p>
        <p className={`text-xs ${cfg.color} flex items-center gap-1.5 mt-0.5`}>
          {cfg.text}
          {fileSize && status === 'ready' && (
            <span className="text-slate-600">• {(fileSize / 1024).toFixed(0)} KB</span>
          )}
        </p>
      </div>
      <button
        id="remove-file-btn"
        onClick={onRemove}
        disabled={status === 'processing'}
        className="p-1.5 rounded-lg hover:bg-white/10 text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        title="Remove file"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
