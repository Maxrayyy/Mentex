import { useState } from 'react';
import type { AgentNode } from '../types';
import { ROLE_META } from '../types';
import { ChevronDown, Loader, Check, Circle, Coins } from 'lucide-react';
import * as Icons from 'lucide-react';

interface Props {
  node: AgentNode;
}

export default function AgentCard({ node }: Props) {
  const [expanded, setExpanded] = useState(false);
  const meta = ROLE_META[node.role];

  // 动态获取图标组件
  const iconName = meta.icon as keyof typeof Icons;
  const IconComponent = (Icons[iconName] as React.ComponentType<{ className?: string }>) || Circle;

  const statusConfig = {
    pending: {
      className: 'border-mentex-border bg-mentex-surface-secondary',
      textColor: 'text-mentex-text-muted',
    },
    running: {
      className: 'border-mentex-accent/30 bg-mentex-accent/5',
      textColor: 'text-mentex-accent',
    },
    done: {
      className: 'border-mentex-success/20 bg-mentex-success/5',
      textColor: 'text-mentex-success',
    },
  };

  const config = statusConfig[node.status];

  return (
    <div
      className={`rounded-lg border transition-all duration-300 cursor-pointer
                   hover:border-mentex-accent/40 ${config.className}`}
      onClick={() => setExpanded(!expanded)}
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setExpanded(!expanded);
        }
      }}
    >
      {/* 卡片头部 */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        {/* 状态图标 */}
        <div className="relative flex-shrink-0">
          <IconComponent className={`w-4 h-4 ${config.textColor}`} />
          {node.status === 'running' && (
            <Loader className="w-3 h-3 text-mentex-accent animate-spin absolute -top-1 -right-1" />
          )}
          {node.status === 'done' && (
            <Check className="w-3 h-3 text-mentex-success absolute -top-1 -right-1" />
          )}
        </div>

        {/* 角色名称和状态 */}
        <div className="flex-1 min-w-0 flex items-center gap-1.5">
          <span className={`text-sm font-medium truncate ${config.textColor}`}>
            {meta.label}
          </span>
          {node.status === 'running' && (
            <span className="text-xs text-mentex-accent animate-pulse flex-shrink-0">
              工作中...
            </span>
          )}
          {node.status === 'done' && node.tokens && (
            <span className="text-xs text-mentex-text-muted/70 flex items-center gap-0.5 flex-shrink-0">
              <Coins className="w-3 h-3" />
              {node.tokens.total.toLocaleString()} tokens
            </span>
          )}
        </div>

        {/* 展开指示器 */}
        <ChevronDown
          className={`w-3.5 h-3.5 text-mentex-text-muted transition-transform duration-200 flex-shrink-0
                      ${expanded ? 'rotate-180' : ''}`}
        />
      </div>

      {/* 展开详情 */}
      {expanded && node.content.length > 0 && (
        <div className="px-3 pb-3 pt-0 border-t border-mentex-border/50 overflow-hidden">
          <div className="pt-2.5 space-y-1.5">
            {node.content.map((line, i) => (
              <p key={i} className="text-xs text-mentex-text-muted leading-relaxed break-words">
                {line}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
