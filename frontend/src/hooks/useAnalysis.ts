import { useState, useCallback, useRef } from 'react';
import type { AnalysisResult, ProgressEvent, AppState } from '../types';

const API_BASE = '';  // vite proxy handles /api -> localhost:8000

export function useAnalysis() {
  const [state, setState] = useState<AppState>('idle');
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps] = useState(5);
  const esRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => {
    esRef.current?.close();
    setState('idle');
    setEvents([]);
    setResult(null);
    setError(null);
    setCurrentStep(0);
  }, []);

  const analyze = useCallback(async (file: File) => {
    reset();
    setState('uploading');
    setEvents([]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) {
        const err = await uploadRes.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }

      const { job_id } = await uploadRes.json();
      setState('analyzing');

      // Open SSE stream
      const es = new EventSource(`${API_BASE}/api/stream/${job_id}`);
      esRef.current = es;

      es.onmessage = async (e) => {
        try {
          const ev: ProgressEvent = JSON.parse(e.data);

          if (ev.type === 'terminal') {
            es.close();
            const terminalEv = ev as unknown as { type: string; status: string };
            if (terminalEv.status === 'error') {
              // Fetch error message
              const res = await fetch(`${API_BASE}/api/result/${job_id}`);
              const errData = await res.json().catch(() => ({}));
              setError(errData.detail || 'Analysis failed');
              setState('error');
            } else {
              // Fetch result
              const res = await fetch(`${API_BASE}/api/result/${job_id}`);
              if (res.ok) {
                const data: AnalysisResult = await res.json();
                setResult(data);
                setState('done');
              } else {
                const errData = await res.json().catch(() => ({}));
                setError(errData.detail || 'Failed to fetch results');
                setState('error');
              }
            }
            return;
          }

          setEvents(prev => [...prev, ev]);

          // Update step counter
          if (ev.type === 'step' && ev.data && typeof ev.data.step === 'number') {
            setCurrentStep(ev.data.step as number);
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        es.close();
        setError('Connection to backend lost. Please try again.');
        setState('error');
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setState('error');
    }
  }, [reset]);

  return { state, events, result, error, currentStep, totalSteps, analyze, reset };
}
