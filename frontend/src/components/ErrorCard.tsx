import { AlertTriangle } from 'lucide-react';

interface Props { message: string; onRetry?: () => void }

export default function ErrorCard({ message, onRetry }: Props) {
  return (
    <div className="rc-card border-red-200 bg-red-50/50 p-5 flex items-start gap-3 animate-fade-in">
      <AlertTriangle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-red-800 font-medium">Something went wrong</p>
        <p className="text-sm text-red-600 mt-1">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="rc-btn-ghost text-xs flex-shrink-0">
          Retry
        </button>
      )}
    </div>
  );
}
