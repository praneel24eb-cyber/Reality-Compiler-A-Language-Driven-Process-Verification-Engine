import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import AnalysisSelector from '@/components/AnalysisSelector';
import WorkflowGraph from '@/components/WorkflowGraph';
import ChatPanel from '@/components/ChatPanel';
import DetailDrawer from '@/components/DetailDrawer';
import { canvasChat } from '@/lib/api';
import type { AnalysisResponse, ChatMessage, State, Transition } from '@/lib/types';

export default function Canvas() {
  const [selected, setSelected] = useState<AnalysisResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [drawer, setDrawer] = useState<{ data: Record<string, unknown>; isEdge: boolean } | null>(null);

  const handleSend = useCallback(async (message: string) => {
    setLoading(true);
    setError('');
    const updated = [...messages, { role: 'user' as const, content: message }];
    setMessages(updated);
    try {
      const history = updated.filter(m => !m.failed).map(m => ({ role: m.role, content: m.content })).slice(-12);
      const reply = await canvasChat(message, history, selected?.id);
      setMessages(prev => [...prev, { role: 'assistant', content: reply.answer }]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Request failed');
      setMessages(prev => { const copy = [...prev]; copy[copy.length - 1] = { ...copy[copy.length - 1], failed: true }; return copy; });
    } finally {
      setLoading(false);
    }
  }, [messages, selected]);

  const names = selected ? Object.fromEntries(selected.analysis.process.states.map(s => [s.id, s.name])) : {};

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Canvas</h1>
          <p className="text-sm text-muted mt-1">Ask a question. Graphs and mindmaps appear automatically.</p>
        </div>
        <button onClick={() => { setMessages([]); setError(''); }} className="rc-btn-ghost text-xs">Clear board</button>
      </div>
      <div className="mb-4">
        <AnalysisSelector value={selected?.id ?? null} onChange={(_, row) => setSelected(row)} allowNull nullLabel="General conversation / mindmaps" />
      </div>
      {selected && !selected.analysis.process.transitions.length && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          This analysis has no transitions. Select a workflow with transitions for process paths.
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5">
        <ChatPanel messages={messages} onSend={handleSend} loading={loading} error={error}
          prompts={['Show the workflow', 'Map the main concepts', 'Find missing paths']}
          className="lg:sticky lg:top-0 lg:h-[calc(100vh-200px)]" />
        <div className="space-y-5">
          {selected && (
            <WorkflowGraph process={selected.analysis.process}
              onNodeClick={(s: State) => setDrawer({ data: s as any, isEdge: false })}
              onEdgeClick={(t: Transition) => setDrawer({ data: t as any, isEdge: true })} className="h-[480px]" />
          )}
          {!selected && !messages.length && (
            <div className="rc-card p-12 text-center">
              <div className="text-5xl mb-4 text-primary-300">◇</div>
              <h2 className="text-xl font-semibold text-ink mb-2">Make your process visible.</h2>
              <p className="text-sm text-muted max-w-md mx-auto">Your workflow graphs and mindmaps appear here as you explore. Select a saved workflow above, or start from a goal in Workflow Builder.</p>
            </div>
          )}
        </div>
      </div>
      <DetailDrawer open={!!drawer} onClose={() => setDrawer(null)} data={drawer?.data ?? null} isEdge={drawer?.isEdge} names={names} sentences={selected?.analysis.sentences} />
    </motion.div>
  );
}
