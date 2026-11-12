import clsx from 'clsx';

const STYLES: Record<string, string> = {
  error: 'bg-red-50 text-red-700 border-red-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  start: 'bg-green-50 text-green-700 border-green-200',
  normal: 'bg-gray-50 text-gray-600 border-gray-200',
  terminal: 'bg-teal-50 text-teal-700 border-teal-200',
  yes: 'bg-amber-50 text-amber-700 border-amber-200',
  no: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  default: 'bg-surface-200 text-muted border-surface-300',
};

interface Props {
  variant?: string;
  children: React.ReactNode;
  className?: string;
}

export default function Badge({ variant = 'default', children, className }: Props) {
  return (
    <span className={clsx('rc-badge border', STYLES[variant] || STYLES.default, className)}>
      {children}
    </span>
  );
}
