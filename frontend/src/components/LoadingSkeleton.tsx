import clsx from 'clsx';

interface Props { rows?: number; className?: string }

export default function LoadingSkeleton({ rows = 3, className }: Props) {
  return (
    <div className={clsx('space-y-3 animate-fade-in', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rc-skeleton h-5" style={{ width: `${70 + Math.random() * 30}%` }} />
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rc-card p-6 space-y-4 animate-fade-in">
      <div className="rc-skeleton h-6 w-48" />
      <div className="rc-skeleton h-4 w-full" />
      <div className="rc-skeleton h-4 w-3/4" />
    </div>
  );
}

export function TableSkeleton({ cols = 4, rows = 5 }: { cols?: number; rows?: number }) {
  return (
    <div className="rc-card overflow-hidden animate-fade-in">
      <div className="grid gap-px bg-surface-300" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <div key={`h-${i}`} className="bg-surface-100 p-3"><div className="rc-skeleton h-4 w-20" /></div>
        ))}
        {Array.from({ length: rows * cols }).map((_, i) => (
          <div key={`c-${i}`} className="bg-white p-3"><div className="rc-skeleton h-4" style={{ width: `${50 + Math.random() * 40}%` }} /></div>
        ))}
      </div>
    </div>
  );
}
