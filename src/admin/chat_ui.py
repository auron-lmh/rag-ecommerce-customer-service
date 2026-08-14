"""用户聊天界面 — Gradio ChatBot

面向终端用户的客服聊天界面，支持：
- 流式输出（逐字显示）
- 多轮对话
- 显示意图分类和人工介入状态
- 显示检索来源
- 自动保存人工介入请求到数据库

启动: python -m src.admin.chat_ui
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import gradio as gr
import requests

logger = logging.getLogger(__name__)

# API 地址 (Docker 容器内使用服务名)
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://rag-api:8000")

# 人工介入数据库
HITL_DB = Path(__file__).parent.parent.parent / "data" / "hitl_requests.db"

# 修复(审查): 会话 ID 用随机 uuid 而非分钟级时间戳——同分钟内多用户会共享同一会话历史/人工状态。
# 每次启动生成一个随机会话，避免不同演示间的串扰；管理员处理结果仍可通过数据库按会话回查。
import uuid as _uuid

SESSION_ID = f"chat_{_uuid.uuid4().hex[:10]}"

# 已展示给客户的处理结果（避免重复显示）
_SHOWN_RESOLUTIONS: set[int] = set()

# 已推送给客户的人工消息最大 ID（避免重复）
_last_admin_msg_id = 0


def is_human_mode(session_id: str) -> bool:
    """该会话是否已转人工（存在待处理请求）"""
    try:
        with sqlite3.connect(HITL_DB) as conn:
            row = conn.execute(
                "SELECT 1 FROM hitl_requests WHERE session_id=? AND status='pending' LIMIT 1",
                (session_id,),
            ).fetchone()
        return row is not None
    except Exception:
        return False


def save_human_message(session_id: str, role: str, content: str) -> None:
    """保存人工对话消息（role: user=客户, assistant=客服）"""
    try:
        with sqlite3.connect(HITL_DB) as conn:
            conn.execute(
                "INSERT INTO human_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, datetime.now().isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error("保存人工消息失败: %s", e)


def get_human_assistant_messages(session_id: str, since_id: int = 0) -> list[tuple]:
    """获取管理员发给该会话的新消息（供主动推送）"""
    try:
        with sqlite3.connect(HITL_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, content FROM human_messages
                   WHERE session_id=? AND role='assistant' AND id>? ORDER BY id""",
                (session_id, since_id),
            ).fetchall()
        return [(r["id"], r["content"]) for r in rows]
    except Exception:
        return []


def init_hitl_db():
    """初始化人工介入数据库"""
    HITL_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(HITL_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hitl_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT DEFAULT '',
                user_query TEXT NOT NULL,
                intent TEXT DEFAULT '',
                confidence REAL DEFAULT 0,
                human_reason TEXT DEFAULT '',
                priority TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                assigned_to TEXT DEFAULT '',
                resolution TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                resolved_at TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS human_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def save_hitl_request(
    session_id: str,
    user_query: str,
    intent: str,
    confidence: float,
    human_reason: str,
    priority: str,
):
    """保存人工介入请求到数据库"""
    try:
        with sqlite3.connect(HITL_DB) as conn:
            conn.execute(
                """INSERT INTO hitl_requests
                   (session_id, user_query, intent, confidence, human_reason, priority, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    user_query,
                    intent,
                    confidence,
                    human_reason,
                    priority,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            logger.info("人工介入请求已保存: %s", user_query[:50])
    except Exception as e:
        logger.error("保存人工介入请求失败: %s", e)


def get_resolution_for_session(session_id: str) -> tuple[int, str]:
    """获取该会话已处理的人工介入结果（修复: 管理员处理后回传客户）

    Returns:
        (request_id, resolution) — 无则 ("", "")
    """
    try:
        with sqlite3.connect(HITL_DB) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT id, resolution FROM hitl_requests
                   WHERE session_id = ? AND status = 'resolved'
                     AND resolution != '' AND resolution IS NOT NULL
                   ORDER BY resolved_at DESC LIMIT 1""",
                (session_id,),
            ).fetchone()
        if row and row["resolution"]:
            return row["id"], row["resolution"]
    except Exception as e:
        logger.error("获取处理结果失败: %s", e)
    return "", ""


# 初始化数据库
init_hitl_db()


def chat_with_bot(message: str, history: list) -> tuple:
    """与客服机器人对话

    Args:
        message: 用户输入
        history: 对话历史 (Gradio 6.0 格式)

    Returns:
        (更新后的历史, 状态信息)
    """
    if not message.strip():
        return history, "请输入问题"

    # 修复: 先检查管理员是否已处理该会话的人工介入 → 回传给客户（形成闭环）
    res_id, resolution = get_resolution_for_session(SESSION_ID)
    admin_reply = ""
    if res_id and res_id not in _SHOWN_RESOLUTIONS:
        _SHOWN_RESOLUTIONS.add(res_id)
        admin_reply = f"【客服处理结果】{resolution}\n\n"

    # 已转人工 → 客户消息直接进人工对话（同一窗口），不走 AI
    if is_human_mode(SESSION_ID):
        save_human_message(SESSION_ID, "user", message)
        history.append({"role": "user", "content": message})
        history.append(
            {
                "role": "assistant",
                "content": "📞 已转人工，客服正在处理，请稍候。您的消息已同步给客服。",
            }
        )
        return history, "🔴 人工模式：消息已转人工客服，等待回复中..."

    try:
        # 调用 API（模块33: 携带 JWT）
        from src.admin.api_auth import auth_headers

        resp = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "query": message,
                "top_k": 5,
                "use_reranker": True,
                "session_id": SESSION_ID,
            },
            headers=auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # 提取结果
        reply = data.get("reply", "抱歉，暂时无法回答。")
        intent = data.get("intent", "")
        confidence = data.get("confidence", 0)
        needs_human = data.get("needs_human", False)
        human_reason = data.get("human_reason", "")
        results = data.get("results", [])

        # 构建状态信息
        status_parts = []
        if intent:
            status_parts.append(f"意图: {intent} ({confidence:.0%})")
        if needs_human:
            status_parts.append(f"⚠️ 需要人工介入: {human_reason}")
        if results:
            status_parts.append(f"检索到 {len(results)} 条结果")
            # 显示来源
            sources = set(
                r.get("source_file", "") for r in results if r.get("source_file")
            )
            if sources:
                status_parts.append(f"来源: {', '.join(sources)}")

        status = " | ".join(status_parts) if status_parts else "正常回复"

        # 如果需要人工介入，保存到数据库（用稳定会话 ID 关联）
        if needs_human:
            save_hitl_request(
                session_id=SESSION_ID,
                user_query=message,
                intent=intent,
                confidence=confidence,
                human_reason=human_reason,
                priority=data.get("human_priority", "medium"),
            )
            status += "\n✅ 已通知管理员，客服处理后将回复您"

        # 管理员处理结果前置（如已处理）
        final_reply = admin_reply + reply

        # Gradio 6.0 格式: [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": final_reply})

        return history, status

    except Exception as e:
        logger.exception("聊天请求失败")
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": "系统暂时繁忙，请稍后重试。"})
        return history, "系统暂时繁忙，请稍后重试。"


