import { useRef, type FormEvent } from 'react';
import { useAppContext } from '../context/AppContext';
import { useTaskStream } from '../hooks/useTaskStream';
import { BACKEND_URL } from '../types';
import { Play, Square } from 'lucide-react';

export default function TaskInput() {
  const { state, dispatch } = useAppContext();
  const { connect, disconnect } = useTaskStream();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isRunning = state.taskStatus === 'running';

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const task = state.taskText.trim();
    if (!task || isRunning) return;

    try {
      const resp = await fetch(`${BACKEND_URL}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
      });

      if (!resp.ok) {
        dispatch({ type: 'TASK_ERROR', error: `后端错误: ${resp.status}` });
        return;
      }

      const data = await resp.json();
      dispatch({ type: 'SUBMIT_TASK', taskId: data.task_id, taskText: task });

      // 建立 SSE 连接
      connect(data.task_id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '连接失败';
      dispatch({ type: 'TASK_ERROR', error: msg });
    }
  }

  function handleStop() {
    disconnect();
    dispatch({ type: 'TASK_DONE', finalOutput: state.finalOutput || '' });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label htmlFor="task-input" className="block text-sm font-medium text-mentex-text-muted">
        新任务
      </label>
      <textarea
        id="task-input"
        ref={textareaRef}
        value={state.taskText}
        onChange={e => dispatch({ type: 'SET_TASK_TEXT', text: e.target.value })}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
        disabled={isRunning}
        rows={4}
        className="w-full bg-mentex-surface-secondary border border-mentex-border rounded-lg px-3 py-2 text-sm
                   text-mentex-text placeholder:text-mentex-text-muted/50
                   focus:outline-none focus:ring-2 focus:ring-mentex-accent/50 focus:border-mentex-accent
                   disabled:opacity-50 disabled:cursor-not-allowed
                   resize-none transition-colors duration-200"
        placeholder={
          '例如：\n• 写一首关于秋天的五言诗\n• 分析 AI Agent 发展趋势\n• 设计一个学生笔记 App'
        }
      />

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isRunning || !state.taskText.trim()}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg
                     bg-mentex-cta text-mentex-cta-text text-sm font-medium
                     hover:bg-mentex-cta/90 active:scale-[0.98]
                     disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100
                     transition-all duration-200 cursor-pointer"
        >
          <Play className="w-4 h-4" />
          开始执行
        </button>

        {isRunning && (
          <button
            type="button"
            onClick={handleStop}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg
                       border border-mentex-error/50 text-mentex-error text-sm font-medium
                       hover:bg-mentex-error/10 active:scale-[0.98]
                       transition-all duration-200 cursor-pointer"
          >
            <Square className="w-4 h-4" />
            停止
          </button>
        )}
      </div>
    </form>
  );
}
