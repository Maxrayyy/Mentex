import type { AgentNode } from '../types';
import { ROLE_META, ROLE_ORDER } from '../types';
import * as Icons from 'lucide-react';
import { Circle } from 'lucide-react';

interface Props {
  nodes: AgentNode[];
}

export default function PipelineVisualization({ nodes }: Props) {
  return (
    <div className="bg-mentex-surface-secondary rounded-xl p-4 border border-mentex-border">
      <p className="text-xs font-medium text-mentex-text-muted mb-4 uppercase tracking-wider">
        Pipeline
      </p>
      <div className="flex items-start justify-between">
        {ROLE_ORDER.map((role, i) => {
          const node = nodes.find(n => n.role === role);
          if (!node) return null;

          const meta = ROLE_META[role];
          const iconName = meta.icon as keyof typeof Icons;
          const IconComponent = (Icons[iconName] as React.ComponentType<{ className?: string }>) || Circle;

          const isActive = node.status === 'running';
          const isDone = node.status === 'done';
          const isPending = node.status === 'pending';

          return (
            <div key={role} className="flex items-center">
              {/* 节点 */}
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center border
                               transition-all duration-300
                               ${isDone
                                 ? 'bg-mentex-success/10 border-mentex-success/30 text-mentex-success'
                                 : isActive
                                   ? 'bg-mentex-accent/10 border-mentex-accent/30 text-mentex-accent animate-pulse'
                                   : 'bg-mentex-surface border-mentex-border text-mentex-text-muted/40'}`}
                  title={`${meta.label} - ${node.status}`}
                  aria-label={`${meta.label}: ${node.status}`}
                >
                  <IconComponent className="w-4 h-4" />
                </div>
                <span
                  className={`text-[10px] leading-tight text-center max-w-[64px] truncate
                               ${isPending ? 'text-mentex-text-muted/40' : 'text-mentex-text/70'}`}
                >
                  {meta.label}
                </span>
              </div>

              {/* 连接线（除最后一个） */}
              {i < ROLE_ORDER.length - 1 && (
                <div className="flex-1 flex justify-center px-0.5 -mt-5">
                  <div
                    className={`w-4 h-px ${
                      isDone ? 'bg-mentex-success/40' : 'bg-mentex-border'
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
