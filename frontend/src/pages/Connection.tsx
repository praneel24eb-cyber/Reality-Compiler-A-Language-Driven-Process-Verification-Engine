import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link2, Wifi, WifiOff, Loader2, LogOut, ExternalLink, Radio } from 'lucide-react';
import clsx from 'clsx';
import ErrorCard from '@/components/ErrorCard';
import { getChatGPTStatus, getModels, selectModel, disconnectChatGPT } from '@/lib/api';
import type { ChatGPTStatus } from '@/lib/types';

export default function Connection() {
  const [status, setStatus] = useState<ChatGPTStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modelLoading, setModelLoading] = useState(false);
  const [chosen, setChosen] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    getChatGPTStatus().then(s => { setStatus(s); setChosen(s.model); }).catch(e => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(refresh, []);

  const loadModels = async () => {
    setModelLoading(true);
    try { await getModels(); refresh(); }
    catch (e: any) { setError(e.message); }
    finally { setModelLoading(false); }
  };

  const chooseModel = async () => {
    if (!chosen) return;
    setModelLoading(true);
    try { await selectModel(chosen); refresh(); }
    catch (e: any) { setError(e.message); }
    finally { setModelLoading(false); }
  };

  const doDisconnect = async () => {
    if (!confirm('Disconnect from ChatGPT?')) return;
    try { await disconnectChatGPT(); refresh(); }
    catch (e: any) { setError(e.message); }
  };

  if (loading) return <div className="space-y-4 animate-fade-in"><div className="rc-skeleton h-10 w-72" /><div className="rc-skeleton h-48" /></div>;
  if (error && !status) return <ErrorCard message={error} onRetry={refresh} />;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 max-w-2xl">
      <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
        <Link2 className="text-primary-500" /> ChatGPT Connection
      </h1>
      <p className="text-sm text-muted">Connect your ChatGPT account to power SOP analysis and canvas chat. This uses your plan allowance.</p>

      {status && !status.enabled && (
        <div className="rc-card p-5 text-sm text-muted">Start the backend with LLM_PROVIDER=chatgpt on 127.0.0.1:8000.</div>
      )}

      {status?.enabled && (
        <div className="space-y-5">
          {/* Status card */}
          <div className={clsx('rc-card p-5 flex items-center gap-4', status.connected ? 'border-green-200' : 'border-surface-300')}>
            <div className={clsx('w-3 h-3 rounded-full', status.connected ? 'bg-green-500 animate-pulse' : 'bg-red-400')} />
            <div className="flex-1">
              <p className="text-sm font-semibold">{status.connected ? 'Connected' : 'Not connected'}</p>
              {status.connected && status.account && <p className="text-xs text-muted mt-0.5">{status.account}</p>}
              {status.session_persistent && <p className="text-[10px] text-muted mt-1">🔒 Session protected on this device</p>}
              {status.storage_error && <p className="text-[10px] text-amber-600 mt-1">{status.storage_error}</p>}
              {status.notice && !status.connected && <p className="text-xs text-muted mt-1">{status.notice}</p>}
            </div>
            {status.connected ? <Wifi size={20} className="text-green-500" /> : <WifiOff size={20} className="text-red-400" />}
          </div>

          {/* Auth buttons */}
          <div className="flex flex-wrap gap-3">
            <a href="/auth/chatgpt/start" className="rc-btn-primary"><Wifi size={16} /> Continue with ChatGPT</a>
            <a href="/auth/chatgpt/start?registration_id=new" className="rc-btn-ghost text-xs">Use a different account</a>
          </div>

          {/* Registrations */}
          {status.registrations && status.registrations.length > 1 && (
            <div className="rc-card p-4 space-y-3">
              <h3 className="text-xs font-semibold text-muted uppercase tracking-wider">Saved Registrations</h3>
              {status.registrations.map(r => (
                <a key={r.id} href={`/auth/chatgpt/start?registration_id=${r.id}`}
                  className="flex items-center gap-3 p-3 rounded-lg border border-surface-200 hover:border-primary-300 hover:bg-primary-50 transition-all">
                  <Radio size={14} className="text-primary-500" />
                  <span className="text-sm">{r.label} <span className="text-muted">(…{r.workspace_hint})</span></span>
                </a>
              ))}
            </div>
          )}

          <button onClick={refresh} className="rc-btn-ghost text-xs">Refresh status</button>

          {/* Model selector */}
          {status.connected && (
            <div className="rc-card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">ChatGPT Model</h3>
                <button onClick={loadModels} disabled={modelLoading} className="rc-btn-ghost text-xs">
                  {modelLoading ? <Loader2 size={14} className="animate-spin" /> : 'Load models'}
                </button>
              </div>

              {status.models.length > 0 ? (
                <div className="space-y-2">
                  {status.models.map(m => (
                    <label key={m.slug}
                      className={clsx(
                        'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all',
                        chosen === m.slug ? 'border-primary-400 bg-primary-50 ring-2 ring-primary-100' : 'border-surface-200 hover:border-primary-300',
                      )}>
                      <input type="radio" name="model" value={m.slug} checked={chosen === m.slug}
                        onChange={() => setChosen(m.slug)} className="text-primary-500" />
                      <span className="text-sm font-medium">{m.display_name}</span>
                    </label>
                  ))}
                  <button onClick={chooseModel} disabled={!chosen || modelLoading} className="rc-btn-primary text-xs w-full">
                    {modelLoading ? <><Loader2 size={14} className="animate-spin" /> Switching…</> : 'Use this model'}
                  </button>
                </div>
              ) : (
                <p className="text-sm text-amber-600">No models available. Check ChatGPT permissions.</p>
              )}

              <p className="text-xs text-muted">Active model: <strong>{status.model || 'Not selected'}</strong></p>
            </div>
          )}

          {/* Actions */}
          {status.connected && (
            <div className="flex flex-wrap gap-3">
              <a href="https://chatgpt.com/#settings" target="_blank" rel="noopener noreferrer" className="rc-btn-ghost text-xs">
                <ExternalLink size={14} /> Manage permissions
              </a>
              <button onClick={doDisconnect} className="rc-btn-danger text-xs"><LogOut size={14} /> Disconnect</button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
