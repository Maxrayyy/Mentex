import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import WorkflowPanel from './components/WorkflowPanel';

export default function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-mentex-bg text-mentex-text">
      {/* 左侧边栏：任务输入 + 历史记录 */}
      <Sidebar />

      {/* 中间：问答内容生成 / 产出展示 */}
      <MainContent />

      {/* 右侧：工作流可视化 */}
      <WorkflowPanel />
    </div>
  );
}
