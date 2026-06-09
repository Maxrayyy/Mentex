import { createContext, useContext, useReducer } from 'react';
import type { ReactNode } from 'react';
import type { AppState, AppAction, AgentState } from '../types';
import { ROLE_ORDER } from '../types';

// ═══════════════════════════════════════
// 初始状态
// ═══════════════════════════════════════
const initialState: AppState = {
  taskId: null,
  taskStatus: 'idle',
  taskText: '',
  events: [],
  finalOutput: null,
  error: null,
  history: [],
  agentNodes: ROLE_ORDER.map(role => ({
    role,
    label: role,
    status: 'pending' as const,
    content: [],
  })),
};

// ═══════════════════════════════════════
// Reducer
// ═══════════════════════════════════════
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SUBMIT_TASK':
      return {
        ...state,
        taskId: action.taskId,
        taskText: action.taskText,
        taskStatus: 'running',
        events: [],
        finalOutput: null,
        error: null,
        agentNodes: ROLE_ORDER.map(role => ({
          role,
          label: role,
          status: 'pending' as const,
          content: [],
        })),
      };

    case 'ADD_EVENT': {
      const event = action.event;
      // 更新对应 agent node 的状态
      const newNodes = state.agentNodes.map(node => {
        if (node.role === event.node) {
          const newStatus: AgentState = event.event === 'agent_start' ? 'running' : 'done';
          return {
            ...node,
            status: newStatus,
            content: [...node.content, event.content],
          };
        }
        return node;
      });

      return {
        ...state,
        events: [...state.events, event],
        agentNodes: newNodes,
      };
    }

    case 'TASK_DONE':
      return {
        ...state,
        taskStatus: 'done',
        finalOutput: action.finalOutput,
      };

    case 'TASK_ERROR':
      return {
        ...state,
        taskStatus: 'error',
        error: action.error,
      };

    case 'RESET':
      return {
        ...state,
        taskId: null,
        taskStatus: 'idle',
        taskText: '',
        events: [],
        finalOutput: null,
        error: null,
        agentNodes: initialState.agentNodes,
      };

    case 'SET_HISTORY':
      return { ...state, history: action.history };

    case 'SET_TASK_TEXT':
      return { ...state, taskText: action.text };

    default:
      return state;
  }
}

// ═══════════════════════════════════════
// Context
// ═══════════════════════════════════════
interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return ctx;
}

export { AppContext };
