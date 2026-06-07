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
            "• 分析 2026 年 AI Agent 的发展趋势，写一篇深度文章\n"
            "• 写一首关于秋天的五言诗\n"
            "• 设计一个面向大学生的笔记 App"
        ),
        key="task_input",
    )

    if st.button("🚀 开始执行", type="primary", use_container_width=True):
        # 提交任务到后端
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
                st.session_state.seen_event_count = 0
            else:
                st.error(f"后端错误: {resp.status_code}")
        except requests.ConnectionError:
            st.error("❌ 后端未启动")

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
                preview = item["task"][:35] + ("..." if len(item["task"]) > 35 else "")
                with st.expander(f"{preview} — {item['created_at'][:10]}"):
                    st.write(item["task"])
                    if st.button("🔁 重新执行", key=f"rerun_{item['id']}"):
                        st.session_state.task_input = item["task"]
                        st.rerun()
    except requests.ConnectionError:
        st.caption("⚠️ 后端未启动")

# ═══════════════════════════════════════
# 主区域：轮询显示 Agent 工作过程
# ═══════════════════════════════════════
if st.session_state.get("polling"):
    task_id = st.session_state["task_id"]
    task_text = st.session_state["task_text"]
    seen_count = st.session_state.get("seen_event_count", 0)

    # 占位区
    status_placeholder = st.empty()
    plan_placeholder = st.empty()
    workers_placeholder = st.empty()
    critic_placeholder = st.empty()
    final_placeholder = st.empty()

    max_polls = 120  # 最多等 2 分钟
    agent_displays = {}  # {node: accumulated text}

    for _ in range(max_polls):
        try:
            resp = requests.get(
                f"{BACKEND_URL}/task/{task_id}/status",
                timeout=5,
            )
            if resp.status_code != 200:
                time.sleep(1)
                continue

            data = resp.json()
            events = data.get("events", [])
            new_events = events[seen_count:]
            seen_count = len(events)
            st.session_state["seen_event_count"] = seen_count

            # 处理新事件
            for evt in new_events:
                node = evt.get("node", "system")
                etype = evt.get("event", "")
                content = evt.get("content", "")

                if node not in agent_displays:
                    agent_displays[node] = ""

                if etype == "agent_start":
                    agent_displays[node] += f"⏳ {content}\n\n"
                elif etype == "agent_done":
                    agent_displays[node] += f"\n\n✅ {content}"
                elif etype == "agent_output":
                    agent_displays[node] += content

            # 渲染
            # Planner
            if "planner" in agent_displays:
                with plan_placeholder.expander("🧠 Planner", expanded=True):
                    st.markdown(agent_displays["planner"])
            elif new_events:
                status_placeholder.info("⏳ 等待 Planner 制定计划...")

            # Workers (researcher, synthesizer, writer, designer, analyst)
            worker_roles = ["researcher", "synthesizer", "writer", "designer", "analyst"]
            active_workers = [r for r in worker_roles if r in agent_displays]
            if active_workers:
                # 每次重新渲染（确保 expander 更新）
                workers_placeholder.empty()
                for role in active_workers:
                    icon = ROLE_ICONS.get(role, "🔹")
                    with workers_placeholder.expander(f"{icon} {role.title()}", expanded=True):
                        st.markdown(agent_displays[role])

            # Critic
            if "critic" in agent_displays:
                with critic_placeholder.expander("👁️ Critic", expanded=True):
                    st.markdown(agent_displays["critic"])

            # Reviser
            if "reviser" in agent_displays:
                with critic_placeholder.expander("🔧 Reviser", expanded=True):
                    st.markdown(agent_displays["reviser"])

            # Final
            if new_events:
                status_placeholder.info(
                    f"⏳ Agent 团队工作中...（{seen_count} 步事件）"
                )

            # 检查是否完成
            if data.get("status") == "done":
                final = data.get("final_output", "")
                if final:
                    final_placeholder.markdown("---")
                    final_placeholder.subheader("📦 最终产出")
                    final_placeholder.markdown(final)
                    col1, col2 = final_placeholder.columns(2)
                    with col1:
                        st.download_button(
                            "💾 下载 Markdown",
                            final,
                            "mentex-output.md",
                            use_container_width=True,
                        )
                status_placeholder.success("✅ 任务完成！")
                st.session_state["polling"] = False
                break
            elif data.get("status") == "error":
                status_placeholder.error(f"❌ 执行出错: {data.get('error', '')}")
                st.session_state["polling"] = False
                break

            time.sleep(1)  # 每秒轮询

        except requests.ConnectionError:
            status_placeholder.error("❌ 后端连接中断")
            st.session_state["polling"] = False
            break
    else:
        status_placeholder.warning("⏰ 任务超时（2 分钟）")
        st.session_state["polling"] = False
