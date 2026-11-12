import axios from 'axios';
import type {
  AnalysisResponse, AuditReport, BenchmarkCase, BenchmarkReport,
  ChatGPTStatus, ChatResponse, Draft, ScenarioResult,
} from './types';

const api = axios.create({ baseURL: '/api', timeout: 300_000 });

// ── Analyses ──
export const getAnalyses = () => api.get<AnalysisResponse[]>('/analyses').then(r => r.data);
export const getAnalysis = (id: string) => api.get<AnalysisResponse>(`/analyses/${id}`).then(r => r.data);
export const createAnalysis = (source: string, rules: unknown[] = []) =>
  api.post<AnalysisResponse>('/analyses', { source, rules }).then(r => r.data);
export const extractPdfText = (file: File) =>
  api.post<{ source: string; page_count: number; characters: number }>(
    '/documents/pdf/text', file, { headers: { 'Content-Type': 'application/pdf' } },
  ).then(r => r.data);
export const getFindings = (id: string) => api.get(`/analyses/${id}/findings`).then(r => r.data);
export const getVersions = (id: string) => api.get<AnalysisResponse[]>(`/analyses/${id}/versions`).then(r => r.data);
export const createVersion = (id: string, payload: Record<string, unknown>) =>
  api.post<AnalysisResponse>(`/analyses/${id}/versions`, payload).then(r => r.data);

// ── Scenarios ──
export const createScenario = (id: string, payload: Record<string, unknown>) =>
  api.post<ScenarioResult>(`/analyses/${id}/scenarios`, payload).then(r => r.data);

// ── Reports ──
export const getReport = (id: string) => api.get<AuditReport>(`/analyses/${id}/report`).then(r => r.data);

// ── Canvas ──
export const canvasChat = (message: string, history: { role: string; content: string }[], analysisId?: string | null) =>
  api.post<ChatResponse>('/canvas/chat', { message, history, analysis_id: analysisId }).then(r => r.data);

// ── Drafts ──
export const getDrafts = () => api.get<Draft[]>('/drafts').then(r => r.data);
export const createDraft = (goal: string) => api.post<Draft>('/drafts', { goal }).then(r => r.data);
export const answerDraft = (id: string, turn: number, answer: string) =>
  api.post<Draft>(`/drafts/${id}/answers`, { turn, answer }).then(r => r.data);
export const compileDraft = (id: string) => api.post<AnalysisResponse>(`/drafts/${id}/compile`, {}).then(r => r.data);

// ── ChatGPT Auth ──
export const getChatGPTStatus = () => api.get<ChatGPTStatus>('/auth/chatgpt/status').then(r => r.data);
export const getModels = () => api.post<{ slug: string; display_name: string }[]>('/auth/chatgpt/models').then(r => r.data);
export const selectModel = (slug: string) => api.post('/auth/chatgpt/model', { slug }).then(r => r.data);
export const disconnectChatGPT = () => api.post('/auth/chatgpt/disconnect').then(r => r.data);

// ── Health ──
export const getHealth = () => api.get('/health').then(r => r.data);

// ── Evaluation ──
export const getEvaluationCases = () => api.get<BenchmarkCase[]>('/evaluation/cases').then(r => r.data);
export const runEvaluation = (caseIds: string[]) =>
  api.post<BenchmarkReport>('/evaluation/run', { case_ids: caseIds }).then(r => r.data);

export default api;
