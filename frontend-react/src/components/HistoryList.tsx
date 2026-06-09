import { useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import { BACKEND_URL } from '../types';
import type { HistoryItem } from '../types';
import { Clock, RotateCcw, ChevronRight } from 'lucide-react';

export default function HistoryList() {
  const { state, dispatch } = useAppContext();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const resp = await fetch(`${BACKEND_URL}/history`);
        if (resp.ok && !cancelled) {
          const data = await resp.json();
          dispatch({ type: 'SET_HISTORY', history: data });
        }
      } catch {
        // 后端未启动时静默失败
      }
    }

    load();

    if (state.taskStatus === 'done' || state.taskStatus === 'error') {
      load();
    }

    return () => { cancelled = true; };
  }, [state.taskStatus, dispatch]);

  function handleRerun(item: HistoryItem) {
    dispatch({ type: 'SET_TASK_TEXT', text: item.task });
  }

  if (state.history.length === 0) {
    return (
      <div className="text-center py-12">
        <Clock className="w-8 h-8 text-mentex-text-muted/20 mx-auto mb-3" />
        <p className="text-sm text-mentex-text-muted">暂无历史记录</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {state.history.map(item => (
        <div
          key={item.id}
          className="group flex items-center gap-2 px-3 py-2 rounded-lg
                     hover:bg-mentex-surface-secondary transition-colors duration-200
                     cursor-pointer"
          onClick={() => handleRerun(item)}
        >
          <ChevronRight className="w-3.5 h-3.5 text-mentex-text-muted/40 flex-shrink-0
                                    group-hover:text-mentex-accent transition-colors duration-200" />
          <span className="text-sm text-mentex-text/70 truncate flex-1 group-hover:text-mentex-text
                           transition-colors duration-200">
            {item.task.slice(0, 40)}{item.task.length > 40 ? '...' : ''}
          </span>
          <RotateCcw className="w-3.5 h-3.5 text-mentex-text-muted/20 flex-shrink-0
                                 opacity-0 group-hover:opacity-100 transition-all duration-200" />
        </div>
      ))}
    </div>
  );
}
