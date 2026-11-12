import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, AlertTriangle } from 'lucide-react';
import AnalysisSelector from '@/components/AnalysisSelector';
import WorkflowGraph from '@/components/WorkflowGraph';
import Badge from '@/components/Badge';
import ErrorCard from '@/components/ErrorCard';
import { getReport } from '@/lib/api';
import type { AnalysisResponse, AuditReport } from '@/lib/types';

export default function Reports() {
  const [row, setRow] = useState<AnalysisResponse | null>(null);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async (id: string, r: AnalysisResponse) => {
    setRow(r); setLoading(true); setError('');
    try { setReport(await getReport(id)); }
    catch (e: any) { setError(e?.response?.data?.detail || e?.message || 'Failed to load report'); }
    finally { setLoading(false); }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <FileText className="text-primary-500" /> Audit Report Center
      </h1>
      <AnalysisSelector value={row?.id ?? null} onChange={load} />

      {loading && <div className="space-y-3"><div className="rc-skeleton h-16 w-full" /><div className="rc-skeleton h-64 w-full" /></div>}
      {error && <ErrorCard message={error} />}

      {report && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          <details className="rc-card px-4 py-3">
            <summary className="text-xs font-semibold text-muted cursor-pointer">About this report and its scope</summary>
            <p className="text-xs text-muted leading-relaxed mt-3">{report.limitations}</p>
          </details>

          {/* Original SOP */}
          <details className="rc-card">
            <summary className="px-5 py-3 text-sm font-semibold cursor-pointer hover:bg-surface-50 transition-colors">
              Original SOP / query
            </summary>
            <pre className="px-5 py-4 text-xs text-ink whitespace-pre-wrap border-t border-surface-200 bg-surface-50 max-h-64 overflow-y-auto">
              {report.analysis.source}
            </pre>
          </details>

          {/* Workflow graph */}
          <div>
            <h2 className="text-sm font-semibold mb-2">Workflow</h2>
            <WorkflowGraph process={report.analysis.process} />
          </div>

          {/* Findings */}
          <div>
            <h2 className="text-sm font-semibold mb-2">Findings ({report.analysis.findings.length})</h2>
            <div className="space-y-2">
              {report.analysis.findings.map((f, i) => (
                <div key={i} className="rc-card p-3 flex items-start gap-3">
                  <Badge variant={f.severity}>{f.severity.toUpperCase()}</Badge>
                  <p className="text-sm text-ink">{f.message}</p>
                </div>
              ))}
              {!report.analysis.findings.length && <p className="text-sm text-muted italic">No findings</p>}
            </div>
          </div>

          {/* Methodology */}
          <div className="rc-card p-5">
            <h2 className="text-sm font-semibold mb-2">Methodology</h2>
            <p className="text-sm text-muted leading-relaxed">{report.methodology}</p>
          </div>

          {/* Download */}
          <button
            onClick={() => {
              const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = 'audit-report.json'; a.click();
              URL.revokeObjectURL(url);
            }}
            className="rc-btn-primary"
          >
            <Download size={16} /> Download Audit Report
          </button>
        </motion.div>
      )}
    </motion.div>
  );
}
