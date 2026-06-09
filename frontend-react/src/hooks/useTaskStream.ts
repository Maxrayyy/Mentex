import { useEffect, useRef, useCallback } from 'react';
import { useAppContext } from '../context/AppContext';
import { BACKEND_URL } from '../types';
import type { AgentEvent } from '../types';

/**
 * SSE 连接 Hook
 * 管理 EventSource 连接、事件解析、自动重连、断开清理
 */
export function useTaskStream() {
  const { dispatch } = useAppContext();
  const eventSourceRef = useRef<EventSource | null>(null);
  const taskIdRef = useRef<string | null>(null);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    taskIdRef.current = null;
  }, []);

  const connect = useCallback((taskId: string) => {
    // 先断开旧连接
    disconnect();

    taskIdRef.current = taskId;
    const url = `${BACKEND_URL}/task/${taskId}/stream`;
    const es = new EventSource(url);

    // agent_start 事件
    es.addEventListener('agent_start', (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data);
        dispatch({ type: 'ADD_EVENT', event });
      } catch {
        // 忽略解析错误
      }
    });

    // agent_done 事件
    es.addEventListener('agent_done', (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data);
        dispatch({ type: 'ADD_EVENT', event });
      } catch {
        // 忽略解析错误
      }
    });

    // done 事件
    es.addEventListener('done', (e) => {
      try {
        const data = JSON.parse(e.data);
        dispatch({ type: 'TASK_DONE', finalOutput: data.final_output || '' });
      } catch {
        dispatch({ type: 'TASK_DONE', finalOutput: '' });
      }
      es.close();
    });

    // error 事件
    es.addEventListener('error', (e) => {
      // EventSource 的 error 事件可能是连接错误或服务端 error 事件
      // 如果 readyState 是 CLOSED，说明连接已断
      if (es.readyState === EventSource.CLOSED) {
        // 如果任务还在运行中，说明意外断连
        if (taskIdRef.current) {
          dispatch({
            type: 'TASK_ERROR',
            error: 'SSE 连接中断，请重试',
          });
        }
        return;
      }

      // 服务端发送的自定义 error 事件
      try {
        const data = JSON.parse((e as MessageEvent).data);
        dispatch({ type: 'TASK_ERROR', error: data.content || '未知错误' });
      } catch {
        // 忽略解析错误
      }
    });

    // heartbeat 事件（保持连接）
    es.addEventListener('heartbeat', () => {
      // no-op，仅用于保活
    });

    // 默认 message 事件（捕获未分类事件）
    es.onmessage = () => {
      // no-op：所有事件都通过具名 listener 处理
    };

    eventSourceRef.current = es;
  }, [dispatch, disconnect]);

  // 组件卸载时断开连接
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect };
}
