import { useState, useRef, useEffect } from 'react';
import clsx from 'clsx';
import { Send, Loader2, Sparkles } from 'lucide-react';
import type { ChatMessage } from '@/lib/types';

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  loading?: boolean;
  error?: string;
  maxLength?: number;
  prompts?: string[];
  className?: string;
}

export default function ChatPanel({ messages, onSend, loading, error, maxLength = 6000, prompts, className }: Props) {
  const [text, setText] = useState('');
  const bottom = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const submit = () => {
    const msg = text.trim();
    if (!msg || loading) return;
    onSend(msg);
    setText('');
  };

  return (
    <div className={clsx('flex flex-col bg-white rounded-xl border border-surface-300 shadow-card overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-200 bg-surface-50">
        <Sparkles size={16} className="text-primary-500" />
        <span className="text-xs font-semibold tracking-wide text-muted">YOUR PROCESS COPILOT</span>
      </div>
      <p className="px-4 pt-2 text-[11px] text-muted">Ask. Explore. Make the next step clear.</p>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px] max-h-[400px]">
        {!messages.length && (
          <div className="text-center pt-8">
            <h3 className="text-lg font-semibold text-ink mb-2">Start with a question.</h3>
            <p className="text-sm text-muted mb-5">
              I can explain your workflow, surface gaps, or map the ideas behind it.
            </p>
            {prompts && (
              <div className="flex flex-wrap justify-center gap-2">
                {prompts.map(p => (
                  <button
                    key={p}
                    onClick={() => { setText(p); inputRef.current?.focus(); }}
                    className="text-xs px-3 py-1.5 rounded-full border border-surface-300 bg-surface-50
                               text-muted hover:border-primary-400 hover:text-primary-600 hover:bg-primary-50
                               transition-all duration-150"
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={clsx('flex flex-col', msg.role === 'user' ? 'items-end' : 'items-start')}>
            <span className="text-[9px] tracking-wider font-bold text-muted/60 mb-1 uppercase">
              {msg.role === 'user' ? 'YOU' : 'COMPILER'}
            </span>
            <div className={clsx(
              'rounded-xl px-3.5 py-2.5 text-[12px] leading-relaxed max-w-[85%] whitespace-pre-wrap',
              msg.role === 'user'
                ? 'bg-primary-50 text-ink rounded-br-sm'
                : 'bg-surface-100 text-ink rounded-bl-sm border border-surface-300',
              msg.failed && 'opacity-50',
            )}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-muted text-xs">
            <Loader2 size={14} className="animate-spin" />
            Preparing your response…
          </div>
        )}

        {error && (
          <div className="text-xs text-red-600 bg-red-50 rounded-lg p-3 border border-red-200">
            {error}
          </div>
        )}

        <div ref={bottom} />
      </div>

      {/* Input */}
      <form
        onSubmit={e => { e.preventDefault(); submit(); }}
        className="p-3 border-t border-surface-200 space-y-2"
      >
        <textarea
          ref={inputRef}
          value={text}
          onChange={e => setText(e.target.value)}
          maxLength={maxLength}
          placeholder="Ask a question about your process…"
          className="rc-input resize-y min-h-[60px] text-xs"
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
        />
        <button type="submit" disabled={!text.trim() || loading} className="rc-btn-primary w-full text-xs">
          <Send size={14} />
          Send message
        </button>
      </form>
    </div>
  );
}
