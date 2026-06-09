import { useAppContext } from '../context/AppContext';
import { useTaskStream } from '../hooks/useTaskStream';
import { BACKEND_URL } from '../types';
import WelcomeScreen from './WelcomeScreen';
import StreamingOutput from './StreamingOutput';
import FinalResult from './FinalResult';
import { Square, ArrowUp, Coins } from 'lucide-react';
import { useRef, type FormEvent } from 'react';

export default function MainContent() {
  const { state, dispatch } = useAppContext();
  const { connect, disconnect } = useTaskStream();
  const { taskStatus } = state;
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isRunning = taskStatus === 'running';

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
    <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
      {/* 状态指示器 */}
      {taskStatus !== 'idle' && (
        <div className="flex items-center gap-2 px-6 py-3 border-b border-mentex-border
                        bg-mentex-surface/80 backdrop-blur-sm">
          <StatusBadge status={taskStatus} />
          {state.totalTokens > 0 && (
            <span className="flex items-center gap-1 text-xs text-mentex-text-muted">
              <Coins className="w-3.5 h-3.5" />
              {state.totalTokens.toLocaleString()} tokens
            </span>
          )}
          {taskStatus === 'running' && state.taskText && (
            <span className="text-sm text-mentex-text-muted truncate">
              {state.taskText.slice(0, 60)}{state.taskText.length > 60 ? '...' : ''}
            </span>
          )}
        </div>
      )}

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto">
        {taskStatus === 'idle' && <WelcomeScreen />}

        {taskStatus === 'running' && (
          <StreamingOutput events={state.events} />
        )}

        {(taskStatus === 'done' || taskStatus === 'error') && (
          <FinalResult />
        )}
      </div>

      {/* 底部输入栏 */}
      <div className="flex-shrink-0 border-t border-mentex-border bg-mentex-surface px-6 py-4">
        <form onSubmit={handleSubmit} className="flex items-end gap-3 max-w-3xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={state.taskText}
              onChange={e => dispatch({ type: 'SET_TASK_TEXT', text: e.target.value })}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              disabled={isRunning}
              rows={2}
              className="w-full bg-mentex-bg border border-mentex-border rounded-xl px-4 py-3 text-sm
                         text-mentex-text placeholder:text-mentex-text-muted/50
                         focus:outline-none focus:ring-2 focus:ring-mentex-accent/30 focus:border-mentex-accent
                         disabled:opacity-50 disabled:cursor-not-allowed
                         resize-none transition-all duration-200"
              placeholder="输入任意任务，例如：写一首关于秋天的五言诗、分析 AI Agent 发展趋势..."
            />
          </div>

          <div className="flex gap-2 flex-shrink-0">
            {isRunning ? (
              <button
                type="button"
                onClick={handleStop}
                className="flex items-center justify-center gap-2 px-4 h-[46px] rounded-xl
                           border border-mentex-error/30 text-mentex-error text-sm font-medium
                           hover:bg-mentex-error/5 active:scale-[0.98]
                           transition-all duration-200 cursor-pointer"
              >
                <Square className="w-4 h-4" />
                停止
              </button>
            ) : (
              <button
                type="submit"
                disabled={!state.taskText.trim()}
                className="flex items-center justify-center gap-2 px-5 h-[46px] rounded-xl
                           bg-mentex-cta text-mentex-cta-text text-sm font-medium
                           hover:bg-mentex-cta/90 active:scale-[0.98]
                           disabled:opacity-30 disabled:cursor-not-allowed disabled:active:scale-100
                           transition-all duration-200 cursor-pointer shadow-sm"
              >
                <ArrowUp className="w-4 h-4" />
                发送
              </button>
            )}
          </div>
        </form>
      </div>
    </main>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string; dot: string }> = {
    running: {
      label: '执行中',
      className: 'text-mentex-accent border-mentex-accent/30 bg-mentex-accent/10',
      dot: 'bg-mentex-accent animate-pulse',
    },
    done: {
      label: '已完成',
      className: 'text-mentex-success border-mentex-success/30 bg-mentex-success/10',
      dot: 'bg-mentex-success',
    },
    error: {
      label: '出错',
      className: 'text-mentex-error border-mentex-error/30 bg-mentex-error/10',
      dot: 'bg-mentex-error',
    },
    idle: { label: '', className: '', dot: '' },
  };

  const c = config[status] || config.idle;
  if (!c.label) return null;

  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                      border transition-all duration-300 ${c.className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </div>
  );
}
