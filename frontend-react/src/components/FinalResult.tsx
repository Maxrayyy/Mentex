import { useAppContext } from '../context/AppContext';
import ReactMarkdown from 'react-markdown';
import { Download, AlertCircle } from 'lucide-react';

export default function FinalResult() {
  const { state, dispatch } = useAppContext();
  const { taskStatus, finalOutput, error } = state;

  // 错误状态
  if (taskStatus === 'error') {
    return (
      <div className="flex items-center justify-center min-h-full px-8 py-16">
        <div className="max-w-lg w-full text-center space-y-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl
                          bg-mentex-error/10 border border-mentex-error/20">
            <AlertCircle className="w-8 h-8 text-mentex-error" />
          </div>
          <h3 className="text-lg font-heading font-medium text-mentex-text">
            任务执行出错
          </h3>
          <p className="text-sm text-mentex-text-muted bg-mentex-surface-secondary
                        rounded-lg px-4 py-3 border border-mentex-border">
            {error || '未知错误'}
          </p>
          <button
            onClick={() => dispatch({ type: 'RESET' })}
            className="text-sm text-mentex-accent hover:underline cursor-pointer"
          >
            重新开始
          </button>
        </div>
      </div>
    );
  }

  // 完成状态
  return (
    <div className="px-8 py-8 space-y-6 max-w-3xl">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-heading font-medium text-mentex-text">
          最终产出
        </h3>
        {finalOutput && (
          <button
            onClick={() => {
              const blob = new Blob([finalOutput], { type: 'text/markdown' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'mentex-output.md';
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                       bg-mentex-surface-secondary border border-mentex-border
                       hover:border-mentex-accent/40 hover:bg-mentex-accent/5
                       text-sm text-mentex-text/80 hover:text-mentex-text
                       transition-all duration-200 cursor-pointer"
          >
            <Download className="w-4 h-4" />
            下载 Markdown
          </button>
        )}
      </div>

      {/* 产出内容 */}
      {finalOutput ? (
        <div className="bg-mentex-surface border border-mentex-border rounded-xl p-6
                        markdown-body">
          <ReactMarkdown>{finalOutput}</ReactMarkdown>
        </div>
      ) : (
        <div className="async-content-placeholder flex items-center justify-center
                        bg-mentex-surface border border-mentex-border rounded-xl">
          <p className="text-mentex-text-muted text-sm">
            暂无产出内容
          </p>
        </div>
      )}

    </div>
  );
}
