import { motion, AnimatePresence } from 'framer-motion';
import { X, User, GitBranch, AlertTriangle, Quote } from 'lucide-react';
import Badge from './Badge';

interface Props {
  open: boolean;
  onClose: () => void;
  data: Record<string, any> | null;
  isEdge?: boolean;
  names?: Record<string, string>;
  sentences?: { id: string; text: string }[];
}

export default function DetailDrawer({ open, onClose, data, isEdge, names = {}, sentences = [] }: Props) {
  if (!data) return null;
  const evidence = (data.evidence as string[]) || [];
  const ledger = Object.fromEntries(sentences.map(s => [s.id, s.text]));

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px]"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: 380 }}
            animate={{ x: 0 }}
            exit={{ x: 380 }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="fixed top-0 right-0 z-50 h-full w-[360px] bg-white border-l border-surface-300 shadow-xl overflow-y-auto"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-surface-200">
              <h3 className="text-sm font-semibold text-ink">
                {isEdge ? 'Connection Details' : 'Step Details'}
              </h3>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-200 text-muted">
                <X size={16} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Name / Connection */}
              <div>
                <label className="text-[10px] tracking-wider font-bold text-muted uppercase">
                  {isEdge ? 'Connection' : 'Step'}
                </label>
                <p className="text-sm font-medium text-ink mt-1">
                  {isEdge
                    ? `${names[data.source as string] || String(data.source)} → ${names[data.target as string] || String(data.target)}`
                    : String(data.name ?? '')}
                </p>
              </div>

              {/* Type / Kind */}
              {data.kind && (
                <div className="flex items-center gap-2">
                  <GitBranch size={14} className="text-muted" />
                  <Badge variant={String(data.kind)}>
                    {String(data.kind).toUpperCase()}
                  </Badge>
                </div>
              )}

              {/* Condition */}
              {(data.condition || (isEdge && data.label)) && (
                <div>
                  <label className="text-[10px] tracking-wider font-bold text-muted uppercase">Condition</label>
                  <p className="text-sm text-ink mt-1">{String(data.condition || data.label)}</p>
                </div>
              )}

              {/* Actor */}
              <div className="flex items-center gap-2">
                <User size={14} className="text-muted" />
                <span className="text-sm text-ink">{(data.actor as string) || 'Not stated'}</span>
              </div>

              {/* Inferred */}
              {typeof data.inferred === 'boolean' && (
                <div className="flex items-center gap-2">
                  {data.inferred && <AlertTriangle size={14} className="text-amber-500" />}
                  <Badge variant={data.inferred ? 'yes' : 'no'}>
                    {data.inferred ? 'Inferred — review required' : 'Directly extracted'}
                  </Badge>
                </div>
              )}
              {data.inference_reason && (
                <p className="text-xs text-muted italic">{data.inference_reason as string}</p>
              )}

              {/* Evidence */}
              {evidence.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Quote size={14} className="text-primary-500" />
                    <label className="text-[10px] tracking-wider font-bold text-muted uppercase">Source Evidence</label>
                  </div>
                  {evidence.map((ref, i) => (
                    <blockquote
                      key={i}
                      className="text-xs text-primary-800 bg-primary-50 border-l-2 border-primary-300
                                 rounded-r-lg px-3 py-2 mb-2 leading-relaxed"
                    >
                      {ledger[ref] || 'Source passage unavailable'}
                    </blockquote>
                  ))}
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
