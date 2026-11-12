import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import {
  LayoutDashboard, Upload, Search, GitBranch, ShieldCheck,
  FlaskConical, FileText, BarChart3, Link2, Sparkles, PlusCircle, Menu, X,
} from 'lucide-react';

const NAV = [
  { to: '/', label: 'AI Canvas', icon: Sparkles },
  { to: '/builder', label: 'Workflow Builder', icon: PlusCircle },
  { to: '/connection', label: 'ChatGPT Connection', icon: Link2 },
  { to: '/dashboard', label: 'Executive Dashboard', icon: LayoutDashboard },
  { to: '/studio', label: 'SOP Input Studio', icon: Upload },
  { to: '/inspector', label: 'Extraction Inspector', icon: Search },
  { to: '/explorer', label: 'Workflow Explorer', icon: GitBranch },
  { to: '/verification', label: 'Verification Center', icon: ShieldCheck },
  { to: '/simulation', label: 'What-If Simulation', icon: FlaskConical },
  { to: '/reports', label: 'Audit Reports', icon: FileText },
  { to: '/evaluation', label: 'Evaluation', icon: BarChart3 },
];

export default function Layout() {
  const [open, setOpen] = useState(false);

  const sidebar = (
    <nav className="flex flex-col h-full">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 pt-5 pb-4">
        <span className="text-4xl font-light text-accent-green select-none">◈</span>
        <div className="leading-tight text-emerald-100">
          <div className="text-lg tracking-tight">Reality</div>
          <div className="text-lg font-bold tracking-tight">Compiler</div>
        </div>
      </div>
      <div className="px-5 pb-4 text-[9px] tracking-[2px] font-bold text-emerald-400/60">
        PROCESS INTELLIGENCE
      </div>
      <p className="px-5 pb-5 text-xs text-emerald-300/50 leading-relaxed">
        Understand the process.<br />See what's missing.
      </p>

      {/* Nav links */}
      <div className="flex-1 overflow-y-auto px-3 space-y-0.5">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] transition-all duration-150',
                isActive
                  ? 'bg-sidebar-active text-white shadow-sm border-l-[3px] border-accent-green'
                  : 'text-emerald-200/80 hover:bg-sidebar-hover hover:text-white border-l-[3px] border-transparent',
              )
            }
          >
            <Icon size={16} strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 flex-shrink-0 flex-col bg-sidebar border-r border-sidebar-light">
        {sidebar}
      </aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
              onClick={() => setOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25 }}
              className="fixed inset-y-0 left-0 z-50 w-64 bg-sidebar lg:hidden"
            >
              <button
                onClick={() => setOpen(false)}
                className="absolute top-4 right-4 text-emerald-300 hover:text-white"
              >
                <X size={20} />
              </button>
              {sidebar}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center gap-4 px-6 py-3 border-b border-surface-300 bg-white/80 backdrop-blur-sm">
          <button
            onClick={() => setOpen(true)}
            className="lg:hidden p-1.5 rounded-lg hover:bg-surface-200 text-muted"
          >
            <Menu size={20} />
          </button>
          <span className="text-[10px] tracking-[0.14em] font-semibold text-muted">
            REALITY COMPILER <span className="mx-3 text-surface-400">/</span> WORKSPACE
          </span>
          <div className="ml-auto">
            <span className="rc-badge bg-primary-50 text-primary-700 border border-primary-200 text-[11px]">
              Evidence-led workflows
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
