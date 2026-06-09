import { useEffect, useRef, useCallback } from 'react';
import { useAppContext } from '../context/AppContext';
import { SSE_BASE } from '../types';
import type { AgentEvent } from '../types';

/**
 * SSE 连接 Hook
 * 管理 EventSource 连接、事件解析、断开清理
 */
export function useTaskStream() {
  const { dispatch } = useAppContext();
  const eventSourceRef = useRef<EventSource | null>(null);
  const taskIdRef = useRef<string | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    taskIdRef.current = null;
  }, []);

  const connect = useCallback((taskId: string) => {
    disconnect();
    taskIdRef.current = taskId;

    function createConnection() {
      if (!taskIdRef.current) return;

      const url = `${SSE_BASE}/task/${taskIdRef.current}/stream`;
      const es = new EventSource(url);

      // agent_start 事件
      es.addEventListener('agent_start', (e) => {
        try {
          const event: AgentEvent = JSON.parse(e.data);
          dispatch({ type: 'ADD_EVENT', event });
        } catch { /* ignore parse errors */ }
      });

      // agent_done 事件
      es.addEventListener('agent_done', (e) => {
        try {
          const event: AgentEvent = JSON.parse(e.data);
          dispatch({ type: 'ADD_EVENT', event });
        } catch { /* ignore parse errors */ }
      });

      // done 事件 — 任务正常完成
      es.addEventListener('done', (e) => {
        try {
          const data = JSON.parse(e.data);
          dispatch({ type: 'TASK_DONE', finalOutput: data.final_output || '' });
        } catch {
          dispatch({ type: 'TASK_DONE', finalOutput: '' });
        }
        disconnect();
      });

      // task_error 事件 — 服务端任务执行出错
      es.addEventListener('task_error', (e) => {
        try {
          const data = JSON.parse(e.data);
          dispatch({ type: 'TASK_ERROR', error: data.content || '未知错误' });
        } catch {
          dispatch({ type: 'TASK_ERROR', error: '任务执行出错' });
        }
        disconnect();
      });

      // heartbeat 事件 — 保活，不做任何事
      es.addEventListener('heartbeat', () => {});

      // 传输层错误（非自定义 SSE error 事件）
      es.onerror = () => {
        // EventSource 在连接断开后会自动重连
        // 只有当确认无法恢复时才报错
        if (es.readyState === EventSource.CLOSED) {
          if (taskIdRef.current) {
            dispatch({
              type: 'TASK_ERROR',
              error: 'SSE 连接中断，请重试',
            });
          }
          disconnect();
        }
        // readyState === CONNECTING 说明浏览器正在重连，不报错
      };

      eventSourceRef.current = es;
    }

    createConnection();
  }, [dispatch, disconnect]);

  // 组件卸载时断开连接
  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return { connect, disconnect };
}
