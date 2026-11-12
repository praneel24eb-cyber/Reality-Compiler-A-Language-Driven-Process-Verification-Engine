import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, FileSearch, MessageSquareText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AnalysisSelector from '@/components/AnalysisSelector';
import WorkflowGraph from '@/components/WorkflowGraph';
import ChatPanel from '@/components/ChatPanel';
import Badge from '@/components/Badge';
import { canvasChat, getAnalyses } from '@/lib/api';
import type { AnalysisResponse, ChatMessage } from '@/lib/types';

export default function Builder() {
  const [analyses, setAnalyses] = useState<AnalysisResponse[]>([]);
  const [row, setRow] = useState<AnalysisResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const nav = useNavigate();

  useEffect(() => {
    getAnalyses().then(items => {
      setAnalyses(items);
      if (items.length) setRow(items[0]);
    }).catch(e => setError(e?.response?.data?.detail || e?.message || 'Could not load saved SOPs.'));
  }, []);

  const selectAnalysis = (_id: string, selected: AnalysisResponse) => {
    setRow(selected);
    setMessages([]);
    setError('');
  };

  const askCompiler = async (query: string) => {
    if (!row) return;
    setLoading(true);
    setError('');
    try {
      const history = messages.slice(-12).map(m => ({ role: m.role, content: m.content }));
      const reply = await canvasChat(query, history, row.id);
      setMessages(previous => [
        ...previous,
        { role: 'user', content: query },
        { role: 'assistant', content: reply.answer },
      ]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'The compiler could not answer this query.');
    } finally {
      setLoading(false);
    }
  };

  const findings = row?.analysis.findings.filter(f => f.severity !== 'info') ?? [];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <MessageSquareText className="text-primary-500" /> Workflow Builder
      </h1>
      <p className="text-sm text-muted">Ask the compiler in your own words. It checks the selected company SOP, shows its workflow, and flags structural gaps.</p>

      <div className="rc-card p-5 space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold"><FileSearch size={17} className="text-primary-500" /> Company SOP</div>
        {analyses.length ? (
          <AnalysisSelector value={row?.id ?? null} onChange={selectAnalysis} />
        ) : (
          <div className="text-sm text-muted">No saved SOPs yet. Upload one in SOP Input Studio first.</div>
        )}
        {row && <p className="text-xs text-muted line-clamp-2">{row.analysis.source.slice(0, 360)}</p>}
        {!analyses.length && <button onClick={() => nav('/studio')} className="rc-btn-primary text-xs">Open SOP Input Studio <ArrowRight size={14} /></button>}
      </div>

      {row && (
        <>
          <ChatPanel messages={messages} onSend={askCompiler} loading={loading} error={error} maxLength={6000} />
          <div className="rc-card p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Verified workflow from this SOP</h2>
              <p className="text-xs text-muted mt-1">The graph and structural findings are computed from the selected saved analysis.</p>
            </div>
            <button onClick={() => nav('/explorer')} className="rc-btn-ghost text-xs">Inspect evidence <ArrowRight size={14} /></button>
          </div>
          <WorkflowGraph process={row.analysis.process} />
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Structural and review findings ({findings.length})</h2>
            {findings.length ? findings.map(f => (
              <div key={f.severity + f.type + f.message} className="rc-card p-3 flex items-start gap-3">
                <Badge variant={f.severity}>{f.severity.toUpperCase()}</Badge>
                <div>
                  <p className="text-sm">{f.message}</p>
                  {f.counterexample_path?.length ? <p className="text-xs text-muted mt-1">Path: {f.counterexample_path.join(' → ')}</p> : null}
                </div>
              </div>
            )) : <p className="text-sm text-muted">No structural findings were reported for this saved analysis.</p>}
          </section>
        </>
      )}
    </motion.div>
  );
}
