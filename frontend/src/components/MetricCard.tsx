import clsx from 'clsx';

interface Props {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  accent?: string;
  className?: string;
}

export default function MetricCard({ label: title, value, icon, accent, className }: Props) {
  return (
    <div className={clsx('rc-card p-5 flex items-start gap-4', className)}>
      {icon && (
        <div className={clsx('p-2.5 rounded-xl', accent || 'bg-primary-50 text-primary-500')}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-muted font-medium uppercase tracking-wider mb-1">{title}</p>
        <p className="text-2xl font-bold tracking-tight text-ink">{value}</p>
      </div>
    </div>
  );
}
