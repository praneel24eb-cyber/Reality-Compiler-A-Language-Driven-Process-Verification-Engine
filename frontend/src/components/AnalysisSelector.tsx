import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { ChevronDown } from 'lucide-react';
import { getAnalyses } from '@/lib/api';
import type { AnalysisResponse } from '@/lib/types';

function label(row: AnalysisResponse): string {
  const src = row.analysis.source.replace(/\s+/g, ' ');
  const date = row.created_at.slice(0, 19).replace('T', ' ');
  const p = row.analysis.process;
  return `${src.slice(0, 90)}${src.length > 90 ? '…' : ''}  ·  ${p.states.length} steps, ${p.transitions.length} transitions  ·  ${date}`;
}

interface Props {
  value: string | null;
  onChange: (id: string, row: AnalysisResponse) => void;
  allowNull?: boolean;
  nullLabel?: string;
}

export default function AnalysisSelector({ value, onChange, allowNull, nullLabel = 'Select a workflow…' }: Props) {
  const [rows, setRows] = useState<AnalysisResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalyses().then(setRows).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="rc-skeleton h-10 w-full" />;
  if (!rows.length) return <p className="text-sm text-muted italic">No saved workflows. Analyze an SOP first.</p>;

  return (
    <div className="relative">
      <select
        value={value ?? ''}
        onChange={e => {
          const id = e.target.value;
          const row = rows.find(r => r.id === id);
          if (row) onChange(id, row);
        }}
        className={clsx(
          'rc-input pr-10 appearance-none cursor-pointer truncate',
          !value && 'text-muted',
        )}
      >
        {allowNull && <option value="">{nullLabel}</option>}
        {rows.map(r => (
          <option key={r.id} value={r.id}>{label(r)}</option>
        ))}
      </select>
      <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
    </div>
  );
}
