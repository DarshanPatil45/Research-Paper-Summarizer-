export interface Brief {
  problem: string;
  method: string;
  results: string;
  limitations: string;
  main_takeaway: string;
}

export interface ClaimCheck {
  claim: string;
  verdict: 'Supported' | 'Partly supported' | 'Unsupported' | 'Contradicted';
  evidence_quote: string;
  page_number: number;
  explanation: string;
  quote_verified: boolean;
}

export interface AnalysisResult {
  filename: string;
  pages: number;
  words: number;
  chunks: number;
  model: string;
  brief: Brief;
  claim_checks: ClaimCheck[];
}

export interface ProgressEvent {
  type: string;
  message: string;
  data: Record<string, unknown>;
  ts: number;
}

export interface BackendStatus {
  ok: boolean;
  model: string;
  error?: string;
}

export type AppState =
  | 'idle'
  | 'uploading'
  | 'analyzing'
  | 'done'
  | 'error';
