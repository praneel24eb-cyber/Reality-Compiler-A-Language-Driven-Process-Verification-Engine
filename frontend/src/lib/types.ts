// ── Types matching the FastAPI backend exactly ──

export interface Sentence {
  id: string;
  text: string;
  start?: number;
  end?: number;
}

export interface State {
  id: string;
  name: string;
  kind: 'start' | 'normal' | 'terminal';
  actor?: string | null;
  evidence: string[];
  inferred: boolean;
  inference_reason?: string | null;
}

export interface Transition {
  id: string;
  source: string;
  target: string;
  label: string;
  condition?: string | null;
  actor?: string | null;
  evidence: string[];
  inferred: boolean;
  inference_reason?: string | null;
}

export interface Process {
  states: State[];
  transitions: Transition[];
  actors: string[];
}

export interface Rule {
  protected: string;
  target?: string | null;
  evidence?: string[];
}

export interface Finding {
  severity: 'error' | 'warning' | 'info';
  type: string;
  message: string;
  location?: string;
  method?: string;
  evidence?: string[];
  counterexample_path?: string[];
}

export interface Analysis {
  source: string;
  sentences: Sentence[];
  process: Process;
  findings: Finding[];
  rules: Rule[];
  stages?: string[];
  origin?: string;
  parent_analysis_id?: string | null;
  revision_reason?: string | null;
}

export interface AnalysisResponse {
  id: string;
  created_at: string;
  analysis: Analysis;
}

export interface VisualNode {
  id: string;
  label: string;
  details?: Record<string, unknown>;
}

export interface VisualEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  details?: Record<string, unknown>;
}

export interface Visual {
  id: string;
  kind: string;
  title: string;
  note: string;
  nodes: VisualNode[];
  edges: VisualEdge[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  failed?: boolean;
}

export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
  analysis_id?: string | null;
}

export interface ChatResponse {
  answer: string;
  visuals: Visual[];
}

export interface Draft {
  id: string;
  goal: string;
  answers: string[];
  ready: boolean;
  analysis_id: string | null;
  messages: ChatMessage[];
}

export interface ChatGPTStatus {
  enabled: boolean;
  connected: boolean;
  account?: string;
  models: { slug: string; display_name: string }[];
  model: string | null;
  registrations?: { id: string; label: string; workspace_hint: string }[];
  session_persistent?: boolean;
  storage_supported?: boolean;
  storage_error?: string;
  notice?: string;
}

export interface ScenarioRequest {
  operation: string;
  element_id: string;
  label?: string;
  condition?: string | null;
}

export interface ScenarioResult {
  id: string;
  process: Process;
  new_findings: Finding[];
  resolved_findings: Finding[];
  lost_reachability: string[];
  gained_reachability: string[];
}

export interface BenchmarkCase {
  id: string;
  title: string;
}

export interface BenchmarkReport {
  methodology: string;
  limitations: string;
  cases: {
    title: string;
    plain_llm: { status: string; error?: string; metrics?: Record<string, { precision: number; recall: number; f1: number }> };
    multipass_verified: { status: string; error?: string; metrics?: Record<string, { precision: number; recall: number; f1: number }> };
  }[];
}

export interface AuditReport {
  id: string;
  created_at: string;
  analysis: Analysis;
  graph: unknown;
  scenarios: unknown[];
  methodology: string;
  limitations: string;
}
