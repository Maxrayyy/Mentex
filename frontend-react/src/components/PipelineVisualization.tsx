import type { AgentNode } from '../types';
import { ROLE_META, ROLE_ORDER } from '../types';
import * as Icons from 'lucide-react';
import { Circle } from 'lucide-react';

interface Props {
  nodes: AgentNode[];
}

export default function PipelineVisualization({ nodes }: Props) {
  return (
    <div className="bg-mentex-surface-secondary rounded-xl p-3 border border-mentex-border">
      <p className="text-xs font-medium text-mentex-text-muted mb-3 uppercase tracking-wider">
        Pipeline
      </p>
      <div className="flex items-start">
        {ROLE_ORDER.map((role, i) => {
          const node = nodes.find(n => n.role === role);
          if (!node) return null;

          const meta = ROLE_META[role];
          const iconName = meta.icon as keyof typeof Icons;
          const IconComponent = (Icons[iconName] as React.ComponentType<{ className?: string }>) || Circle;

          const isActive = node.status === 'running';
          const isDone = node.status === 'done';

          return (
            <div key={role} className="flex items-center flex-1 min-w-0 last:flex-none">
              <div
                className={`w-7 h-7 rounded-md flex items-center justify-center border
                             transition-all duration-300 flex-shrink-0
                             ${isDone
                               ? 'bg-mentex-success/10 border-mentex-success/30 text-mentex-success'
                               : isActive
                                 ? 'bg-mentex-accent/10 border-mentex-accent/30 text-mentex-accent animate-pulse'
                                 : 'bg-mentex-surface border-mentex-border text-mentex-text-muted/40'}`}
                title={`${meta.label} — ${node.status}`}
              >
                <IconComponent className="w-3.5 h-3.5" />
              </div>
              {i < ROLE_ORDER.length - 1 && (
                <div className={`flex-1 h-px mx-0.5 min-w-[4px] ${isDone ? 'bg-mentex-success/40' : 'bg-mentex-border'}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
