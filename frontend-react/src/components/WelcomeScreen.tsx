import { useAppContext } from '../context/AppContext';
import { Brain, Sparkles, ArrowRight } from 'lucide-react';

const EXAMPLE_TASKS = [
  '写一首关于秋天的五言诗',
  '分析 2026 年 AI Agent 的发展趋势，写一篇深度文章',
  '设计一个面向大学生的笔记 App',
  '用 SWOT 方法分析特斯拉的竞争地位',
];

export default function WelcomeScreen() {
  const { dispatch } = useAppContext();

  function handleExample(task: string) {
    dispatch({ type: 'SET_TASK_TEXT', text: task });
  }

  return (
    <div className="flex items-center justify-center min-h-full px-8 py-16">
      <div className="max-w-2xl w-full text-center space-y-8">
        {/* 图标 */}
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl
                        bg-mentex-accent/10 border border-mentex-accent/20">
          <Brain className="w-8 h-8 text-mentex-accent" />
        </div>

        {/* 标题 */}
        <h2 className="text-2xl font-heading font-semibold text-mentex-text">
          多 Agent 创意工作室
        </h2>

        {/* 示例任务 */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 justify-center">
            <Sparkles className="w-4 h-4 text-mentex-warning" />
            <span className="text-sm font-medium text-mentex-text-muted">
              试试这些任务
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 max-w-lg mx-auto">
            {EXAMPLE_TASKS.map(task => (
              <button
                key={task}
                onClick={() => handleExample(task)}
                className="text-left px-4 py-3 rounded-lg
                           bg-mentex-surface-secondary border border-mentex-border
                           hover:border-mentex-accent/40 hover:bg-mentex-accent/5
                           text-sm text-mentex-text/80 hover:text-mentex-text
                           transition-all duration-200 cursor-pointer
                           group flex items-center gap-2"
              >
                <ArrowRight className="w-3.5 h-3.5 text-mentex-text-muted/50 flex-shrink-0
                                         group-hover:text-mentex-accent transition-colors duration-200" />
                <span className="line-clamp-2">{task}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
