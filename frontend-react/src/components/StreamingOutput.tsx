import type { AgentEvent } from '../types';
import { Loader } from 'lucide-react';

interface Props {
  events: AgentEvent[];
}

export default function StreamingOutput({ events }: Props) {
  return (
    <div className="px-8 py-8 space-y-6">
      {events.length === 0 ? (
        <div className="flex items-center gap-3">
          <Loader className="w-5 h-5 text-mentex-accent animate-spin" />
          <span className="text-sm text-mentex-text-muted">等待 Planner 开始工作...</span>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((evt, i) => (
            <div
              key={i}
              className="flex items-start gap-3 py-2"
            >
              <span className="w-2 h-2 mt-1.5 rounded-full bg-mentex-accent flex-shrink-0" />
              <p className="text-sm text-mentex-text/80">{evt.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
