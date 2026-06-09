import { useAppContext } from '../context/AppContext';
import AgentCard from './AgentCard';
import PipelineVisualization from './PipelineVisualization';
import { GitBranch, Zap } from 'lucide-react';

export default function WorkflowPanel() {
  const { state } = useAppContext();
  const { agentNodes, taskStatus } = state;
  const isActive = taskStatus === 'running' || taskStatus === 'done';

  return (
    <aside className="w-96 flex-shrink-0 border-l border-mentex-border flex flex-col
                      bg-mentex-surface">
      {/* 面板标题 */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-mentex-border">
        <GitBranch className="w-5 h-5 text-mentex-accent" />
        <h2 className="text-sm font-heading font-medium text-mentex-text">
          工作流
        </h2>
        {taskStatus === 'running' && (
          <span className="ml-auto flex items-center gap-1 text-xs text-mentex-accent">
            <Zap className="w-3 h-3" />
            SSE
          </span>
        )}
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!isActive || agentNodes.every(n => n.status === 'pending') ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-2">
            <GitBranch className="w-10 h-10 text-mentex-text-muted/15" />
            <p className="text-sm text-mentex-text-muted">
              提交任务后，工作流状态将在此实时展示
            </p>
            <p className="text-xs text-mentex-text-muted/50">
              Planner → Worker → Critic → Reviser
            </p>
          </div>
        ) : (
          <>
            <PipelineVisualization nodes={agentNodes} />
            <div className="space-y-2">
              {agentNodes
                .filter(n => n.status !== 'pending')
                .map(node => (
                  <AgentCard key={node.role} node={node} />
                ))}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
