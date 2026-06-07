import streamlit as st
import requests
import json
import sseclient

st.set_page_config(
    page_title="Mentex — 多 Agent 创意工作室",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Mentex — 多 Agent 创意工作室")
st.caption("像老板一样下达任务，然后看你的 AI 团队实时协作")

# ── 角色图标映射 ──
ROLE_ICONS = {
    "planner":     "🧠",
    "researcher":  "🔍",
    "synthesizer": "🔗",
    "writer":      "✍️",
    "designer":    "🎨",
    "analyst":     "📊",
    "critic":      "👁️",
    "reviser":     "🔧",
    "system":      "📦",
}

BACKEND_URL = "http://localhost:8000"

# ═══════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════
with st.sidebar:
    st.subheader("📝 新任务")
    task = st.text_area(
        "任务描述",
        height=150,
        placeholder=(
            "例如：\n"
            "• 分析 2026 年 AI Agent 的发展趋势，写一篇深度文章\n"
            "• 写一首关于秋天的五言诗\n"
            "• 设计一个面向大学生的笔记 App"
        ),
        key="task_input",
    )

    if st.button("🚀 开始执行", type="primary", use_container_width=True):
        st.session_state.run_triggered = True
        st.session_state.current_task = task

    st.divider()

    # 历史任务列表
    st.subheader("📚 历史任务")
    try:
        resp = requests.get(f"{BACKEND_URL}/history", timeout=5)
        if resp.status_code == 200:
            history = resp.json()
            if not history:
                st.caption("暂无历史记录")
            for item in history:
                task_preview = item["task"][:35] + ("..." if len(item["task"]) > 35 else "")
                with st.expander(f"{task_preview} — {item['created_at'][:10]}"):
                    st.write(item["task"])
                    if st.button("🔁 重新执行", key=f"rerun_{item['id']}"):
                        st.session_state.task_input = item["task"]
                        st.rerun()
        else:
            st.caption("⚠️ 后端返回错误")
    except requests.ConnectionError:
        st.caption("⚠️ 后端未启动，请先运行：")
        st.code("python -m uvicorn backend.api:app --port 8000")

# ═══════════════════════════════════════
# 主区域
# ═══════════════════════════════════════
if st.session_state.get("run_triggered") and st.session_state.get("current_task"):
    task_text = st.session_state.current_task
    st.session_state.run_triggered = False  # 重置

    # 为每个角色预分配显示容器
    containers = {}
    placeholders = {}

    # Planner 和 Critic 一定出现，先创建
    for role in ["planner"]:
        icon = ROLE_ICONS.get(role, "🔹")
        containers[role] = st.expander(f"{icon} {role.title()}", expanded=True)
        placeholders[role] = containers[role].empty()

    final_area = st.empty()
    status_bar = st.status("等待 Agent 团队开工...", expanded=True)

    try:
        with requests.post(
            f"{BACKEND_URL}/task",
            json={"task": task_text},
            stream=True,
            timeout=300,
        ) as r:
            if r.status_code != 200:
                st.error(f"后端错误: {r.status_code}")
            else:
                client = sseclient.SSEClient(r)
                agent_outputs = {}

                for sse_event in client.events():
                    data = json.loads(sse_event.data)
                    node = data.get("node", "system")
                    event_type = data.get("event", "")
                    content = data.get("content", "")

                    # 动态创建新角色的 expander
                    if node not in containers:
                        icon = ROLE_ICONS.get(node, "🔹")
                        containers[node] = st.expander(
                            f"{icon} {node.title()}", expanded=True
                        )
                        placeholders[node] = containers[node].empty()
                        agent_outputs[node] = ""

                    if node not in agent_outputs:
                        agent_outputs[node] = ""

                    if event_type == "agent_start":
                        agent_outputs[node] = f"⏳ {content}\n\n"
                        placeholders[node].markdown(agent_outputs[node])
                        status_bar.update(label=f"{ROLE_ICONS.get(node, '')} {node.title()} 工作中...")

                    elif event_type == "agent_done":
                        agent_outputs[node] += f"\n\n✅ {content}"
                        placeholders[node].markdown(agent_outputs[node])

                    elif event_type == "final":
                        status_bar.update(label="✅ 任务完成！", state="complete")
                        if content:
                            final_area.markdown("---")
                            final_area.subheader("📦 最终产出")
                            final_area.markdown(content)

                            col1, col2 = st.columns(2)
                            with col1:
                                st.download_button(
                                    "💾 下载 Markdown",
                                    content,
                                    "mentex-output.md",
                                    use_container_width=True,
                                )
                            with col2:
                                if st.button("📋 复制到剪贴板", use_container_width=True):
                                    st.info("已复制！")

                    elif event_type == "error":
                        st.error(content)

    except requests.ConnectionError:
        st.error("❌ 无法连接后端，请先启动：`python -m uvicorn backend.api:app --port 8000`")
