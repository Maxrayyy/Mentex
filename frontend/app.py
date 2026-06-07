import time
import requests
import streamlit as st

st.set_page_config(
    page_title="Mentex — 多 Agent 创意工作室",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Mentex — 多 Agent 创意工作室")
st.caption("像老板一样下达任务，然后看你的 AI 团队实时协作")

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

ROLE_ORDER = [
    "planner", "researcher", "synthesizer",
    "writer", "designer", "analyst",
    "critic", "reviser",
]

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
            "• 写一首关于秋天的五言诗\n"
            "• 分析 AI Agent 发展趋势\n"
            "• 设计一个学生笔记 App"
        ),
        key="task_input",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 开始执行", type="primary", use_container_width=True):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/task",
                    json={"task": task},
                    timeout=10,
                )
                if resp.status_code == 200:
                    st.session_state.task_id = resp.json()["task_id"]
                    st.session_state.polling = True
                    st.session_state.agent_texts = {}
                    st.session_state.event_count = 0
                    st.rerun()
                else:
                    st.error(f"后端错误: {resp.status_code}")
            except requests.ConnectionError:
                st.error("后端未启动")
    with col2:
        if st.button("🛑 停止", use_container_width=True):
            st.session_state.polling = False
            st.rerun()

    st.divider()
    st.subheader("📚 历史任务")
    try:
        resp = requests.get(f"{BACKEND_URL}/history", timeout=5)
        if resp.status_code == 200:
            history = resp.json()
            if not history:
                st.caption("暂无历史记录")
            for item in history:
                preview = item["task"][:30] + ("..." if len(item["task"]) > 30 else "")
                with st.expander(f"{preview} — {item['created_at'][:10]}"):
                    st.write(item["task"])
                    if st.button("🔁 重试", key=f"rerun_{item['id']}"):
                        st.session_state.task_input = item["task"]
                        st.rerun()
    except requests.ConnectionError:
        st.caption("后端未启动")

# ═══════════════════════════════════════
# 主区域
# ═══════════════════════════════════════
if st.session_state.get("polling"):
    task_id = st.session_state["task_id"]
    seen = st.session_state.get("event_count", 0)

    # 查增量事件
    try:
        resp = requests.get(
            f"{BACKEND_URL}/task/{task_id}/events?after={seen}",
            timeout=5,
        )
        if resp.status_code != 200:
            time.sleep(0.5)
            st.rerun()

        data = resp.json()
        new_events = data.get("events", [])
        status = data.get("status", "running")

        # 累积文本
        if "agent_texts" not in st.session_state:
            st.session_state.agent_texts = {}

        for evt in new_events:
            node = evt.get("node", "system")
            etype = evt.get("event", "")
            content = evt.get("content", "")

            if node not in st.session_state.agent_texts:
                st.session_state.agent_texts[node] = []

            if etype == "agent_start":
                st.session_state.agent_texts[node].append(f"⏳ {content}")
            elif etype == "agent_done":
                st.session_state.agent_texts[node].append(f"✅ {content}")

        st.session_state.event_count = seen + len(new_events)

        # ── 按顺序渲染每个角色 ──
        texts = st.session_state.agent_texts
        any_agent_shown = False

        for role in ROLE_ORDER:
            if role in texts and texts[role]:
                any_agent_shown = True
                icon = ROLE_ICONS.get(role, "🔹")
                with st.expander(
                    f"{icon} {role.title()}",
                    expanded=(status == "running" and role == list(texts.keys())[-1])
                ):
                    for line in texts[role]:
                        st.markdown(line)

        if not any_agent_shown:
            st.info("⏳ 等待 Planner 开始工作...")
        else:
            if status == "running":
                st.caption(f"⏳ 已产生 {len(new_events) + seen} 个事件，继续等待...")

        # 完成
        if status == "done":
            st.session_state.polling = False
            final = data.get("final_output", "")
            if final:
                st.markdown("---")
                st.subheader("📦 最终产出")
                st.markdown(final)
                st.download_button("💾 下载 Markdown", final, "mentex-output.md")
            st.success("✅ 任务完成！")

        elif status == "error":
            st.session_state.polling = False
            st.error(f"❌ 执行出错: {data.get('error', '')}")

        else:
            time.sleep(0.5)   # 半秒后再查
            st.rerun()

    except requests.ConnectionError:
        st.error("后端连接中断")
        st.session_state.polling = False
