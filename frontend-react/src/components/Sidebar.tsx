import HistoryList from './HistoryList';
import { Brain } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 border-r border-mentex-border flex flex-col bg-mentex-surface">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-mentex-border">
        <Brain className="w-6 h-6 text-mentex-accent" />
        <h1 className="text-lg font-semibold font-heading tracking-tight text-mentex-text">
          Mentex
        </h1>
      </div>

      {/* 历史记录 — 占满剩余空间 */}
      <div className="flex-1 overflow-y-auto p-4">
        <HistoryList />
      </div>

    </aside>
  );
}
