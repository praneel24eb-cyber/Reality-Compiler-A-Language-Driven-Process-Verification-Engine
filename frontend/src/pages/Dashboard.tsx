import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { LayoutDashboard, AlertTriangle, AlertCircle, Info, Link2, ArrowRight } from 'lucide-react';
import MetricCard from '@/components/MetricCard';
import ErrorCard from '@/components/ErrorCard';
import { getAnalyses } from '@/lib/api';
import type { AnalysisResponse } from '@/lib/types';

const COLORS = { error: '#dc2626', warning: '#d97706', info: '#2563eb' };

export default function Dashboard() {
  const [rows, setRows] = useState<AnalysisResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const nav = useNavigate();

  useEffect(() => { getAnalyses().then(setRows).catch(e => setError(e.message)).finally(() => setLoading(false)); }, []);

  if (loading) return <div className="space-y-4 animate-fade-in"><div className="rc-skeleton h-10 w-72" /><div className="grid grid-cols-3 gap-4">{[1,2,3].map(i=><div key={i} className="rc-skeleton h-28" />)}</div></div>;
  if (error) return <ErrorCard message={error} onRetry={() => window.location.reload()} />;

  const findings = rows.flatMap(r => r.analysis.findings);
  const counts = { error: 0, warning: 0, info: 0 };
  findings.forEach(f => { counts[f.severity]++; });
  const pieData = Object.entries(counts).filter(([,v]) => v > 0).map(([k,v]) => ({ name: k, value: v }));

  let linked = 0, total = 0;
  rows.forEach(r => {
    const ids = new Set(r.analysis.sentences.map(s => s.id));
    [...r.analysis.process.states, ...r.analysis.process.transitions].forEach(el => {
      total++; if (el.evidence.length && el.evidence.every(e => ids.has(e))) linked++;
    });
  });

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3"><LayoutDashboard className="text-primary-500" /> Executive Dashboard</h1>
        <button onClick={() => nav('/studio')} className="rc-btn-primary">Analyze SOP <ArrowRight size={16} /></button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Saved Workflows" value={rows.length} accent="bg-primary-50 text-primary-500" icon={<LayoutDashboard size={20} />} />
        <MetricCard label="Total Findings" value={findings.length} accent="bg-amber-50 text-amber-500" icon={<AlertTriangle size={20} />} />
        <MetricCard label="Valid Evidence Links" value={`${linked}/${total}`} accent="bg-blue-50 text-blue-500" icon={<Link2 size={20} />} />
        <div className="rc-card p-5 flex items-center justify-center">
          {pieData.length > 0 ? (
            <ResponsiveContainer width={120} height={120}>
              <PieChart><Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={30} outerRadius={50} paddingAngle={3} strokeWidth={0}>{pieData.map(d=><Cell key={d.name} fill={COLORS[d.name as keyof typeof COLORS]} />)}</Pie><Tooltip /></PieChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-muted italic">No findings</p>}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {([['error','Errors',AlertCircle,'border-l-red-400 bg-red-50/40'],['warning','Warnings',AlertTriangle,'border-l-amber-400 bg-amber-50/40'],['info','Info',Info,'border-l-blue-400 bg-blue-50/40']] as const).map(([key,lbl,Icon,cls])=>(
          <div key={key} className={`rc-card border-l-4 ${cls} p-5 flex items-center gap-4`}><Icon size={20} className="text-muted" /><div><p className="text-xs text-muted uppercase tracking-wider font-medium">{lbl}</p><p className="text-2xl font-bold">{counts[key]}</p></div></div>
        ))}
      </div>
      {total > 0 && (<div className="rc-card p-5"><div className="flex justify-between text-sm mb-2"><span className="font-medium">Evidence Coverage</span><span className="text-muted">{linked}/{total} ({Math.round(linked/total*100)}%)</span></div><div className="h-2.5 bg-surface-200 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-primary-400 to-primary-600 rounded-full transition-all duration-500" style={{width:`${(linked/total)*100}%`}} /></div></div>)}
      <div className="rc-card overflow-hidden">
        <div className="px-5 py-3 border-b border-surface-200 bg-surface-50"><h2 className="text-sm font-semibold">Recent Workflows</h2></div>
        {rows.slice(0,10).map(r=>{const src=r.analysis.source.replace(/\s+/g,' ');return(
          <div key={r.id} className="px-5 py-3 border-b border-surface-100 hover:bg-surface-50 cursor-pointer transition-colors flex items-center justify-between" onClick={()=>nav('/explorer')}>
            <span className="text-sm text-ink truncate max-w-[70%]">{src.slice(0,100)}{src.length>100?'…':''}</span>
            <span className="text-xs text-muted">{r.analysis.process.states.length} steps · {r.analysis.process.transitions.length} transitions</span>
          </div>);})}
        {!rows.length && <p className="p-5 text-sm text-muted italic">No workflows yet.</p>}
      </div>
    </motion.div>
  );
}
