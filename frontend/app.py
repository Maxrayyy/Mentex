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
                    st.session_state.task_text = task
                    st.session_state.polling = True
                    st.session_state.agent_outputs = {}
                    st.session_state.last_event_count = 0
                    st.rerun()
                else:
                    st.error(f"后端错误: {resp.status_code}")
            except requests.ConnectionError:
                st.error("❌ 后端未启动")
    with col2:
        if st.button("🛑 停止", use_container_width=True):
            st.session_state.polling = False
            st.rerun()

    st.divider()

    # 历史任务
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
        st.caption("⚠️ 后端未启动")

# ═══════════════════════════════════════
# 主区域：每次 rerun 只查一次 API
# ═══════════════════════════════════════
if st.session_state.get("polling"):
    task_id = st.session_state["task_id"]

    # 查一次状态
    try:
        resp = requests.get(f"{BACKEND_URL}/task/{task_id}/status", timeout=5)
        if resp.status_code != 200:
            st.warning("等待后端响应...")
            time.sleep(1)
            st.rerun()

        data = resp.json()
        status = data.get("status", "running")
        events = data.get("events", [])

        # 累积展示文本
        if "agent_outputs" not in st.session_state:
            st.session_state.agent_outputs = {}

        for evt in events:
            node = evt.get("node", "system")
            etype = evt.get("event", "")
            content = evt.get("content", "")

            if node not in st.session_state.agent_outputs:
                st.session_state.agent_outputs[node] = ""

            if etype == "agent_start":
                st.session_state.agent_outputs[node] += f"⏳ {content}\n\n"
            elif etype == "agent_done":
                st.session_state.agent_outputs[node] += f"\n\n✅ {content}"
            elif etype == "agent_output":
                st.session_state.agent_outputs[node] += content

        outputs = st.session_state.agent_outputs

        # ── 渲染 ──
        # Planner
        if "planner" in outputs:
            with st.expander("🧠 Planner", expanded=True):
                st.markdown(outputs["planner"])

        # Workers
        for role in ["researcher", "synthesizer", "writer", "designer", "analyst"]:
            if role in outputs:
                icon = ROLE_ICONS.get(role, "🔹")
                with st.expander(f"{icon} {role.title()}", expanded=True):
                    st.markdown(outputs[role])

        # Critic
        if "critic" in outputs:
            with st.expander("👁️ Critic", expanded=True):
                st.markdown(outputs["critic"])

        # Reviser
        if "reviser" in outputs:
            with st.expander("🔧 Reviser", expanded=True):
                st.markdown(outputs["reviser"])

        # 状态和结果
        if status == "done":
            final = data.get("final_output", "")
            st.session_state.polling = False
            if final:
                st.markdown("---")
                st.subheader("📦 最终产出")
                st.markdown(final)
                st.download_button(
                    "💾 下载 Markdown",
                    final,
                    "mentex-output.md",
                )
            st.success(f"✅ 任务完成！共产生 {len(events)} 个事件")
        elif status == "error":
            st.session_state.polling = False
            st.error(f"❌ 执行出错: {data.get('error', '')}")
        else:
            # 还在跑，1 秒后自动刷新
            st.info(f"⏳ Agent 团队工作中...（{len(events)} 步事件）")
            time.sleep(1)
            st.rerun()

    except requests.ConnectionError:
        st.error("❌ 后端连接中断")
        st.session_state.polling = False
