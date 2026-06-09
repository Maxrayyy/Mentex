// ═══════════════════════════════════════
// Mentex 类型定义
// ═══════════════════════════════════════

/** Agent 事件类型 */
export type AgentEventType = 'agent_start' | 'agent_done' | 'done' | 'error' | 'heartbeat';

/** 后端推送的原始事件 */
export interface AgentEvent {
  event: AgentEventType;
  timestamp: string;
  node: string;
  instance: string;
  content: string;
  final_output?: string;
}

/** 任务执行状态 */
export type TaskStatus = 'idle' | 'running' | 'done' | 'error';

/** 历史任务记录 */
export interface HistoryItem {
  id: string;
  task: string;
  created_at: string;
}

/** Agent 角色名称 */
export type AgentRole =
  | 'planner'
  | 'researcher'
  | 'synthesizer'
  | 'writer'
  | 'designer'
  | 'analyst'
  | 'critic'
  | 'reviser';

/** Agent 工作状态 */
export type AgentState = 'pending' | 'running' | 'done';

/** 工作流中的 Agent 节点信息 */
export interface AgentNode {
  role: AgentRole;
  label: string;
  status: AgentState;
  content: string[];
}

/** 全局应用状态 */
export interface AppState {
  taskId: string | null;
  taskStatus: TaskStatus;
  taskText: string;
  events: AgentEvent[];
  finalOutput: string | null;
  error: string | null;
  history: HistoryItem[];
  agentNodes: AgentNode[];
}

/** 全局 Action 类型 */
export type AppAction =
  | { type: 'SUBMIT_TASK'; taskId: string; taskText: string }
  | { type: 'ADD_EVENT'; event: AgentEvent }
  | { type: 'TASK_DONE'; finalOutput: string }
  | { type: 'TASK_ERROR'; error: string }
  | { type: 'RESET' }
  | { type: 'SET_HISTORY'; history: HistoryItem[] }
  | { type: 'SET_TASK_TEXT'; text: string }
  | { type: 'SET_AGENT_NODES'; nodes: AgentNode[] };

/** Agent 角色元数据 */
export const ROLE_META: Record<AgentRole, { label: string; icon: string }> = {
  planner:     { label: 'Planner',     icon: 'Brain' },
  researcher:  { label: 'Researcher',  icon: 'Search' },
  synthesizer: { label: 'Synthesizer', icon: 'Link' },
  writer:      { label: 'Writer',      icon: 'PenLine' },
  designer:    { label: 'Designer',    icon: 'Palette' },
  analyst:     { label: 'Analyst',     icon: 'BarChart3' },
  critic:      { label: 'Critic',      icon: 'Eye' },
  reviser:     { label: 'Reviser',     icon: 'Wrench' },
};

/** 角色执行顺序（用于工作流排列） */
export const ROLE_ORDER: AgentRole[] = [
  'planner', 'researcher', 'synthesizer',
  'writer', 'designer', 'analyst',
  'critic', 'reviser',
];

/** REST API 走 Vite 代理（同源，无 CORS） */
export const BACKEND_URL = '/api';

/** SSE 直连后端（Vite 代理会缓冲 SSE 流） */
export const SSE_BASE = 'http://localhost:8000';