def clear_history():
    """清空对话历史"""
    return [], "对话已清空"


def poll_resolution(history: list):
    """主动推送客服处理结果 + 人工对话新回复（无需客户再发消息）

    由 gr.Timer 定时调用：管理员处理完/回复后 → 自动加进对话。
    """
    changed = False

    # 一次性处理结果
    res_id, resolution = get_resolution_for_session(SESSION_ID)
    if res_id and res_id not in _SHOWN_RESOLUTIONS:
        _SHOWN_RESOLUTIONS.add(res_id)
        history = list(history) + [
            {"role": "assistant", "content": f"【客服处理结果】{resolution}"}
        ]
        changed = True

    # 人工对话多轮回复（客服在管理员界面回复 → 主动推给客户）
    global _last_admin_msg_id
    new_msgs = get_human_assistant_messages(SESSION_ID, _last_admin_msg_id)
    for mid, content in new_msgs:
        history = list(history) + [
            {"role": "assistant", "content": f"【人工客服】{content}"}
        ]
        _last_admin_msg_id = mid
        changed = True

    if changed:
        return history, "📥 客服回复已送达"
    return history, gr.update()


def create_chat_ui() -> gr.Blocks:
    """创建聊天界面"""

    with gr.Blocks(title="电商智能客服") as app:
        gr.Markdown("""
            # 🤖 电商智能客服

            欢迎使用电商智能客服系统！请输入您的问题，我会尽力为您解答。

            **支持的功能：**
            - 商品咨询、退货退款、物流查询
            - 智能意图识别 + 多级检索降级
            - 幻觉检测 + 自纠正
            - 人工介入（退款/投诉/敏感话题）
            """)

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=400,
                    show_label=False,
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="输入问题",
                        placeholder="请输入您的问题...",
                        show_label=False,
                        scale=4,
                        container=False,
                    )
                    submit_btn = gr.Button("发送", variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("清空对话", variant="secondary")
                    retry_btn = gr.Button("重新回答", variant="secondary")

            with gr.Column(scale=1):
                status_display = gr.Textbox(
                    label="状态",
                    value="等待输入...",
                    interactive=False,
                    lines=3,
                )

                gr.Markdown("""
                    ### 📋 快捷问题

                    - 怎么退货？
                    - 退款多久到账？
                    - 快递到哪了？
                    - 这个商品怎么样？
                    - 我要投诉
                    """)

                gr.Markdown("""
                    ### ℹ️ 系统说明

                    - 意图分类：6类意图自动识别
                    - 检索策略：Hybrid Search + Reranker
                    - 降级策略：5级降级 + 联网搜索
                    - 质量保证：幻觉检测 + 自纠正
                    """)

        # 事件绑定
        def respond(message, history):
            return chat_with_bot(message, history)

        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, status_display],
        ).then(
            lambda: "",
            outputs=[msg_input],
        )

        submit_btn.click(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, status_display],
        ).then(
            lambda: "",
            outputs=[msg_input],
        )

        clear_btn.click(
            clear_history,
            outputs=[chatbot, status_display],
        )

        def retry_last(history):
            if history:
                # 获取最后一条用户消息
                last_message = None
                for msg in reversed(history):
                    if msg.get("role") == "user":
                        last_message = msg.get("content")
                        break
                if last_message:
                    # 移除最后一轮对话
                    history = history[:-2]
                    return chat_with_bot(last_message, history)
            return history, "没有可重试的消息"

        retry_btn.click(
            retry_last,
            inputs=[chatbot],
            outputs=[chatbot, status_display],
        )

        # 主动推送: 每 5 秒检查管理员处理结果（无需客户再发消息）
        timer = gr.Timer(5)
        timer.tick(
            poll_resolution,
            inputs=[chatbot],
            outputs=[chatbot, status_display],
        )

    return app


def main():
    """启动聊天界面"""
    from src.admin.api_auth import gradio_auth

    app = create_chat_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
        auth=gradio_auth(),
    )


if __name__ == "__main__":
    main()
