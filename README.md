# 🧠 Mentex — 多 Agent 创意工作室

把你的任务交给 AI 团队，看他们实时协作完成。

## 快速开始

```bash
source ../.venv/bin/activate
cp .env.example .env    # 编辑 .env 填入 DeepSeek API Key

# 终端 1：启动后端
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# 终端 2：启动前端
streamlit run frontend/app.py
```

浏览器打开 http://localhost:8501
