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
  const esRef = useRef<EventSource | null>(null);
  const taskIdRef = useRef<string | null>(null);

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    taskIdRef.current = null;
  }, []);

  const connect = useCallback((taskId: string) => {
    // 先断开旧连接
    disconnect();
    taskIdRef.current = taskId;

    const url = `${SSE_BASE}/task/${taskId}/stream`;
    const es = new EventSource(url);

    es.onopen = () => {
      console.log('[SSE] 已连接');
    };

    // agent_start 事件
    es.addEventListener('agent_start', (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data);
        dispatch({ type: 'ADD_EVENT', event });
      } catch (err) {
        console.error('[SSE] agent_start 解析失败:', err);
      }
    });

    // agent_done 事件
    es.addEventListener('agent_done', (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data);
        dispatch({ type: 'ADD_EVENT', event });
      } catch (err) {
        console.error('[SSE] agent_done 解析失败:', err);
      }
    });

    // done 事件 — 任务正常完成
    es.addEventListener('done', (e) => {
      try {
        const data = JSON.parse(e.data);
        dispatch({ type: 'TASK_DONE', finalOutput: data.final_output || '' });
      } catch (err) {
        console.error('[SSE] done 解析失败:', err);
        dispatch({ type: 'TASK_DONE', finalOutput: '' });
      }
      disconnect();
    });

    // task_error 事件 — 服务端任务执行出错
    es.addEventListener('task_error', (e) => {
      try {
        const data = JSON.parse(e.data);
        dispatch({ type: 'TASK_ERROR', error: data.content || '未知错误' });
      } catch (err) {
        console.error('[SSE] task_error 解析失败:', err);
        dispatch({ type: 'TASK_ERROR', error: '任务执行出错' });
      }
      disconnect();
    });

    // heartbeat 事件 — 保活
    es.addEventListener('heartbeat', () => {});

    // 传输层错误（非自定义 SSE error 事件）
    es.onerror = () => {
      console.error('[SSE] 传输层错误, readyState:', es.readyState);
      if (es.readyState === EventSource.CLOSED) {
        if (taskIdRef.current) {
          dispatch({
            type: 'TASK_ERROR',
            error: 'SSE 连接中断，请重试',
          });
        }
        disconnect();
      }
      // readyState === CONNECTING 说明浏览器正在重连
    };

    esRef.current = es;
  }, [dispatch, disconnect]);

  // 组件卸载时断开连接
  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return { connect, disconnect };
}
